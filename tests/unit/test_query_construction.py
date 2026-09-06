"""Construction cannot substitute model-authored provenance or altered evidence."""

import json
from datetime import UTC, datetime

import pytest
from agent.experimental.model_review import ModelReply
from agent.experimental.query_construction import CapturedSource, construct_research

QUESTION = "What does the pilot establish?"
TEXT = "Pilot lead time fell. Causation is unproven."


def proposal():
    return {
        "schema_version": "research-construction/1",
        "evidence": [{"evidence_id": "e1", "snapshot_id": "source-1", "quote": TEXT}],
        "claims": [
            {
                "claim_id": "c1",
                "text": "The captured note reports lower lead time without establishing causation.",
                "kind": "source_statement",
                "qualifiers": ["One captured pilot note"],
                "temporal_scope": "historical",
            }
        ],
        "relationships": [
            {
                "relationship_id": "r1",
                "kind": "supports",
                "source_id": "e1",
                "target_id": "c1",
                "rationale": "The captured text states both facts.",
                "rule": None,
                "assumptions": [],
            }
        ],
        "questions": [
            {
                "question_id": "question-root",
                "question": QUESTION,
                "status": "answered",
                "report_claim_id": "c1",
            }
        ],
        "conflicts": [],
    }


async def run(value, text=TEXT):
    async def complete(request):
        assert request.requested_model == "local"
        return ModelReply(json.dumps(value).encode(), "local", None, None)

    return await construct_research(
        QUESTION,
        (CapturedSource("https://example.test/pilot", text, "2026-09-06T00:00:00Z"),),
        complete=complete,
        scope_id="owner",
        clock=lambda: datetime(2026, 9, 7, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_constructs_unverified_context_with_server_owned_sources():
    result = await run(proposal())
    assert result.context.objective == QUESTION
    assert result.context.snapshots[0].published_at is None
    assert result.context.evidence[0].start == 0
    assert result.context.evidence[0].end == len(TEXT)
    assert result.context.scope_id == "owner"
    assert not hasattr(result.context, "verifications")
    assert result.model_reply.resolved_model == "local"
    source = await result.resolve(result.context.snapshots[0].content_ref)
    assert source.body == TEXT.encode()


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["quote", "question", "scope", "source", "human"])
async def test_rejects_model_changes_to_evidence_or_authority(mutation):
    value = proposal()
    if mutation == "quote":
        value["evidence"][0]["quote"] = "Invented"
    elif mutation == "question":
        value["questions"][0]["question"] = "Different question"
    elif mutation == "source":
        value["evidence"][0]["snapshot_id"] = "foreign"
    else:
        value["scope_id" if mutation == "scope" else "human_approved"] = "forged"
    with pytest.raises(ValueError):
        await run(value)


@pytest.mark.asyncio
async def test_ambiguous_quote_requires_explicit_new_construction():
    with pytest.raises(ValueError, match="ambiguous"):
        await run(proposal(), TEXT + TEXT)
