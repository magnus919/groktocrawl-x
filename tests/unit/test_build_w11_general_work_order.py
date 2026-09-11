from scripts.build_w11_general_work_order import build

CASES = {
    "cases": [
        {"case_id": "a", "challenge_type": "freshness"},
        {"case_id": "b", "challenge_type": "identity"},
    ]
}


def _summary(*, complete: bool = True) -> dict:
    return {
        "schema_version": "enterprise-evaluation/w10-summary/1",
        "complete": complete,
        "selected_challenge_types": ["freshness"],
    }


def test_build_maps_selected_types_and_counterbalances_arms() -> None:
    result = build(_summary(), CASES, seed=7, repetitions=3)
    assert result["policy_by_challenge_type"] == {
        "freshness": "full",
        "identity": "fixed",
    }
    assert len(result["entries"]) == 12
    for repetition in range(3):
        entries = [row for row in result["entries"] if row["repetition"] == repetition]
        for case_id in ("a", "b"):
            assert {row["arm"] for row in entries if row["case_id"] == case_id} == {
                "flat_http",
                "recorded_continuation",
            }


def test_build_rejects_partial_w10_summary() -> None:
    try:
        build(_summary(complete=False), CASES, seed=7, repetitions=3)
    except ValueError as error:
        assert "must be complete" in str(error)
    else:
        raise AssertionError("partial W10 summary was accepted")


def test_build_rejects_unknown_selected_type() -> None:
    summary = _summary()
    summary["selected_challenge_types"] = ["unknown"]
    try:
        build(summary, CASES, seed=7, repetitions=3)
    except ValueError as error:
        assert "unknown challenge type" in str(error)
    else:
        raise AssertionError("unknown challenge type was accepted")
