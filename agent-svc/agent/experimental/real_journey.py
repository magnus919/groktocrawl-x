"""Model construction and executed review over caller-acquired source material."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from .checked_knowledge import CheckedKnowledge
from .consolidated_journey import ConsolidatedJourney, JourneyResult, RenderedReport
from .knowledge import text_digest
from .knowledge_checks import KnowledgeCheckInput, ModelReviewer
from .knowledge_context import KnowledgeContext
from .model_review import Complete, ModelReviewAdapter
from .query_construction import CapturedSource, construct_research
from .render_manifest import ManifestArtifact, Renderer


def _evidence(context: KnowledgeContext, claim_id: str) -> list[str]:
    closure = {claim_id}
    while True:
        extended = closure | {
            r.target_id
            for r in context.relationships
            if r.kind == "derived_from" and r.source_id in closure
        }
        if extended == closure:
            break
        closure = extended
    ids = {
        r.source_id
        for r in context.relationships
        if r.kind in {"supports", "contradicts"} and r.target_id in closure
    }
    return [e.evidence_id for e in context.evidence if e.evidence_id in ids]


def review_plan(
    context: KnowledgeContext, reviewer: ModelReviewer
) -> tuple[KnowledgeCheckInput, ...]:
    checks = []
    work = [(kind, context.revision_id) for kind in ("structural", "conflict_coverage")]
    work += [
        (kind, claim.claim_id)
        for claim in context.claims
        for kind in ("assessment", "semantic_support", "freshness")
    ]
    for kind, subject in work:
        evidence = (
            [e.evidence_id for e in context.evidence]
            if subject == context.revision_id
            else _evidence(context, subject)
        )
        snapshots = {
            e.snapshot_id for e in context.evidence if e.evidence_id in evidence
        }
        freshness = None
        if kind == "freshness":
            claim = next(c for c in context.claims if c.claim_id == subject)
            freshness = {
                "evaluated_at": context.created_at,
                "sources": [
                    {
                        "snapshot_id": s.snapshot_id,
                        "basis": "historical_snapshot"
                        if claim.temporal_scope == "historical"
                        else "unknown",
                        "max_age_seconds": 604800,
                        "reason": "Captured document only; publication/effective dates are unknown.",
                    }
                    for s in context.snapshots
                    if s.snapshot_id in snapshots
                ],
            }
        checks.append(
            KnowledgeCheckInput.model_validate_json(
                json.dumps(
                    {
                        "schema_version": "knowledge-check-input-prototype/1",
                        "input_id": str(uuid4()),
                        "check_type": kind,
                        "subject_id": subject,
                        "policy_version": context.policy_version,
                        "reviewer": reviewer.model_dump(mode="json"),
                        "context": context.model_dump(mode="json"),
                        "evidence_ids": evidence,
                        "freshness": freshness,
                    }
                )
            )
        )
    return tuple(checks)


async def render_research(
    knowledge: CheckedKnowledge, artifact_set_id: str
) -> tuple[RenderedReport, ...]:
    """Deterministic presentation of assessed claims; full output still needs audit."""
    context = knowledge.context
    reports = []
    for layer in ("summary", "analysis", "dossier"):
        text = f"# {layer.title()}\n\nModel-reviewed experimental research.\n\n{context.objective}\n\nCoverage: {knowledge.coverage}.\n\n"
        statements = []
        for claim in context.claims:
            start = len(text)
            text += claim.text
            evidence = _evidence(context, claim.claim_id)
            statements.append(
                {
                    "start": start,
                    "end": len(text),
                    "text": claim.text,
                    "claim_ids": [claim.claim_id],
                    "evidence_ids": evidence,
                }
            )
            text += "\n\nScope: " + "; ".join(claim.qualifiers) + ".\n\n"
            if layer != "summary":
                text += "Evidence: " + ", ".join(evidence) + ".\n\n"
        if layer != "summary":
            text += "## Questions and limits\n\n"
            text += (
                "\n\n".join(f"{q.question} — {q.status}" for q in context.questions)
                + "\n\n"
            )
            text += "\n\n".join(c.reason for c in context.conflicts) + "\n\n"
        if layer == "dossier":
            text += "## Captured evidence\n\n"
            for passage in context.evidence:
                source = next(
                    s for s in context.snapshots if s.snapshot_id == passage.snapshot_id
                )
                text += f"{passage.evidence_id}: {source.canonical_url}\n\n{passage.quote}\n\n"
        text += (
            "## Sources\n\n"
            + "\n".join(s.canonical_url for s in context.snapshots)
            + "\n"
        )
        identity = str(uuid4())
        artifact = ManifestArtifact.model_validate_json(
            json.dumps(
                {
                    "artifact_id": identity,
                    "layer": layer,
                    "content_ref": {
                        "scope_id": context.scope_id,
                        "research_id": context.research_id,
                        "artifact_set_id": artifact_set_id,
                        "artifact_id": identity,
                    },
                    "content_digest": text_digest(text),
                    "content_bytes": len(text.encode()),
                    "statements": statements,
                    "question_ids": [q.question_id for q in context.questions],
                    "conflict_ids": [c.conflict_id for c in context.conflicts],
                }
            )
        )
        reports.append(RenderedReport(artifact, text.encode()))
    return tuple(reports)


async def research_from_sources(
    objective: str,
    sources: tuple[CapturedSource, ...],
    *,
    complete: Complete,
    scope_id: str,
    model: str = "local",
) -> JourneyResult:
    """Construct, check and audit a bounded root; no retained publication yet."""
    constructed = await construct_research(
        objective, sources, complete=complete, scope_id=scope_id, model=model
    )
    adapter = ModelReviewAdapter(
        provider="configured-litellm", model=model, complete=complete
    )
    identity = str(uuid4())
    callbacks = {}
    for source in constructed.sources:

        async def acquire(value=source):
            return value

        callbacks[source.reference.snapshot_id] = acquire

    async def verify(checked):
        return await adapter.verify(checked, constructed)

    async def render(knowledge):
        return await render_research(knowledge, identity)

    try:
        return await ConsolidatedJourney(
            context=constructed.context,
            checks=review_plan(constructed.context, adapter.reviewer),
            acquisitions=callbacks,
            verifier=adapter.reviewer,
            verify=verify,
            renderer=Renderer(
                identity="assessed-claim-pyramid",
                version="1",
                configuration_digest=text_digest("assessed-claim-pyramid/1"),
            ),
            render=render,
            auditor=adapter.reviewer,
            audit=adapter.audit,
            artifact_set_id=identity,
            clock=lambda: datetime.now(UTC),
            timeout_seconds=120,
        ).run()
    finally:
        adapter.close()
