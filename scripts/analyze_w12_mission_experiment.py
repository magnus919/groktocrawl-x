#!/usr/bin/env python3
"""Compute the frozen W12.1 decision gates from validated run evidence."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent-svc"))

from agent.experimental.mission_experiment import (
    sealed_candidate_id,
)
from agent.experimental.research_mission import load_mission_experiment_corpus

TARGET_STRATA = {"ambiguous", "compound"}


def load(path: Path) -> Any:
    return json.loads(path.read_bytes())


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[rank]


def relative_reduction(control: float, treatment: float) -> float | None:
    if control == 0:
        return 0.0 if treatment == 0 else -math.inf
    return (control - treatment) / control


def usage_cost(receipt: dict[str, Any]) -> float:
    usage = receipt.get("usage") or {}
    value = usage.get("cost")
    return float(value) if isinstance(value, int | float) else 0.0


def analyze(run_dir: Path) -> dict[str, Any]:
    experiment_dir = ROOT / "docs/experiments/research-mission"
    source_path = ROOT / "docs/experiments/enterprise-evaluation/corpus.json"
    corpus = load_mission_experiment_corpus(
        experiment_dir / "w12.1-cases.json", source_corpus_path=source_path
    )
    cases = {item.case_id: item for item in corpus.cases}

    grades = {
        path.stem: load(path)["grade"]
        for path in (run_dir / "public/grades").glob("*.json")
        if load(path).get("status") == "completed"
    }
    trial_rows: list[dict[str, Any]] = []
    for path in sorted((run_dir / "public/trials").glob("*.json")):
        trial = load(path)
        if trial.get("status") != "completed":
            continue
        case = cases[trial["case_id"]]
        grade = grades[sealed_candidate_id(trial["trial_id"])]
        obligation_weights = {
            item.obligation_id: item.weight
            for item in case.reference_mission.obligations
        }
        closed_weight = sum(
            obligation_weights[key]
            for key, value in grade["obligation_grades"].items()
            if value["status"] == "closed"
        )
        total_weight = sum(obligation_weights.values())
        trial_rows.append(
            {
                "trial_id": trial["trial_id"],
                "candidate_id": sealed_candidate_id(trial["trial_id"]),
                "case_id": case.case_id,
                "stratum": case.stratum,
                "arm": trial["arm"],
                "repetition": trial["repetition"],
                "closed_weight": closed_weight,
                "total_weight": total_weight,
                "weighted_coverage": closed_weight / total_weight,
                "equal_weight_coverage": sum(
                    value["status"] == "closed"
                    for value in grade["obligation_grades"].values()
                )
                / len(grade["obligation_grades"]),
                "scope_violations": len(grade["scope_violations"]),
                "material_scope_violations": sum(
                    item["severity"] == "material" for item in grade["scope_violations"]
                ),
                "decision_usefulness": grade["decision_usefulness"],
                "hard_boundary_failure": grade["hard_boundary_failure"],
                "supported_claim_rate": (
                    grade["supported_material_claims"] / grade["total_material_claims"]
                    if grade["total_material_claims"]
                    else None
                ),
                "latency_ms": trial["receipt"]["latency_ms"],
                "cost": usage_cost(trial["receipt"]),
            }
        )

    by_pair = {
        (row["case_id"], row["repetition"], row["arm"]): row for row in trial_rows
    }
    repetition_gates: list[dict[str, Any]] = []
    for repetition in (1, 2, 3):
        target = [
            row
            for row in trial_rows
            if row["repetition"] == repetition and row["stratum"] in TARGET_STRATA
        ]
        arms: dict[str, dict[str, float]] = {}
        for arm in ("control", "treatment"):
            rows = [row for row in target if row["arm"] == arm]
            arms[arm] = {
                "coverage": sum(row["closed_weight"] for row in rows)
                / sum(row["total_weight"] for row in rows),
                "scope_violations": float(sum(row["scope_violations"] for row in rows)),
            }
        coverage_gain = arms["treatment"]["coverage"] - arms["control"]["coverage"]
        reduction = relative_reduction(
            arms["control"]["scope_violations"],
            arms["treatment"]["scope_violations"],
        )
        repetition_gates.append(
            {
                "repetition": repetition,
                "control": arms["control"],
                "treatment": arms["treatment"],
                "coverage_gain": coverage_gain,
                "scope_violation_relative_reduction": reduction,
                "passes": coverage_gain >= 0.10
                and reduction is not None
                and reduction >= 0.30,
            }
        )

    paired_rows = []
    for case in corpus.cases:
        for repetition in (1, 2, 3):
            control = by_pair[(case.case_id, repetition, "control")]
            treatment = by_pair[(case.case_id, repetition, "treatment")]
            paired_rows.append(
                {
                    "case_id": case.case_id,
                    "stratum": case.stratum,
                    "repetition": repetition,
                    "coverage_change": treatment["weighted_coverage"]
                    - control["weighted_coverage"],
                    "scope_violation_change": treatment["scope_violations"]
                    - control["scope_violations"],
                    "decision_usefulness_change": treatment["decision_usefulness"]
                    - control["decision_usefulness"],
                }
            )

    arm_ops: dict[str, Any] = {}
    for arm in ("control", "treatment"):
        rows = [row for row in trial_rows if row["arm"] == arm]
        arm_ops[arm] = {
            "p95_latency_ms": percentile([row["latency_ms"] for row in rows], 0.95),
            "total_cost": sum(row["cost"] for row in rows),
            "hard_boundary_failures": sum(row["hard_boundary_failure"] for row in rows),
        }
    latency_increase = (
        arm_ops["treatment"]["p95_latency_ms"] / arm_ops["control"]["p95_latency_ms"]
        - 1
    )
    cost_increase = (
        arm_ops["treatment"]["total_cost"] / arm_ops["control"]["total_cost"] - 1
        if arm_ops["control"]["total_cost"]
        else None
    )
    target_gate = sum(row["passes"] for row in repetition_gates) >= 2
    anchor_regression = any(
        row["stratum"] == "straightforward" and row["decision_usefulness_change"] < -2
        for row in paired_rows
    )
    operational_gate = latency_increase <= 0.25 and (
        cost_increase is None or cost_increase <= 0.25
    )
    boundary_gate = arm_ops["treatment"]["hard_boundary_failures"] == 0
    if target_gate and operational_gate and boundary_gate:
        disposition = (
            "adopt_universally" if not anchor_regression else "adopt_selectively"
        )
    else:
        disposition = "reject"

    intake_grades = [
        load(path)["grade"]
        for path in (run_dir / "public/intake-grades").glob("*.json")
        if load(path).get("status") == "completed"
    ]
    intake = {
        "grade_count": len(intake_grades),
        "action_accuracy": statistics.mean(
            int(item["action_correct"]) for item in intake_grades
        ),
        "mean_required_field_recall": statistics.mean(
            item["required_field_recall"] for item in intake_grades
        ),
        "hard_boundary_failures": sum(
            item["hard_boundary_failure"] for item in intake_grades
        ),
        "total_correction_actions": sum(
            len(item["correction_actions"]) for item in intake_grades
        ),
    }
    return {
        "schema_version": "research-mission-analysis/1",
        "trial_count": len(trial_rows),
        "paired_case_repetitions": paired_rows,
        "repetition_gates": repetition_gates,
        "operations": {
            **arm_ops,
            "latency_increase": latency_increase,
            "cost_increase": cost_increase,
        },
        "gates": {
            "target_effect": target_gate,
            "anchor_regression": anchor_regression,
            "operational": operational_gate,
            "hard_boundary": boundary_gate,
        },
        "intake": intake,
        "disposition": disposition,
    }


def render_markdown(analysis: dict[str, Any]) -> str:
    gates = analysis["gates"]
    intake = analysis["intake"]
    lines = [
        "# W12.1 Research Mission outcome",
        "",
        f"Decision: **{analysis['disposition'].replace('_', ' ')}**",
        "",
        "## Frozen gates",
        "",
        f"- Difficult-case practical effect: {'pass' if gates['target_effect'] else 'fail'}",
        f"- Straightforward-case regression: {'present' if gates['anchor_regression'] else 'absent'}",
        f"- Latency and cost: {'pass' if gates['operational'] else 'fail'}",
        f"- Hard boundary: {'pass' if gates['hard_boundary'] else 'fail'}",
        "",
        "## Intake",
        "",
        f"- Action accuracy: {intake['action_accuracy']:.1%}",
        f"- Mean required-field recall: {intake['mean_required_field_recall']:.1f}/100",
        f"- Hard boundary failures: {intake['hard_boundary_failures']}",
        f"- Required correction actions: {intake['total_correction_actions']}",
        "",
        "## Repetition-level difficult-case results",
        "",
        "| Repetition | Coverage gain | Scope-violation reduction | Gate |",
        "|---:|---:|---:|---|",
    ]
    for row in analysis["repetition_gates"]:
        reduction = row["scope_violation_relative_reduction"]
        rendered_reduction = "n/a" if reduction is None else f"{reduction:.1%}"
        lines.append(
            f"| {row['repetition']} | {row['coverage_gain']:.1%} | "
            f"{rendered_reduction} | {'pass' if row['passes'] else 'fail'} |"
        )
    lines.extend(
        [
            "",
            "This report is a mechanical rendering of the retained grades. Case-level ",
            "results, raw receipts, failed attempts, and sensitivity review remain part ",
            "of the evidence packet and must be reviewed before an ADR is accepted.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run_dir)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.output_markdown.write_text(render_markdown(result))
    print(result["disposition"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
