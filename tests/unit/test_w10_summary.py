import pytest

from scripts.run_w10_adaptive_policy import (
    build_work_order,
    trial_evidence_checkpoint,
)
from scripts.summarize_w10_adaptive_policy import aggregate, gate


def row(**overrides):
    value = {
        "status": "completed",
        "closed_weight": 6,
        "total_weight": 10,
        "closed_claims": 2,
        "total_claims": 3,
        "admitted": 5,
        "useful": 4,
        "followup_queries": 0,
        "unnecessary_followup_queries": 0,
        "unsupported_high_importance": 1,
        "within_bounds": True,
        "elapsed_ms": 1_000,
    }
    value.update(overrides)
    return value


def test_gate_requires_effect_precision_work_and_failure_guards():
    fixed = aggregate([row(closed_weight=5, useful=4, admitted=5)])
    full = aggregate(
        [
            row(
                closed_weight=7,
                useful=4,
                admitted=5,
                followup_queries=2,
                unnecessary_followup_queries=0,
            )
        ]
    )
    result = gate(full, fixed)
    assert result["passed"]
    assert result["closure_gain"] == pytest.approx(0.2)


def test_gate_fails_when_precision_is_undefined_or_queries_add_nothing():
    fixed = aggregate([row(closed_weight=5)])
    full = aggregate(
        [
            row(
                closed_weight=7,
                admitted=0,
                useful=0,
                followup_queries=2,
                unnecessary_followup_queries=2,
            )
        ]
    )
    result = gate(full, fixed)
    assert not result["passed"]
    assert not result["checks"]["precision_within_5pp"]
    assert not result["checks"]["unnecessary_queries_at_most_10pct"]


def test_work_order_rotates_each_policy_within_each_case():
    cases = [{"case_id": "a"}, {"case_id": "b"}]
    policies = ["fixed", "gap", "full"]
    first = build_work_order(cases, policies, 3, 20260911)
    assert first == build_work_order(cases, policies, 3, 20260911)
    for case in cases:
        positions = {policy: [] for policy in policies}
        for repetition in range(3):
            ordered = [
                policy
                for item, policy, rep in first
                if item["case_id"] == case["case_id"] and rep == repetition
            ]
            assert sorted(ordered) == sorted(policies)
            for position, policy in enumerate(ordered):
                positions[policy].append(position)
        assert all(len(set(values)) == 3 for values in positions.values())


def test_trial_checkpoint_preserves_failure_evidence_without_public_excerpts():
    public, private = trial_evidence_checkpoint(
        case={"case_id": "case-1", "challenge_type": "contradiction"},
        policy="full",
        repetition=1,
        stage="assessment_received",
        attempts=[{"query": "example", "result_count": 1}],
        proposals=[],
        candidates={
            "https://example.com/evidence": {
                "url": "https://example.com/evidence",
                "title": "Evidence",
                "observed_at": "2026-09-11T00:00:00+00:00",
                "accessed_at": "2026-09-11T00:00:01+00:00",
                "acquisition_status": "acquired",
                "reviewed_bytes_sha256": "abc",
                "reviewed_excerpt": "private source text",
            }
        },
    )

    assert public["stage"] == "assessment_received"
    assert public["attempts"] == [{"query": "example", "result_count": 1}]
    assert "reviewed_excerpt" not in public["candidates"][0]
    assert private[0]["reviewed_excerpt"] == "private source text"
