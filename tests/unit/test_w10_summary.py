import pytest

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
