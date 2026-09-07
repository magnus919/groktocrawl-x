"""Opt-in experimental research protocol adapters.

The first executable adapter is deliberately fixture-backed and process-local.
It exercises the protocol lifecycle and exact artifact reads without claiming
durable execution, live-provider quality, or production authorization policy.
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from common.features import is_enabled

from ..experimental.client_protocol import ProtocolEvent, ProtocolState, replay_after
from ..experimental.consolidated_example import example_journey

router = APIRouter()

_ROUTE_PREFIX = "/experimental/research/v1"


class CreateResearchRunRequest(BaseModel):
    """Bounded fixture-run admission request."""

    protocol_version: Literal["research/1"] = "research/1"
    objective: str = Field(min_length=1, max_length=10_000)
    as_of: datetime | None = None
    webhook: str | None = None


@dataclass
class _RunRecord:
    run_id: str
    research_id: str
    scope_id: str
    objective: str
    request_digest: str
    events: list[ProtocolEvent] = field(default_factory=list)
    state: Literal[
        "accepted", "running", "cancel_requested", "completed", "failed", "cancelled"
    ] = "accepted"
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    journey: Any = None
    task: asyncio.Task[None] | None = None
    deleted: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_RUNS: dict[str, _RunRecord] = {}
_IDEMPOTENCY: dict[tuple[str, str], tuple[str, str]] = {}


def _scope_id(request: Request) -> str:
    """Derive a stable process-local scope without trusting request payload."""
    credential = request.headers.get("Authorization") or request.headers.get(
        "X-API-Key"
    )
    if not credential:
        return "anonymous"
    return "key:" + hashlib.sha256(credential.encode()).hexdigest()[:32]


def _require_feature(feature: str = "experimental_research") -> None:
    if not is_enabled(feature):
        raise HTTPException(status_code=404, detail="Experimental research disabled")


def _require_runs() -> None:
    _require_feature()
    if not is_enabled("experimental_research_runs"):
        raise HTTPException(status_code=404, detail="Experimental research runs disabled")


def _event(
    record: _RunRecord,
    event: Literal["accepted", "progress", "done", "error", "cancelled"],
    state: ProtocolState,
    **kwargs: Any,
) -> None:
    record.events.append(
        ProtocolEvent(
            protocol_version="research/1",
            run_id=record.run_id,
            sequence=len(record.events) + 1,
            event=event,
            state=state,
            **kwargs,
        )
    )


def _record_projection(record: _RunRecord) -> dict[str, Any]:
    terminal = record.events[-1] if record.events and record.events[-1].terminal else None
    return {
        "protocol_version": "research/1",
        "run_id": record.run_id,
        "research_id": record.research_id,
        "state": record.state,
        "execution_outcome": (
            "completed"
            if record.state == "completed"
            else record.state
            if record.state in {"failed", "cancelled"}
            else None
        ),
        "result": record.result if terminal and terminal.event == "done" else None,
        "error": record.error if terminal and terminal.event == "error" else None,
        "status_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}",
        "events_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}/events",
    }


def _find_run(run_id: str, request: Request) -> _RunRecord:
    record = _RUNS.get(run_id)
    if record is None or record.scope_id != _scope_id(request):
        raise HTTPException(status_code=404, detail="Research run not found")
    if record.deleted:
        raise HTTPException(status_code=410, detail="Research run deleted")
    return record


def _artifact_result(record: _RunRecord) -> dict[str, Any]:
    journey = record.journey
    manifest = journey.candidate.admitted.manifest
    summary = next(report for report in journey.reports if report.artifact.layer == "summary")
    return {
        "research_id": record.research_id,
        "ir_revision_id": manifest.revision_id,
        "artifact_set_id": manifest.artifact_set_id,
        "summary": summary.body.decode("utf-8"),
        "coverage": manifest.coverage,
        "manifest_url": f"{_ROUTE_PREFIX}/artifact-sets/{manifest.artifact_set_id}",
        "artifacts": {
            report.artifact.layer: f"{_ROUTE_PREFIX}/artifacts/{report.artifact.artifact_id}"
            for report in journey.reports
        },
    }


async def _execute_run(record: _RunRecord) -> None:
    async with record.lock:
        if record.state != "accepted":
            return
        record.state = "running"
        _event(record, "progress", "running", stage="acquisition")
    try:
        journey = example_journey(
            scope_id=record.scope_id,
            research_id=record.research_id,
            objective=record.objective,
            artifact_set_id=str(uuid4()),
        )
        result = await journey.run()
    except asyncio.CancelledError:
        async with record.lock:
            if record.state not in {"completed", "failed", "cancelled"}:
                record.state = "cancelled"
                _event(record, "cancelled", "cancelled")
        raise
    except Exception:  # pragma: no cover - defensive terminal contract
        async with record.lock:
            if record.state == "cancel_requested":
                record.state = "cancelled"
                _event(record, "cancelled", "cancelled")
            elif record.state not in {"completed", "cancelled"}:
                record.state = "failed"
                record.error = {"code": "fixture_run_failed", "retryable": False}
                _event(record, "error", "failed", error=record.error)
        return
    async with record.lock:
        if record.state == "cancel_requested":
            record.state = "cancelled"
            _event(record, "cancelled", "cancelled")
            return
        record.journey = result
        record.result = _artifact_result(record)
        record.state = "completed"
        _event(record, "done", "completed", result=record.result)


def capability_document() -> dict[str, Any]:
    """Return the honest capability boundary for the current W6 slice."""
    runs_available = is_enabled("experimental_research_runs")
    return {
        "protocol_version": "research/1",
        "route_prefix": _ROUTE_PREFIX,
        "implementation_stage": "fixture_run_adapter" if runs_available else "contract_and_golden_traces",
        "recovery_mode": "process_local" if runs_available else "not_advertised",
        "replay": {
            "mode": "contract_only",
            "window_events": 0,
        },
        "operations": {
            "capabilities": {"available": True},
            "runs": {"available": runs_available, "reason": None if runs_available else "public_adapters_pending"},
            "artifacts": {"available": runs_available, "reason": None if runs_available else "public_adapters_pending"},
            "evidence": {"available": runs_available, "reason": None if runs_available else "public_adapters_pending"},
            "sessions": {"available": False, "reason": "public_adapters_pending"},
        },
    }


@router.get(f"{_ROUTE_PREFIX}/capabilities")
async def get_experimental_research_capabilities() -> dict[str, Any]:
    """Advertise the opt-in protocol without implying unavailable operations."""
    if not is_enabled("experimental_research"):
        raise HTTPException(status_code=404, detail="Experimental research disabled")
    return capability_document()


@router.post(f"{_ROUTE_PREFIX}/runs", status_code=202)
async def create_experimental_research_run(
    payload: CreateResearchRunRequest, request: Request
) -> dict[str, Any]:
    """Admit one bounded fixture run with scoped idempotency."""
    _require_runs()
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key or len(key) > 200:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required")
    scope = _scope_id(request)
    digest = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    existing = _IDEMPOTENCY.get((scope, key))
    if existing is not None:
        run_id, prior_digest = existing
        if prior_digest != digest:
            raise HTTPException(status_code=409, detail="Idempotency key conflict")
        record = _RUNS[run_id]
        return {
            "protocol_version": "research/1",
            "run_id": record.run_id,
            "research_id": record.research_id,
            "state": record.state,
            "status_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}",
            "events_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}/events",
        }
    run_id = str(uuid4())
    record = _RunRecord(
        run_id=run_id,
        research_id=str(uuid4()),
        scope_id=scope,
        objective=payload.objective,
        request_digest=digest,
    )
    _event(record, "accepted", "accepted")
    _RUNS[run_id] = record
    _IDEMPOTENCY[(scope, key)] = (run_id, digest)
    record.task = asyncio.create_task(_execute_run(record))
    return {
        "protocol_version": "research/1",
        "run_id": record.run_id,
        "research_id": record.research_id,
        "state": record.state,
        "status_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}",
        "events_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}/events",
    }


@router.get(f"{_ROUTE_PREFIX}/runs/{{run_id}}")
async def get_experimental_research_run(run_id: str, request: Request) -> dict[str, Any]:
    """Return the authoritative process-local run projection."""
    _require_runs()
    return _record_projection(_find_run(run_id, request))


@router.get(f"{_ROUTE_PREFIX}/runs/{{run_id}}/events")
async def stream_experimental_research_events(run_id: str, request: Request) -> StreamingResponse:
    """Replay retained process-local events as SSE; no restart recovery is claimed."""
    _require_runs()
    record = _find_run(run_id, request)
    try:
        events = replay_after(record.events, request.headers.get("Last-Event-ID"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def body():
        for event in events:
            yield f"id: {event.event_id}\nevent: {event.event}\ndata: {event.model_dump_json()}\n\n"

    return StreamingResponse(body(), media_type="text/event-stream")


@router.post(f"{_ROUTE_PREFIX}/runs/{{run_id}}/cancel", status_code=202)
async def cancel_experimental_research_run(run_id: str, request: Request) -> dict[str, Any]:
    """Request cancellation and return the current authoritative projection."""
    _require_runs()
    record = _find_run(run_id, request)
    async with record.lock:
        if record.state in {"completed", "failed", "cancelled"}:
            return _record_projection(record)
        if record.state == "accepted":
            record.state = "cancelled"
            _event(record, "cancelled", "cancelled")
            if record.task is not None and not record.task.done():
                record.task.cancel()
            return _record_projection(record)
        record.state = "cancel_requested"
        _event(record, "progress", "cancel_requested", stage="cancellation")
        if record.task is not None and not record.task.done():
            record.task.cancel()
    return _record_projection(record)


@router.get(f"{_ROUTE_PREFIX}/artifact-sets/{{artifact_set_id}}")
async def get_experimental_artifact_set(artifact_set_id: str, request: Request) -> dict[str, Any]:
    """Return the exact audited manifest for a completed fixture run."""
    _require_runs()
    scope = _scope_id(request)
    for record in _RUNS.values():
        if record.scope_id != scope or record.journey is None:
            continue
        manifest = record.journey.candidate.admitted.manifest
        if manifest.artifact_set_id != artifact_set_id:
            continue
        if record.deleted:
            raise HTTPException(status_code=410, detail="Artifact set deleted")
        return json.loads(manifest.model_dump_json())
    raise HTTPException(status_code=404, detail="Artifact set not found")


@router.get(f"{_ROUTE_PREFIX}/artifacts/{{artifact_id}}")
async def get_experimental_artifact(artifact_id: str, request: Request) -> Response:
    """Return exact retained fixture bytes after scope and digest checks."""
    _require_runs()
    scope = _scope_id(request)
    for record in _RUNS.values():
        if record.scope_id != scope or record.journey is None:
            continue
        if not any(
            report.artifact.artifact_id == artifact_id for report in record.journey.reports
        ):
            continue
        if record.deleted:
            raise HTTPException(status_code=410, detail="Artifact deleted")
        for report in record.journey.reports:
            if report.artifact.artifact_id == artifact_id:
                body = report.body
                if hashlib.sha256(body).hexdigest() != report.artifact.content_digest:
                    raise HTTPException(status_code=503, detail="Artifact integrity unavailable")
                return Response(body, media_type="text/markdown")
    raise HTTPException(status_code=404, detail="Artifact not found")


@router.get(f"{_ROUTE_PREFIX}/research/{{research_id}}/evidence/{{snapshot_id}}")
async def get_experimental_evidence(research_id: str, snapshot_id: str, request: Request) -> dict[str, Any]:
    """Return bounded exact fixture evidence for one scoped snapshot."""
    _require_runs()
    scope = _scope_id(request)
    for record in _RUNS.values():
        if record.scope_id != scope or record.research_id != research_id or record.journey is None:
            continue
        if record.deleted:
            raise HTTPException(status_code=410, detail="Research evidence deleted")
        for source in record.journey.sources:
            if source.reference.snapshot_id == snapshot_id:
                return {
                    "research_id": research_id,
                    "snapshot_id": snapshot_id,
                    "media_type": source.media_type,
                    "body": source.body.decode("utf-8"),
                    "content_digest": hashlib.sha256(source.body).hexdigest(),
                }
    raise HTTPException(status_code=404, detail="Evidence not found")


@router.delete(f"{_ROUTE_PREFIX}/research/{{research_id}}", status_code=202)
async def delete_experimental_research(research_id: str, request: Request) -> dict[str, Any]:
    """Tombstone the process-local research root before physical cleanup."""
    _require_runs()
    scope = _scope_id(request)
    for record in _RUNS.values():
        if record.scope_id == scope and record.research_id == research_id:
            record.deleted = True
            return {"research_id": research_id, "state": "deleted"}
    raise HTTPException(status_code=404, detail="Research root not found")
