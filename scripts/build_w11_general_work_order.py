#!/usr/bin/env python3
"""Build the W11 A0/A1 work order from a completed W10 decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

ARMS = ("flat_http", "recorded_continuation")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(
    summary: dict[str, Any], cases: dict[str, Any], *, seed: int, repetitions: int
) -> dict[str, Any]:
    if summary.get("schema_version") != "enterprise-evaluation/w10-summary/1":
        raise ValueError("unsupported W10 summary schema")
    if summary.get("complete") is not True:
        raise ValueError("W10 must be complete before the W11 work order is built")
    if repetitions != 3:
        raise ValueError("the frozen W11 protocol requires exactly three repetitions")
    selected = set(summary.get("selected_challenge_types", []))
    known_types = {str(case["challenge_type"]) for case in cases.get("cases", [])}
    if not selected <= known_types:
        raise ValueError("W10 selected an unknown challenge type")

    policy_by_type = {
        challenge_type: "full" if challenge_type in selected else "fixed"
        for challenge_type in sorted(known_types)
    }
    entries: list[dict[str, Any]] = []
    case_rows = sorted(cases["cases"], key=lambda item: str(item["case_id"]))
    for repetition in range(repetitions):
        ordered = list(case_rows)
        random.Random(seed + repetition).shuffle(ordered)
        for position, case in enumerate(ordered):
            first = (position + repetition) % 2
            arm_order = ARMS[first:] + ARMS[:first]
            for arm in arm_order:
                entries.append(
                    {
                        "position": len(entries) + 1,
                        "case_id": case["case_id"],
                        "challenge_type": case["challenge_type"],
                        "repetition": repetition,
                        "arm": arm,
                        "control_policy": policy_by_type[case["challenge_type"]],
                    }
                )
    return {
        "schema_version": "enterprise-evaluation/w11-general-work-order/1",
        "seed": seed,
        "repetitions": repetitions,
        "arms": list(ARMS),
        "policy_by_challenge_type": policy_by_type,
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w10-summary", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11052026)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    summary = json.loads(args.w10_summary.read_text())
    cases = json.loads(args.cases.read_text())
    result = build(summary, cases, seed=args.seed, repetitions=args.repetitions)
    result["inputs"] = {
        "w10_summary_sha256": digest(args.w10_summary),
        "cases_sha256": digest(args.cases),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"entries": len(result["entries"]), "policy_by_challenge_type": result["policy_by_challenge_type"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
