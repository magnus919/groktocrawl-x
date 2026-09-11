from agent.experimental.bounded_adaptive_policy import (
    CandidateAssessment,
    EvidenceGap,
    QueryProposal,
    WorkState,
    admit_candidate,
    gate_proposal,
    intent_similarity,
    stop_reason,
)


def gap(*, closed: bool = False) -> EvidenceGap:
    return EvidenceGap("quality", 3, "Measured escaped-defect quality effect", closed)


def test_proposal_gate_requires_open_gap_novel_intent_and_topic_connection():
    proposal = QueryProposal(
        "escaped defect study coding agents",
        "quality",
        "A measured escaped-defect comparison",
        "missing_support",
    )
    assert gate_proposal(
        proposal,
        original_query="Do coding agents improve delivery quality?",
        gaps=(gap(),),
        prior_queries=("coding agent productivity evidence",),
    ).admitted
    assert not gate_proposal(
        proposal,
        original_query="Do coding agents improve delivery quality?",
        gaps=(gap(closed=True),),
        prior_queries=(),
    ).admitted


def test_proposal_gate_rejects_duplicate_and_drift():
    duplicate = QueryProposal(
        "coding agent productivity evidence",
        "quality",
        "comparison",
        "missing_support",
    )
    assert intent_similarity(duplicate.query, "coding agent productivity evidence") == 1
    assert (
        gate_proposal(
            duplicate,
            original_query="coding agents",
            gaps=(gap(),),
            prior_queries=("coding agent productivity evidence",),
        ).reason
        == "duplicate_intent"
    )
    drift = QueryProposal("weather forecast", "quality", "forecast", "missing_support")
    assert (
        gate_proposal(
            drift,
            original_query="coding agents",
            gaps=(gap(),),
            prior_queries=(),
        ).reason
        == "topic_drift"
    )


def test_candidate_admission_separates_availability_relevance_and_value():
    useful = CandidateAssessment(
        "source-1",
        ("quality",),
        (2, 2, 2, 2, 1),
        "canonical-1",
        "publisher-1",
        True,
        True,
    )
    assert (
        admit_candidate(
            useful,
            admitted_canonical_ids=frozenset(),
            admitted_publishers=frozenset(),
        ).reason
        == "admitted_claim_value"
    )
    assert (
        admit_candidate(
            useful,
            admitted_canonical_ids=frozenset({"canonical-1"}),
            admitted_publishers=frozenset(),
        ).reason
        == "canonical_duplicate"
    )


def test_stop_order_is_reproducible_from_recorded_state():
    open_gap = (gap(),)
    closed_gap = (gap(closed=True),)
    state = WorkState(2, 1, 2, 1_000, 0, False, False, False)
    assert stop_reason(closed_gap, state) == "all_gaps_closed"
    assert stop_reason(open_gap, state) == "no_marginal_gain"
    assert (
        stop_reason(open_gap, WorkState(3, 1, 2, 1_000, 1, False, False, False))
        == "search_limit"
    )
