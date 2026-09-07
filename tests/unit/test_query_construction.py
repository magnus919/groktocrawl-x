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


@pytest.mark.asyncio
async def test_model_journey_executes_checks_and_audit_without_fixture_provenance():
    from agent.experimental.real_journey import research_from_sources

    calls = []

    async def complete(request):
        value = json.loads(request.payload)
        calls.append(value)
        if "schema" in value:
            content = proposal()
        else:
            assessment = value.get("check", {}).get("check_type") == "assessment"
            content = {
                "schema_version": "model-review-decision/1",
                "input_digest": value["input_digest"],
                "outcome": "supported" if assessment else "pass",
                "reason": "Scripted transport response for integration testing only.",
            }
        return ModelReply(json.dumps(content).encode(), "test-model", 1, 1)

    result = await research_from_sources(
        QUESTION,
        (CapturedSource("https://example.test/pilot", TEXT, "2026-09-06T00:00:00Z"),),
        complete=complete,
        scope_id="test-scope",
    )
    assert not result.candidate.fixture_only
    assert len(result.reports) == 3
    assert len({report.body for report in result.reports}) == 3
    assert len(calls) == 7  # construction, five checks, whole-render audit
    assert "reports" in calls[-1]
    assert len(calls[-1]["reports"]) == 3
    assert all(
        i.reviewer.kind == "model"
        for i in result.candidate.admitted.knowledge.verification_inputs
    )


@pytest.mark.asyncio
async def test_query_dispatches_acquisition_then_real_contract_journey():
    from agent.experimental.query_runner import run_query

    events = []

    async def search(query, limit):
        events.append("search")
        assert query == QUESTION and limit == 3
        return ("https://example.test/pilot",)

    async def acquire(url):
        events.append("acquire")
        return CapturedSource(url, TEXT, "2026-09-06T00:00:00Z")

    async def complete(request):
        events.append("model")
        value = json.loads(request.payload)
        content = (
            proposal()
            if "schema" in value
            else {
                "schema_version": "model-review-decision/1",
                "input_digest": value["input_digest"],
                "outcome": "supported"
                if value.get("check", {}).get("check_type") == "assessment"
                else "pass",
                "reason": "Scripted integration response.",
            }
        )
        return ModelReply(json.dumps(content).encode(), "test-model", 1, 1)

    result = await run_query(
        QUESTION,
        search=search,
        acquire=acquire,
        complete=complete,
        scope_id="test-scope",
    )
    assert not result.candidate.fixture_only
    assert events[:2] == ["search", "acquire"]
    assert events.count("model") == 7


@pytest.mark.asyncio
async def test_query_cancellation_during_search_prevents_acquisition():
    import asyncio

    from agent.experimental.query_runner import run_query

    started = asyncio.Event()
    calls = []

    async def search(query, limit):
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            asyncio.current_task().uncancel()
        return ("https://example.test/pilot",)

    async def acquire(url):
        calls.append(url)
        return CapturedSource(url, TEXT, "2026-09-06T00:00:00Z")

    async def complete(request):
        raise AssertionError("model must not run")

    task = asyncio.create_task(
        run_query(
            QUESTION,
            search=search,
            acquire=acquire,
            complete=complete,
            scope_id="test-scope",
        )
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("reject", ["semantic_support", "audit"])
async def test_real_journey_cannot_publish_after_negative_model_review(reject):
    from agent.experimental.real_journey import research_from_sources

    async def complete(request):
        value = json.loads(request.payload)
        if "schema" in value:
            content = proposal()
        else:
            kind = value.get("check", {}).get("check_type", "audit")
            content = {
                "schema_version": "model-review-decision/1",
                "input_digest": value["input_digest"],
                "outcome": "fail"
                if kind == reject
                else "supported"
                if kind == "assessment"
                else "pass",
                "reason": "Scripted negative-review control.",
            }
        return ModelReply(json.dumps(content).encode(), "test-model", 1, 1)

    with pytest.raises(ValueError):
        await research_from_sources(
            QUESTION,
            (
                CapturedSource(
                    "https://example.test/pilot", TEXT, "2026-09-06T00:00:00Z"
                ),
            ),
            complete=complete,
            scope_id="test-scope",
        )


def test_fixture_entry_point_still_rejects_model_reviewers():
    from agent.experimental.consolidated_example import example_journey
    from agent.experimental.consolidated_journey import ConsolidatedFixtureJourney
    from agent.experimental.model_review import ModelReviewAdapter

    async def complete(request):
        raise AssertionError("must not dispatch")

    fixture = example_journey()
    adapter = ModelReviewAdapter(provider="test", model="local", complete=complete)
    with pytest.raises(ValueError, match="requires fixture reviewers"):
        ConsolidatedFixtureJourney(
            context=fixture._context,
            checks=fixture._checks,
            acquisitions=fixture._acquire,
            verifier=adapter.reviewer,
            verify=fixture._verify,
            renderer=fixture._renderer,
            render=fixture._render,
            auditor=adapter.reviewer,
            audit=fixture._audit,
            artifact_set_id=fixture._artifact_set_id,
            clock=fixture._clock,
        )
