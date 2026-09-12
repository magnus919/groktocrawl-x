import pytest

from scripts.record_w10_policy_selection import build_selection

SHA = "a" * 64
PRIMARY = {
    "schema_version": "enterprise-evaluation/w10-summary/1",
    "complete": True,
    "selected_challenge_types": ["freshness"],
}
ADJUDICATION = {
    "schema_version": "enterprise-evaluation/w10-adjudication-analysis/1",
    "primary_summary_sha256": SHA,
    "decision_changed": False,
}
ACCOUNTING = {
    "schema_version": "enterprise-evaluation/w10-public-accounting/1",
    "complete": True,
    "inputs": {"summary_sha256": SHA},
}
CASES = {
    "cases": [
        {"challenge_type": "freshness"},
        {"challenge_type": "identity"},
    ]
}
INPUTS = {
    "primary_summary": SHA,
    "adjudication_analysis": "b" * 64,
    "accounting": "c" * 64,
    "challenge_cases": "d" * 64,
}


def build(outcome="bounded_recovery", selected=None, **changes):
    values = {
        "primary": PRIMARY,
        "adjudication": ADJUDICATION,
        "accounting": ACCOUNTING,
        "cases": CASES,
        "outcome": outcome,
        "selected_types": ["freshness"] if selected is None else selected,
        "rationale": "Observed decision",
        "reversal_condition": "A repeated study crosses the frozen boundary",
        "input_digests": INPUTS,
    }
    values.update(changes)
    return build_selection(**values)


def test_bounded_selection_is_bound_and_authorizes_w11():
    result = build()
    assert result["w11_measurement_authorized"] is True
    assert result["selected_challenge_types"] == ["freshness"]
    assert result["adr"] == "ADR-0081"
    assert result["inputs"] == INPUTS


def test_fixed_selection_has_no_adaptive_types():
    result = build("keep_fixed_retrieval", selected=[])
    assert result["w11_measurement_authorized"] is True
    assert result["selected_challenge_types"] == []


def test_decision_changing_sensitivity_requires_followup():
    changed = {**ADJUDICATION, "decision_changed": True}
    with pytest.raises(ValueError, match="requires a follow-up"):
        build(adjudication=changed)
    result = build(
        "run_followup_experiment", selected=[], adjudication=changed
    )
    assert result["w11_measurement_authorized"] is False


def test_adaptive_outcomes_cannot_exceed_primary_evidence():
    with pytest.raises(ValueError, match="exceeds the primary"):
        build(selected=["identity"])
    with pytest.raises(ValueError, match="every type"):
        build("full_bounded_policy", selected=["freshness", "identity"])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("primary", {**PRIMARY, "complete": False}, "must be complete"),
        ("accounting", {**ACCOUNTING, "complete": False}, "must be complete"),
        (
            "adjudication",
            {**ADJUDICATION, "primary_summary_sha256": "e" * 64},
            "not bound",
        ),
    ],
)
def test_incomplete_or_unbound_inputs_fail_closed(field, value, message):
    with pytest.raises(ValueError, match=message):
        build(**{field: value})
