#!/usr/bin/env python3
"""Analyze W12.2 paired longitudinal results and frozen decision gates."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

SCORES = (
    "change_accuracy",
    "current_accuracy",
    "historical_preservation",
    "unresolved_accuracy",
    "usefulness",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trials = {
        record["trial_id"]: record
        for path in (args.run_dir / "public/trials").glob("*.json")
        if (record := json.loads(path.read_bytes())).get("status") == "completed"
    }
    grades = [
        record
        for path in (args.run_dir / "public/grades").glob("*.json")
        if (record := json.loads(path.read_bytes())).get("status") == "completed"
    ]
    paired: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for record in grades:
        trial = trials[record["trial_id"]]
        paired[(trial["case_id"], trial["repetition"])][trial["arm"]] = record["grade"]
    effects = []
    repetition_effects: dict[int, list[float]] = defaultdict(list)
    hard_failures = []
    for (case_id, repetition), arms in sorted(paired.items()):
        if set(arms) != {"control", "treatment"}:
            continue
        control = mean(arms["control"][score] for score in SCORES)
        treatment = mean(arms["treatment"][score] for score in SCORES)
        effect = treatment - control
        repetition_effects[repetition].append(effect)
        effects.append(
            {
                "case_id": case_id,
                "repetition": repetition,
                "control_score": control,
                "treatment_score": treatment,
                "effect_points": effect,
            }
        )
        grade = arms["treatment"]
        if grade["false_merge"] or grade["stale_current_leak"] or grade["lost_history"]:
            hard_failures.append({"case_id": case_id, "repetition": repetition, "grade": grade})
    by_repetition = {
        str(rep): round(mean(values), 3) for rep, values in repetition_effects.items()
    }
    repetitions_over_ten = sum(value >= 10 for value in by_repetition.values())
    grade_summary = json.loads((args.run_dir / "public/grade-summary.json").read_bytes())
    failure_rate = grade_summary["failed"] / max(1, grade_summary["completed"] + grade_summary["failed"])
    decision = (
        "adopt_narrow_thread_contract"
        if repetitions_over_ten >= 2 and not hard_failures and failure_rate < 0.10
        else "reject_or_revise"
    )
    result = {
        "schema_version": "research-thread-analysis/1",
        "decision": decision,
        "paired_count": len(effects),
        "mean_effect_points": round(mean(item["effect_points"] for item in effects), 3) if effects else None,
        "effect_points_by_repetition": by_repetition,
        "repetitions_at_or_above_10_points": repetitions_over_ten,
        "hard_failure_count": len(hard_failures),
        "hard_failures": hard_failures,
        "grade_failure_rate": round(failure_rate, 6),
        "effects": effects,
        "limitations": [
            "Model grading is blinded but not human adjudication.",
            "Efficiency gate requires receipt analysis before final adoption.",
            "The synthetic corpus establishes causal behavior, not production prevalence.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
