#!/usr/bin/env python3
"""Execute resumable W10 adaptive-policy retrieval trials."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import random
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "agent-svc"))

from agent.experimental.bounded_adaptive_policy import (
    CandidateAssessment,
    EvidenceGap,
    QueryProposal,
    WorkState,
    admit_candidate,
    gate_proposal,
    replay_policy_trace,
    stop_reason,
)

POLICIES = ("fixed", "unconstrained", "gap", "gated", "full")
PURPOSES = (
    "missing_support",
    "contradiction",
    "freshness",
    "primary_source",
    "publisher_independence",
    "entity_identity",
)


def digest(value: str | bytes) -> str:
    raw = value.encode() if isinstance(value, str) else value
    return hashlib.sha256(raw).hexdigest()


def remaining_seconds(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("the 90-second case limit was reached")
    return max(0.1, remaining)


def canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.casefold(), host, path, parsed.query, ""))


def publisher_id(value: str) -> str:
    host = (urlsplit(value).hostname or "").casefold()
    return host.removeprefix("www.")


def build_work_order(
    cases: list[dict[str, Any]],
    policies: list[str],
    repetitions: int,
    seed: int,
) -> list[tuple[dict[str, Any], str, int]]:
    """Rotate policy order inside each case while shuffling case order by repetition."""
    work = []
    bases: dict[str, list[str]] = {}
    for case in cases:
        order = list(policies)
        case_seed = int(digest(f"{seed}:{case['case_id']}:policies")[:16], 16)
        random.Random(case_seed).shuffle(order)
        bases[case["case_id"]] = order
    for repetition in range(repetitions):
        case_order = list(cases)
        random.Random(seed + repetition).shuffle(case_order)
        for case in case_order:
            base = bases[case["case_id"]]
            offset = repetition % len(base)
            rotated = base[offset:] + base[:offset]
            work.extend((case, policy, repetition) for policy in rotated)
    return work


def model_json(
    client: httpx.Client,
    *,
    model: str,
    name: str,
    schema: dict[str, Any],
    prompt: dict[str, Any],
    max_tokens: int,
    deadline: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    try:
        response = client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a conservative research evaluator. Use only the "
                            "provided material. Return JSON matching the schema."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                "temperature": 0,
                "max_tokens": max_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": name, "strict": True, "schema": schema},
                },
            },
            timeout=remaining_seconds(deadline),
        )
        response.raise_for_status()
        envelope = response.json()
        content = envelope["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except Exception as error:
        raise RuntimeError(f"{name}: {type(error).__name__}: {error}") from error
    return parsed, {
        "latency_ms": round((time.monotonic() - started) * 1000, 3),
        "model": envelope.get("model"),
        "usage": envelope.get("usage") or {},
        "response_sha256": digest(content),
    }


def search(
    client: httpx.Client, query: str, limit: int, *, deadline: float
) -> tuple[list[dict[str, Any]], float]:
    started = time.monotonic()
    response = client.post(
        "/v2/search",
        json={"query": query, "limit": limit, "search_type": "fast"},
        timeout=remaining_seconds(deadline),
    )
    response.raise_for_status()
    payload = response.json()
    results = (payload.get("data") or {}).get("web") or []
    if not payload.get("success") or not isinstance(results, list):
        raise RuntimeError("search returned no valid result list")
    return results[:limit], round((time.monotonic() - started) * 1000, 3)


def scrape(
    client: httpx.Client, result: dict[str, Any], *, deadline: float
) -> dict[str, Any]:
    started = time.monotonic()
    url = str(result.get("url", ""))
    record: dict[str, Any] = {
        "url": url,
        "canonical_url": canonical_url(url),
        "publisher_id": publisher_id(url),
        "title": str(result.get("title", ""))[:500],
        "snippet": str(result.get("description", result.get("content", "")))[:1000],
        "accessed_at": datetime.now(UTC).isoformat(),
    }
    try:
        response = client.post(
            "/v2/scrape",
            json={"url": url, "formats": ["markdown"]},
            timeout=remaining_seconds(deadline),
        )
        response.raise_for_status()
        payload = response.json()
        markdown = str((payload.get("data") or {}).get("markdown", ""))
        if not payload.get("success") or not markdown:
            raise RuntimeError("empty scrape")
        record.update(
            acquisition_status="acquired",
            reviewed_bytes_sha256=digest(markdown),
            reviewed_excerpt=markdown[:4000],
        )
    except Exception as error:
        record.update(
            acquisition_status="unavailable",
            reviewed_bytes_sha256=None,
            reviewed_excerpt="",
            acquisition_error=f"{type(error).__name__}: {error}"[:500],
        )
    record["acquisition_ms"] = round((time.monotonic() - started) * 1000, 3)
    return record


def search_record(result: dict[str, Any], *, attempt: int, rank: int) -> dict[str, Any]:
    url = str(result.get("url", ""))
    return {
        "url": url,
        "canonical_url": canonical_url(url),
        "publisher_id": publisher_id(url),
        "title": str(result.get("title", ""))[:500],
        "snippet": str(result.get("description", result.get("content", "")))[:1000],
        "observed_at": datetime.now(UTC).isoformat(),
        "search_origins": [{"attempt": attempt, "rank": rank}],
        "acquisition_status": "not_selected",
        "reviewed_bytes_sha256": None,
        "reviewed_excerpt": "",
    }


def planning_schema(gap_ids: list[str], *, unconstrained: bool) -> dict[str, Any]:
    allowed_gaps = [*gap_ids, "general"] if unconstrained else gap_ids
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["initial_gaps", "proposals"],
        "properties": {
            "initial_gaps": {
                "type": "array",
                "minItems": len(gap_ids),
                "maxItems": len(gap_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["gap_id", "status", "reason"],
                    "properties": {
                        "gap_id": {"type": "string", "enum": gap_ids},
                        "status": {
                            "type": "string",
                            "enum": ["open", "closed", "ambiguous"],
                        },
                        "reason": {"type": "string"},
                    },
                },
            },
            "proposals": {
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["query", "gap_id", "predicted_evidence", "purpose"],
                    "properties": {
                        "query": {"type": "string"},
                        "gap_id": {"type": "string", "enum": allowed_gaps},
                        "predicted_evidence": {"type": "string"},
                        "purpose": {"type": "string", "enum": list(PURPOSES)},
                    },
                },
            },
        },
    }


def assessment_schema(gap_ids: list[str], candidate_ids: list[str]) -> dict[str, Any]:
    quality = {
        "type": "object",
        "additionalProperties": False,
        "required": ["currency", "relevance", "authority", "accuracy", "purpose"],
        "properties": {
            key: {"type": "integer", "minimum": 0, "maximum": 2}
            for key in ("currency", "relevance", "authority", "accuracy", "purpose")
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["candidates", "gaps"],
        "properties": {
            "candidates": {
                "type": "array",
                "minItems": len(candidate_ids),
                "maxItems": len(candidate_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "candidate_id",
                        "relevant_gap_ids",
                        "supports_or_challenges",
                        "quality",
                        "derivative_of",
                        "marginal_value",
                        "improves_currency",
                        "improves_authority",
                        "resolves_contradiction",
                        "reason",
                    ],
                    "properties": {
                        "candidate_id": {"type": "string", "enum": candidate_ids},
                        "relevant_gap_ids": {
                            "type": "array",
                            "items": {"type": "string", "enum": gap_ids},
                        },
                        "supports_or_challenges": {"type": "boolean"},
                        "quality": quality,
                        "derivative_of": {"type": ["string", "null"]},
                        "marginal_value": {"type": "boolean"},
                        "improves_currency": {"type": "boolean"},
                        "improves_authority": {"type": "boolean"},
                        "resolves_contradiction": {"type": "boolean"},
                        "reason": {"type": "string", "maxLength": 240},
                    },
                },
            },
            "gaps": {
                "type": "array",
                "minItems": len(gap_ids),
                "maxItems": len(gap_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["gap_id", "status", "candidate_ids", "reason"],
                    "properties": {
                        "gap_id": {"type": "string", "enum": gap_ids},
                        "status": {
                            "type": "string",
                            "enum": ["open", "closed", "ambiguous"],
                        },
                        "candidate_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reason": {"type": "string", "maxLength": 240},
                    },
                },
            },
        },
    }


def execute_trial(
    case: dict[str, Any],
    policy: str,
    repetition: int,
    *,
    api_client: httpx.Client,
    llm_client: httpx.Client,
    model: str,
    result_limit: int,
    seed: int,
) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + 90
    claims = case["claims"]
    gaps = tuple(
        EvidenceGap(item["claim_id"], item["importance"], item["closure_rule"])
        for item in claims
    )
    attempts: list[dict[str, Any]] = []
    initial, latency = search(
        api_client, case["query"], result_limit, deadline=deadline
    )
    attempts.append(
        {
            "query": case["query"],
            "purpose": "initial",
            "latency_ms": latency,
            "result_count": len(initial),
        }
    )
    candidates: dict[str, dict[str, Any]] = {}

    def register(results: list[dict[str, Any]], attempt: int) -> list[str]:
        keys: list[str] = []
        for rank, result in enumerate(results, 1):
            item = search_record(result, attempt=attempt, rank=rank)
            key = item["canonical_url"]
            if not key:
                continue
            if key in candidates:
                candidates[key]["search_origins"].extend(item["search_origins"])
            else:
                candidates[key] = item
            keys.append(key)
        return list(dict.fromkeys(keys))

    def acquire(keys: list[str], limit: int) -> None:
        selected = [
            key
            for key in keys
            if candidates[key]["acquisition_status"] == "not_selected"
        ][:limit]
        for key in selected:
            origins = candidates[key]["search_origins"]
            candidates[key].update(
                scrape(api_client, candidates[key], deadline=deadline)
            )
            candidates[key]["search_origins"] = origins

    initial_keys = register(initial, 0)
    acquire(initial_keys, 8 if policy == "fixed" else 4)

    planning = None
    planning_receipt = None
    proposal_log: list[dict[str, Any]] = []
    if policy != "fixed":
        blind_initial = [
            {
                "candidate_id": digest(key)[:16],
                "title": item["title"],
                "excerpt": item["reviewed_excerpt"],
                "available": item["acquisition_status"] == "acquired",
            }
            for key, item in candidates.items()
            if item["acquisition_status"] != "not_selected"
        ]
        planning, planning_receipt = model_json(
            llm_client,
            model=model,
            name="w10_query_plan",
            schema=planning_schema(
                [gap.gap_id for gap in gaps], unconstrained=policy == "unconstrained"
            ),
            prompt={
                "question": case["query"],
                "as_of": case["as_of"],
                "gaps": claims,
                "initial_sources": blind_initial,
                "policy": (
                    "Propose broad follow-up searches wherever more information may help."
                    if policy == "unconstrained"
                    else "Tie every proposal to one still-open declared gap."
                ),
                "instruction": "Do not answer the research question.",
            },
            max_tokens=1400,
            deadline=deadline,
        )
        statuses = {item["gap_id"]: item["status"] for item in planning["initial_gaps"]}
        all_closed = statuses and all(value == "closed" for value in statuses.values())
        if not all_closed:
            prior = (case["query"],)
            for raw in planning["proposals"]:
                admitted, reason = True, "policy_has_no_proposal_gate"
                if policy in {"gated", "full"}:
                    proposal = QueryProposal(**raw)
                    decision = gate_proposal(
                        proposal,
                        original_query=case["query"],
                        gaps=gaps,
                        prior_queries=prior,
                    )
                    admitted, reason = decision.admitted, decision.reason
                proposal_log.append({**raw, "admitted": admitted, "reason": reason})
                if admitted:
                    results, query_ms = search(
                        api_client, raw["query"], result_limit, deadline=deadline
                    )
                    attempts.append(
                        {
                            "query": raw["query"],
                            "purpose": raw["purpose"],
                            "gap_id": raw["gap_id"],
                            "latency_ms": query_ms,
                            "result_count": len(results),
                        }
                    )
                    followup_keys = register(results, len(attempts) - 1)
                    acquire(followup_keys, 2)
                    prior = (*prior, raw["query"])

    acquire(
        list(candidates),
        8
        - sum(
            item["acquisition_status"] != "not_selected" for item in candidates.values()
        ),
    )

    candidate_payload = []
    id_to_key: dict[str, str] = {}
    for key, item in candidates.items():
        if item["acquisition_status"] == "not_selected":
            continue
        candidate_id = digest(key)[:16]
        id_to_key[candidate_id] = key
        candidate_payload.append(
            {
                "candidate_id": candidate_id,
                "title": item["title"],
                "excerpt": item["reviewed_excerpt"],
                "available": item["acquisition_status"] == "acquired",
            }
        )
    blind_seed = int(digest(f"{seed}:{case['case_id']}:{policy}:{repetition}")[:16], 16)
    random.Random(blind_seed).shuffle(candidate_payload)
    assessment, assessment_receipt = model_json(
        llm_client,
        model=model,
        name="w10_evidence_assessment",
        schema=assessment_schema(
            [gap.gap_id for gap in gaps],
            [item["candidate_id"] for item in candidate_payload],
        ),
        prompt={
            "question": case["query"],
            "as_of": case["as_of"],
            "gaps": claims,
            "candidates": candidate_payload,
            "instruction": (
                "Judge every candidate separately. Close a gap only from acquired "
                "content that meets its closure rule. A snippet alone is insufficient. "
                "Score each quality dimension as 0 poor, 1 adequate, or 2 strong. "
                "Marginal value means the source adds material claim evidence beyond "
                "the other candidates, improves authority or currency, resolves a "
                "contradiction, or supplies an independent publisher. Use candidate "
                "IDs in derivative_of. Keep reasons concrete and brief."
            ),
        },
        max_tokens=4000,
        deadline=deadline,
    )
    assessed = {item["candidate_id"]: item for item in assessment["candidates"]}
    if set(assessed) != set(id_to_key):
        raise ValueError("assessment must return every candidate exactly once")
    graded_gaps = {item["gap_id"] for item in assessment["gaps"]}
    if graded_gaps != {gap.gap_id for gap in gaps}:
        raise ValueError("assessment must return every gap exactly once")
    admitted_ids: list[str] = []
    admitted_canonical_ids: set[str] = set()
    admitted_publishers: set[str] = set()
    for canonical, source in candidates.items():
        candidate_id = digest(canonical)[:16]
        source["candidate_id"] = candidate_id
        if source["acquisition_status"] == "not_selected":
            source["admitted"] = False
            source["admission_reason"] = "not_selected_for_acquisition"
            continue
        item = assessed[candidate_id]
        admitted = source["acquisition_status"] == "acquired" and len(admitted_ids) < 8
        admission_reason = (
            "admitted_within_source_limit" if admitted else "source_limit"
        )
        if policy == "full":
            quality = item["quality"]
            decision = admit_candidate(
                CandidateAssessment(
                    candidate_id=candidate_id,
                    relevant_gap_ids=tuple(item["relevant_gap_ids"]),
                    source_quality=tuple(
                        quality[key]
                        for key in (
                            "currency",
                            "relevance",
                            "authority",
                            "accuracy",
                            "purpose",
                        )
                    ),
                    canonical_id=canonical,
                    publisher_id=source["publisher_id"],
                    acquired=source["acquisition_status"] == "acquired",
                    supports_or_challenges=(
                        item["supports_or_challenges"] and item["marginal_value"]
                    ),
                    derivative=item["derivative_of"] is not None,
                    improves_currency=item["improves_currency"],
                    improves_authority=item["improves_authority"],
                    resolves_contradiction=item["resolves_contradiction"],
                ),
                admitted_canonical_ids=frozenset(admitted_canonical_ids),
                admitted_publishers=frozenset(admitted_publishers),
            )
            admitted = decision.admitted
            admission_reason = decision.reason
            if len(admitted_ids) >= 8:
                admitted = False
                admission_reason = "source_limit"
        source["operational_assessment"] = item
        source["admitted"] = admitted
        source["admission_reason"] = admission_reason
        if admitted:
            admitted_ids.append(candidate_id)
            admitted_canonical_ids.add(canonical)
            admitted_publishers.add(source["publisher_id"])
    gap_results = []
    for item in assessment["gaps"]:
        supporting = [value for value in item["candidate_ids"] if value in admitted_ids]
        if not supporting:
            status = "open"
        elif set(supporting) != set(item["candidate_ids"]):
            status = "ambiguous"
        else:
            status = item["status"]
        gap_results.append({**item, "candidate_ids": supporting, "status": status})
    total_weight = sum(item["importance"] for item in claims)
    closed = {item["gap_id"] for item in gap_results if item["status"] == "closed"}
    closed_weight = sum(
        item["importance"] for item in claims if item["claim_id"] in closed
    )
    final_gaps = tuple(
        EvidenceGap(
            gap.gap_id,
            gap.importance,
            gap.closure_rule,
            gap.gap_id in closed,
        )
        for gap in gaps
    )
    stop = stop_reason(
        final_gaps,
        WorkState(
            searches=len(attempts),
            model_calls=int(planning is not None) + 1,
            admitted_sources=len(admitted_ids),
            elapsed_ms=round((time.monotonic() - started) * 1000),
            newly_closed_weight=closed_weight,
            quality_gain=any(
                item["quality"]["authority"] >= 2 for item in assessed.values()
            ),
            contradiction_gain=any(
                item["supports_or_challenges"] for item in assessed.values()
            ),
            publisher_gain=len(admitted_publishers) > 1,
        ),
    )
    public_candidates = [
        {key: value for key, value in item.items() if key != "reviewed_excerpt"}
        for item in candidates.values()
    ]
    policy_events = (
        *(
            {"type": "search", "query": item["query"], "purpose": item["purpose"]}
            for item in attempts
        ),
        *(
            {
                "type": "proposal",
                "gap_id": item["gap_id"],
                "admitted": item["admitted"],
                "reason": item["reason"],
            }
            for item in proposal_log
        ),
        *(
            {
                "type": "candidate",
                "candidate_id": item["candidate_id"],
                "admitted": item["admitted"],
            }
            for item in public_candidates
        ),
        *(
            {"type": "gap", "gap_id": item["gap_id"], "status": item["status"]}
            for item in gap_results
        ),
        {"type": "stop", "reason": stop},
    )
    event_digests = replay_policy_trace(tuple(policy_events))
    return {
        "schema_version": "enterprise-evaluation/w10-policy-trial/1",
        "case_id": case["case_id"],
        "challenge_type": case.get("challenge_type", case.get("category")),
        "policy": policy,
        "repetition": repetition,
        "status": "completed",
        "attempts": attempts,
        "proposals": proposal_log,
        "candidates": public_candidates,
        "gap_results": gap_results,
        "metrics": {
            "searches": len(attempts),
            "model_calls": int(planning is not None) + 1,
            "candidate_count": len(candidates),
            "acquired_count": sum(
                item["acquisition_status"] == "acquired" for item in candidates.values()
            ),
            "admitted_count": len(admitted_ids),
            "closed_weight": closed_weight,
            "total_weight": total_weight,
            "weighted_closure": closed_weight / total_weight,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
        },
        "stop_reason": stop,
        "orchestration": {
            "runtime": "langgraph",
            "event_count": len(event_digests),
            "event_digests": list(event_digests),
        },
        "planning_receipt": planning_receipt,
        "assessment_receipt": assessment_receipt,
        "blind_grade": {
            "candidate_order_seed_sha256": digest(str(blind_seed)),
            "policy_and_rank_labels_exposed": False,
        },
        "private_acquisitions": [
            {
                "candidate_id": digest(key)[:16],
                "canonical_url": key,
                "url": item["url"],
                "accessed_at": item.get("accessed_at", item["observed_at"]),
                "acquisition_status": item["acquisition_status"],
                "reviewed_bytes_sha256": item.get("reviewed_bytes_sha256"),
                "reviewed_excerpt": item.get("reviewed_excerpt", ""),
                "exclusion_reason": item.get("acquisition_error"),
            }
            for key, item in candidates.items()
        ],
    }


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", default=os.environ.get("GROKTOCRAWL_API_KEY", ""))
    parser.add_argument("--llm-base-url", default=os.environ.get("LLM_BASE_URL", ""))
    parser.add_argument("--llm-api-key", default=os.environ.get("LLM_API_KEY", ""))
    parser.add_argument("--model", default="local")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--result-limit", type=int, default=8)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument(
        "--policies", nargs="+", choices=POLICIES, default=list(POLICIES)
    )
    args = parser.parse_args()
    if not args.api_key or not args.llm_base_url or not args.llm_api_key:
        parser.error("API and LLM credentials are required")
    try:
        langgraph_version = version("langgraph")
    except PackageNotFoundError:
        parser.error("the isolated experiment environment needs langgraph==0.6.11")
    if langgraph_version != "0.6.11":
        parser.error(
            f"expected langgraph==0.6.11, found langgraph=={langgraph_version}"
        )
    started_at = datetime.now(UTC).isoformat()
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    records = args.output / "records"
    records.mkdir(exist_ok=True, mode=0o700)
    payload = json.loads(args.cases.read_text())
    work = build_work_order(
        payload["cases"], args.policies, args.repetitions, args.seed
    )
    order_payload = {
        "schema_version": "enterprise-evaluation/w10-work-order/1",
        "method": "seeded_case_shuffle_with_per_case_policy_rotation",
        "seed": args.seed,
        "entries": [
            {
                "position": position,
                "case_id": case["case_id"],
                "policy": policy,
                "repetition": repetition,
            }
            for position, (case, policy, repetition) in enumerate(work, 1)
        ],
    }
    atomic_json(args.output / "work-order.json", order_payload)
    work_order_sha256 = digest((args.output / "work-order.json").read_bytes())

    def execute(item: tuple[dict[str, Any], str, int]) -> dict[str, Any]:
        case, policy, repetition = item
        name = f"{case['case_id']}--{policy}--{repetition}.json"
        path = records / name
        private_path = args.output / "private-acquisitions"
        private_record = private_path / name
        if path.exists() and private_record.exists():
            return json.loads(path.read_text())
        try:
            with (
                httpx.Client(
                    base_url=args.base_url,
                    headers={"Authorization": f"Bearer {args.api_key}"},
                    timeout=180,
                ) as api,
                httpx.Client(
                    base_url=args.llm_base_url,
                    headers={"Authorization": f"Bearer {args.llm_api_key}"},
                    timeout=180,
                ) as llm,
            ):
                result = execute_trial(
                    case,
                    policy,
                    repetition,
                    api_client=api,
                    llm_client=llm,
                    model=args.model,
                    result_limit=args.result_limit,
                    seed=args.seed,
                )
                private = result.pop("private_acquisitions")
                private_path.mkdir(exist_ok=True, mode=0o700)
                atomic_json(private_record, private)
        except Exception as error:
            result = {
                "schema_version": "enterprise-evaluation/w10-policy-trial/1",
                "case_id": case["case_id"],
                "policy": policy,
                "repetition": repetition,
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error)[:1000],
            }
        atomic_json(path, result)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(execute, work))
    manifest = {
        "schema_version": "enterprise-evaluation/w10-policy-run/1",
        "cases_sha256": digest(args.cases.read_bytes()),
        "records": len(results),
        "completed": sum(item["status"] == "completed" for item in results),
        "failed": sum(item["status"] != "completed" for item in results),
        "policies": args.policies,
        "repetitions": args.repetitions,
        "result_limit": args.result_limit,
        "seed": args.seed,
        "work_order_sha256": work_order_sha256,
        "started_at": started_at,
        "completed_at": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "httpx": version("httpx"),
            "langgraph": langgraph_version,
            "model_requested": args.model,
            "api_route": "candidate_loopback",
            "llm_route": "openai_compatible",
            "runner_sha256": digest(Path(__file__).read_bytes()),
            "policy_sha256": digest(
                (
                    ROOT / "agent-svc/agent/experimental/bounded_adaptive_policy.py"
                ).read_bytes()
            ),
        },
    }
    atomic_json(args.output / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
