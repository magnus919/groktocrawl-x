#!/usr/bin/env python3
"""Validate closure, replay, and blinding for a W12.1 downstream run."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent-svc"))

from agent.experimental.mission_experiment import (
    WorkItem,
    build_downstream_prompt,
    sealed_candidate_id,
    sealed_grade_candidate,
    validate_downstream_result,
)
from agent.experimental.research_mission import load_mission_experiment_corpus


def load(path: Path) -> Any:
    return json.loads(path.read_bytes())


def source_index(path: Path) -> dict[str, dict[str, str]]:
    return {
        item["source_id"]: {
            "source_id": item["source_id"],
            "title": item["title"],
            "text": item["text"],
        }
        for item in load(path)["sources"]
    }


def validate_run(run_dir: Path, *, expected_revision: str) -> list[str]:
    issues: list[str] = []
    experiment_dir = ROOT / "docs/experiments/research-mission"
    source_path = ROOT / "docs/experiments/enterprise-evaluation/corpus.json"
    corpus = load_mission_experiment_corpus(
        experiment_dir / "w12.1-cases.json", source_corpus_path=source_path
    )
    cases = {item.case_id: item for item in corpus.cases}
    sources = source_index(source_path)
    work_payload = load(experiment_dir / "w12.1-work-order.json")
    work = tuple(WorkItem(**item) for item in work_payload["trials"])
    manifest_path = run_dir / "public/run-manifest.json"
    summary_path = run_dir / "public/run-summary.json"
    if not manifest_path.exists() or not summary_path.exists():
        return ["run manifest or summary is missing"]
    manifest = load(manifest_path)
    summary = load(summary_path)
    if manifest.get("source_revision") != expected_revision:
        issues.append("run manifest source revision differs from the expected revision")
    if manifest.get("work_order_sha256") != work_payload["trials_sha256"]:
        issues.append("run manifest work order differs from the frozen work order")

    completed = 0
    candidate_ids: set[str] = set()
    for item in work:
        public_path = run_dir / "public/trials" / f"{item.trial_id}.json"
        private_path = run_dir / "private/trials" / f"{item.trial_id}.json"
        if not public_path.exists() or not private_path.exists():
            issues.append(f"{item.trial_id}: public or private trial record is missing")
            continue
        if stat.S_IMODE(private_path.stat().st_mode) != 0o600:
            issues.append(f"{item.trial_id}: private record mode is not 0600")
        public = load(public_path)
        private = load(private_path)
        expected_fields = {
            "trial_id": item.trial_id,
            "case_id": item.case_id,
            "arm": item.arm,
            "repetition": item.repetition,
            "position": item.position,
        }
        if any(public.get(key) != value for key, value in expected_fields.items()):
            issues.append(
                f"{item.trial_id}: public trial identity differs from work order"
            )
        if public.get("status") != "completed":
            issues.append(f"{item.trial_id}: trial is not completed")
            continue
        completed += 1
        receipt = private.get("receipt") or {}
        content = private.get("raw_completion")
        if not isinstance(content, str):
            issues.append(f"{item.trial_id}: raw completion is missing")
            continue
        if (
            receipt.get("response_sha256")
            != hashlib.sha256(content.encode()).hexdigest()
        ):
            issues.append(f"{item.trial_id}: response digest does not close")
        if public.get("receipt") != receipt:
            issues.append(f"{item.trial_id}: public and private receipts differ")
        case = cases[item.case_id]
        source_pack = tuple(sources[source_id] for source_id in case.source_ids)
        expected_prompt = build_downstream_prompt(
            case, sources=source_pack, arm=item.arm
        )
        if private.get("prompt") != expected_prompt:
            issues.append(
                f"{item.trial_id}: retained prompt differs from frozen inputs"
            )
        try:
            validated = validate_downstream_result(
                json.loads(content), case=case, arm=item.arm
            )
        except Exception as error:
            issues.append(f"{item.trial_id}: raw completion is invalid: {error}")
            continue
        candidate_id = sealed_candidate_id(item.trial_id)
        if any(token in candidate_id for token in (item.arm, item.case_id)):
            issues.append(f"{item.trial_id}: sealed identity reveals allocation")
        expected_candidate = sealed_grade_candidate(
            validated, candidate_id=candidate_id
        )
        if public.get("sealed_candidate") != expected_candidate:
            issues.append(f"{item.trial_id}: sealed candidate does not replay")
        if candidate_id in candidate_ids:
            issues.append(f"{item.trial_id}: sealed candidate identity is duplicated")
        candidate_ids.add(candidate_id)

    if summary.get("attempted") != len(work):
        issues.append("summary attempted count differs from frozen work order")
    if summary.get("completed") != completed:
        issues.append("summary completed count differs from validated trials")
    if summary.get("failed") != 0:
        issues.append("summary contains failed trials")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--expected-revision", required=True)
    args = parser.parse_args()
    issues = validate_run(args.run_dir, expected_revision=args.expected_revision)
    print(json.dumps({"valid": not issues, "issues": issues}, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
