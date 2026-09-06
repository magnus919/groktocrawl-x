"""Corpus identities, descriptive statistics and the actual encoded size boundary."""

import base64
from uuid import uuid4

from agent.experimental.research_publication import admit_research_publication

from tests.storage.capacity_common import body_for, format_boundary_payload, summaries
from tests.storage.publication_fixture import CONTEXT
from tests.storage.research_publication_fixture import research_publication_payload
from tests.unit.test_research_publication import pinned as pinned_fixture


def test_unique_reproducible_exact_sized_corpus():
    first = body_for("sequential", 0, 0, 130)
    assert len(first) == 130
    assert first == body_for("sequential", 0, 0, 130)
    assert first != body_for("concurrent", 0, 0, 130)
    assert first != body_for("sequential", 1, 0, 130)
    assert first != body_for("sequential", 0, 1, 130)
    assert set(first) <= set(b"0123456789abcdef")
    assert len({first[:64], first[64:128]}) == 2


def test_summary_preserves_failed_denominator_and_nearest_rank():
    events = [
        {
            "event": "operation",
            "phase": "p",
            "kind": "read",
            "duration_seconds": n,
            "outcome": "success" if n < 20 else "TimeoutError",
        }
        for n in range(1, 21)
    ]
    result = summaries(events)["p:read"]
    assert result["attempted"] == 20
    assert result["succeeded"] == 19
    assert result["failed"] == 1
    assert result["median_seconds"] == 10.5
    assert result["nearest_rank_p95_seconds"] == 19
    assert summaries([]) == {}


def test_valid_publication_exceeds_export_encoding_budget():
    pinned = pinned_fixture.__wrapped__()
    identity = uuid4()
    raw = format_boundary_payload(
        research_publication_payload(pinned, identity, CONTEXT)
    )
    admitted = admit_research_publication(raw, pinned, identity, CONTEXT)
    assert admitted.size < 1024 * 1024
    # This member alone already exceeds the entire bundle budget.
    assert len(base64.b64encode(admitted.document.data)) > 1024 * 1024
