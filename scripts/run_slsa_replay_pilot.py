#!/usr/bin/env python3
"""Run the frozen SLSA replay packet through an operator-supplied Jev proxy.

The runner sends only per-stage first-pass state and the frozen proposal. It
does not send evaluator labels, future passages, the result pool, or source
blobs. No searches are dispatched, and provider requests are never retried.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import jev_continuation_request_builder as builder

PACKET_SHA256 = "bf080316bf2470d068b7207df4718971a385dbcc517450f802728a062815bea9"
MAX_REQUESTS = 11
CASE_COUNT = 4


def _finite_nonnegative(value: Any) -> float | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value < 0
    ):
        return None
    return float(value)


def _call(proxy: list[str], plan: builder.RequestPlan) -> tuple[dict[str, Any], Any]:
    try:
        process = subprocess.run(
            proxy,
            input=plan.serialized,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "proxy_or_timeout_failure", "error_type": type(exc).__name__}, None
    if process.returncode:
        return {"status": "proxy_process_failure", "returncode": process.returncode}, None
    try:
        response = json.loads(process.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"status": "invalid_proxy_json"}, None
    checked = builder.validate_noul_response(response, plan)
    if isinstance(checked, builder.Abstention):
        return {"status": "unevaluated_response", "reason": checked.reason}, None
    receipt: dict[str, Any] = {
        "status": "evaluated",
        "model": checked.model,
        "request_sha256": checked.request_sha256,
        "response_sha256": hashlib.sha256(process.stdout).hexdigest(),
        "probabilities": dict(checked.probabilities),
        "elapsed_ms": _finite_nonnegative(response.get("_elapsed_ms")),
    }
    raw_usage = response.get("usage")
    if isinstance(raw_usage, dict):
        usage = {
            key: value
            for key in ("input_tokens", "output_tokens", "total_tokens")
            if isinstance((value := raw_usage.get(key)), int)
            and not isinstance(value, bool)
            and value >= 0
        }
        if usage:
            receipt["usage"] = usage
    return receipt, checked


def run(packet_path: Path, corpus_root: Path, proxy: list[str]) -> dict[str, Any]:
    packet_bytes = packet_path.read_bytes()
    packet_hash = hashlib.sha256(packet_bytes).hexdigest()
    if packet_hash != PACKET_SHA256:
        raise ValueError("case packet digest differs from signed freeze")
    packet = json.loads(packet_bytes)
    if (
        packet.get("schema_version") != "jev-slsa-replay-pilot/2"
        or packet.get("study_id") != "jev-slsa-deterministic-replay-2026-10-03"
        or len(packet.get("cases", [])) != CASE_COUNT
        or packet.get("call_budget", {}).get("hard_max_total_requests") != MAX_REQUESTS
    ):
        raise ValueError("unsupported packet or budget")
    source_files = {
        row["result_id"]: row["markdown_file"]
        for row in packet["corpus"]["source_pages"]
    }
    results: dict[str, Any] = {
        "study_id": packet["study_id"],
        "case_packet_sha256": packet_hash,
        "requested_model": builder.MODEL,
        "requests_attempted": 0,
        "requests_unevaluated": 0,
        "searches_dispatched": 0,
        "cases": [],
    }

    def call(
        case: dict[str, Any],
        stage_key: str,
        plan: builder.RequestPlan,
    ) -> tuple[dict[str, Any], Any]:
        if results["requests_attempted"] >= MAX_REQUESTS:
            raise RuntimeError("frozen call budget exhausted")
        expected = case["frozen_request_sha256"][stage_key]
        if hashlib.sha256(plan.serialized).hexdigest() != expected:
            raise ValueError(f"{case['case_id']} request differs from frozen digest")
        results["requests_attempted"] += 1
        receipt, checked = _call(proxy, plan)
        receipt["request_sha256"] = expected
        if receipt["status"] == "evaluated":
            model = receipt["model"]
            if results.get("returned_model") not in (None, model):
                receipt = {"status": "unevaluated_response", "reason": "model revision changed"}
                checked = None
            else:
                results["returned_model"] = model
        if receipt["status"] != "evaluated":
            results["requests_unevaluated"] += 1
        return receipt, checked

    for case in packet["cases"]:
        state = case["state"]
        hypothesis = case["research_agent_proposal"]
        documents: dict[str, str] = {}
        for source in state["first_pass"]["sources"]:
            source_id = source["source_id"]
            filename = source_files.get(source_id)
            if not filename:
                raise ValueError(f"missing source identity for {source_id}")
            document = (corpus_root / filename).read_text()
            if hashlib.sha256(document.encode()).hexdigest() != source["source_sha256"]:
                raise ValueError(f"first-pass source digest mismatch for {source_id}")
            documents[source_id] = document

        row: dict[str, Any] = {"case_id": case["case_id"]}
        stage1 = builder.build_sufficiency_request(state)
        if isinstance(stage1, builder.Abstention):
            row["stage1"] = {"status": "pre_call_abstention", "reason": stage1.reason}
            row["stage3"] = {"status": "skipped_after_stage1_abstention"}
            results["cases"].append(row)
            continue
        row["stage1"], _ = call(case, "stage1_sufficiency", stage1)
        if row["stage1"]["status"] != "evaluated":
            row["stage3"] = {"status": "skipped_after_stage1_failure"}
            results["cases"].append(row)
            continue

        stage3 = builder.build_hypothesis_review_request(state, [hypothesis], documents)
        if isinstance(stage3, builder.Abstention):
            row["stage3"] = {"status": "pre_call_abstention", "reason": stage3.reason}
            results["cases"].append(row)
            continue
        row["stage3"], checked3 = call(case, "stage3_hypothesis_review", stage3)
        if row["stage3"]["status"] != "evaluated" or checked3 is None:
            row["stage4"] = {"status": "skipped_after_stage3_failure"}
            results["cases"].append(row)
            continue

        probability = checked3.probabilities["q0000"]
        if probability <= 0.5:
            row["stage4"] = {
                "status": "skipped_by_frozen_binary_argmax",
                "stage3_yes_probability": probability,
            }
        elif results["requests_attempted"] >= MAX_REQUESTS:
            row["stage4"] = {
                "status": "not_called_budget_exhausted",
                "stage3_yes_probability": probability,
            }
        else:
            stage4 = builder.build_addressability_request(
                state,
                hypothesis,
                documents,
                stage3_plan=stage3,
                stage3_response=checked3,
                stage3_question_id="q0000",
                policy_qualified_hypothesis_id=hypothesis["hypothesis_id"],
            )
            if isinstance(stage4, builder.Abstention):
                row["stage4"] = {"status": "pre_call_abstention", "reason": stage4.reason}
            else:
                row["stage4"], _ = call(
                    case, "stage4_addressability_if_stage3_positive", stage4
                )
        results["cases"].append(row)

    results["requests_validated"] = (
        results["requests_attempted"] - results["requests_unevaluated"]
    )
    results["status"] = "completed"
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("proxy", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.proxy and args.proxy[0] == "--":
        args.proxy = args.proxy[1:]
    if not args.proxy:
        parser.error("supply operator-configured proxy argv after --")
    descriptor = os.open(
        args.output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "w+", encoding="utf-8") as output:
        output.write('{"status":"running_incomplete"}\n')
        output.flush()
        os.fsync(output.fileno())
        try:
            result = run(args.packet, args.corpus, args.proxy)
        except Exception as exc:
            output.seek(0)
            output.truncate()
            output.write(json.dumps({
                "status": "failed_incomplete",
                "error_type": type(exc).__name__,
            }, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())
            raise
        output.seek(0)
        output.truncate()
        output.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())
    print(json.dumps({
        key: result[key]
        for key in (
            "study_id",
            "requests_attempted",
            "requests_validated",
            "requests_unevaluated",
            "searches_dispatched",
            "status",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
