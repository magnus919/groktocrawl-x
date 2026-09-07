"""Opt-in experimental research protocol adapters.

The first executable adapter is deliberately fixture-backed and process-local.
It exercises the protocol lifecycle and exact artifact reads without claiming
durable execution, live-provider quality, or production authorization policy.
"""

import asyncio
import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, cast
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from common.features import is_enabled

from ..experimental.client_protocol import ProtocolEvent, ProtocolState, replay_after
from ..experimental.consolidated_example import example_journey
from ..experimental.durable_research import (
    DurableResearchError,
    DurableResearchLedger,
    DurableRun,
)

router = APIRouter()

_ROUTE_PREFIX = "/experimental/research/v1"
_MAX_DURABLE_TERMINAL_PAYLOAD_BYTES = 1_048_576


class CreateResearchRunRequest(BaseModel):
    """Bounded fixture-run admission request."""

    protocol_version: Literal["research/1"] = "research/1"
    objective: str = Field(min_length=1, max_length=10_000)
    as_of: datetime | None = None
    webhook: str | None = None


class AttachResearchSessionRequest(BaseModel):
    """Optimistic attachment of a completed research root to a session."""

    run_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(strict=True, ge=0)


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
    durable_ledger: DurableResearchLedger | None = None
    durable_owner_id: str | None = None
    durable_generation: int | None = None
    durable_manifest: bytes | None = None
    durable_artifacts: dict[str, tuple[bytes, str]] = field(default_factory=dict)


_RUNS: dict[str, _RunRecord] = {}
_IDEMPOTENCY: dict[tuple[str, str], tuple[str, str]] = {}
_SESSION_ATTACHMENTS: dict[tuple[str, str], tuple[int, str]] = {}
_DURABLE_LEDGERS: dict[str, DurableResearchLedger] = {}


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


def _durable_enabled() -> bool:
    return is_enabled("experimental_research_durable")


def _durable_ledger(request: Request) -> DurableResearchLedger:
    url = getattr(request.app.state, "valkey_url", None) or os.environ.get(
        "DURABLE_RESEARCH_REDIS_URL"
    )
    if not url:
        raise HTTPException(
            status_code=503, detail="Durable experimental research storage unavailable"
        )
    ledger = _DURABLE_LEDGERS.get(url)
    if ledger is None:
        ledger = DurableResearchLedger(url)
        _DURABLE_LEDGERS[url] = ledger
    return ledger


def _build_event(
    record: _RunRecord,
    event: Literal["accepted", "progress", "done", "error", "cancelled"],
    state: ProtocolState,
    **kwargs: Any,
) -> ProtocolEvent:
    return ProtocolEvent(
        protocol_version="research/1",
        run_id=record.run_id,
        sequence=len(record.events) + 1,
        event=event,
        state=state,
        **kwargs,
    )


def _event(
    record: _RunRecord,
    event: Literal["accepted", "progress", "done", "error", "cancelled"],
    state: ProtocolState,
    **kwargs: Any,
) -> ProtocolEvent:
    event_record = _build_event(record, event, state, **kwargs)
    record.events.append(event_record)
    return event_record


def _decode_b64(value: Any, label: str) -> bytes:
    if not isinstance(value, str):
        raise DurableResearchError(f"durable {label} payload is invalid")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise DurableResearchError(f"durable {label} payload is invalid") from exc


def _durable_artifact_payload(record: _RunRecord) -> dict[str, Any]:
    if record.journey is None:
        raise DurableResearchError("completed run has no fixture material")
    manifest = record.journey.manifest_bytes
    artifacts: dict[str, dict[str, str]] = {}
    for report in record.journey.reports:
        artifacts[report.artifact.artifact_id] = {
            "body_b64": base64.b64encode(report.body).decode("ascii"),
            "content_digest": report.artifact.content_digest,
        }
    payload = {
        "manifest": {
            "body_b64": base64.b64encode(manifest).decode("ascii"),
            "content_digest": hashlib.sha256(manifest).hexdigest(),
        },
        "artifacts": artifacts,
    }
    encoded_size = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    if encoded_size > _MAX_DURABLE_TERMINAL_PAYLOAD_BYTES:
        raise DurableResearchError("durable fixture payload exceeds its size bound")
    return payload


def _decode_durable_artifacts(
    terminal: dict[str, Any],
) -> tuple[bytes | None, dict[str, tuple[bytes, str]]]:
    material = terminal.get("artifacts")
    manifest_payload = terminal.get("manifest")
    if material is None and manifest_payload is None:
        return None, {}
    if not isinstance(manifest_payload, dict) or not isinstance(material, dict):
        raise DurableResearchError("durable artifact payload is invalid")
    manifest = _decode_b64(manifest_payload.get("body_b64"), "manifest")
    if hashlib.sha256(manifest).hexdigest() != manifest_payload.get("content_digest"):
        raise DurableResearchError("durable manifest digest mismatch")
    artifacts: dict[str, tuple[bytes, str]] = {}
    for artifact_id, item in material.items():
        if not isinstance(artifact_id, str) or not isinstance(item, dict):
            raise DurableResearchError("durable artifact payload is invalid")
        body = _decode_b64(item.get("body_b64"), "artifact")
        digest = item.get("content_digest")
        if not isinstance(digest, str) or hashlib.sha256(body).hexdigest() != digest:
            raise DurableResearchError("durable artifact digest mismatch")
        artifacts[artifact_id] = (body, digest)
    return manifest, artifacts


def _restore_events(durable: DurableRun) -> list[ProtocolEvent]:
    terminal = durable.terminal_payload or {}
    raw_events = terminal.get("events") or durable.payload.get("events") or []
    if not isinstance(raw_events, list):
        raise DurableResearchError("durable event history is invalid")
    try:
        return [ProtocolEvent.model_validate(item) for item in raw_events]
    except (TypeError, ValueError) as exc:
        raise DurableResearchError("durable event history is invalid") from exc


def _durable_terminal_payload(
    record: _RunRecord, terminal_event: ProtocolEvent
) -> dict[str, Any]:
    return {
        "research_id": record.research_id,
        "result": record.result,
        "events": [
            event.model_dump(mode="json") for event in (*record.events, terminal_event)
        ],
        **_durable_artifact_payload(record),
    }


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
        "result": record.result
        if record.state == "completed" and record.result is not None
        else None,
        "error": record.error if terminal and terminal.event == "error" else None,
        "status_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}",
        "events_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}/events",
    }


def _find_run(run_id: str, request: Request) -> _RunRecord:
    record = _RUNS.get(run_id)
    if record is None and _durable_enabled():
        durable = _durable_ledger(request).get(run_id)
        if durable is not None:
            try:
                record = _restore_durable_record(durable)
            except DurableResearchError as exc:
                raise HTTPException(
                    status_code=503, detail="Durable research projection unavailable"
                ) from exc
            record.durable_ledger = _durable_ledger(request)
            if record.scope_id != _scope_id(request):
                raise HTTPException(status_code=404, detail="Research run not found")
            _RUNS[run_id] = record
            if durable.state in {"admitted", "running"}:
                record.task = asyncio.create_task(_execute_run(record))
    if record is None or record.scope_id != _scope_id(request):
        raise HTTPException(status_code=404, detail="Research run not found")
    if record.deleted:
        raise HTTPException(status_code=410, detail="Research run deleted")
    return record


def _restore_durable_record(durable: DurableRun) -> _RunRecord:
    payload = durable.payload
    terminal = durable.terminal_payload or {}
    state = durable.state
    if state not in {
        "accepted",
        "running",
        "cancel_requested",
        "completed",
        "failed",
        "cancelled",
    }:
        state = "accepted"
    typed_state = cast(
        Literal[
            "accepted",
            "running",
            "cancel_requested",
            "completed",
            "failed",
            "cancelled",
        ],
        state,
    )
    manifest, artifacts = _decode_durable_artifacts(terminal)
    return _RunRecord(
        run_id=durable.run_id,
        research_id=str(payload.get("research_id", durable.run_id)),
        scope_id=durable.scope_id,
        objective=str(payload.get("objective", "Recovered experimental research run")),
        request_digest=durable.request_digest,
        state=typed_state,
        result=terminal.get("result") if typed_state == "completed" else None,
        events=_restore_events(durable),
        durable_manifest=manifest,
        durable_artifacts=artifacts,
        durable_ledger=None,
    )


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
        if record.state not in {"accepted", "running"}:
            return
        if record.durable_ledger is not None:
            try:
                claimed = record.durable_ledger.claim(
                    record.run_id,
                    owner_id=f"worker:{uuid4()}",
                    attempt_id=f"attempt:{uuid4()}",
                )
            except Exception:
                return
            record.durable_owner_id = claimed.owner_id
            record.durable_generation = claimed.owner_generation
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
        terminal_event: ProtocolEvent | None = None
        if (
            record.durable_ledger is not None
            and record.durable_owner_id is not None
            and record.durable_generation is not None
        ):
            terminal_event = _build_event(record, "done", "completed", result=record.result)
            terminal_payload = _durable_terminal_payload(record, terminal_event)
            checkpoint_digest = hashlib.sha256(
                json.dumps(terminal_payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            result_digest = hashlib.sha256(
                json.dumps(record.result, sort_keys=True).encode("utf-8")
            ).hexdigest()
            record.durable_ledger.checkpoint(
                record.run_id,
                record.durable_owner_id,
                record.durable_generation,
                "terminal_projection",
                checkpoint_digest,
            )
            record.durable_ledger.commit_result(
                record.run_id,
                record.durable_owner_id,
                record.durable_generation,
                result_digest,
                terminal_payload=terminal_payload,
            )
        record.state = "completed"
        if terminal_event is not None:
            record.events.append(terminal_event)
        else:
            _event(record, "done", "completed", result=record.result)


def capability_document() -> dict[str, Any]:
    """Return the honest capability boundary for the current W6 slice."""
    runs_available = is_enabled("experimental_research_runs")
    durable = runs_available and _durable_enabled()
    return {
        "protocol_version": "research/1",
        "route_prefix": _ROUTE_PREFIX,
        "implementation_stage": "durable_fixture_run_adapter"
        if durable
        else "fixture_run_adapter"
        if runs_available
        else "contract_and_golden_traces",
        "recovery_mode": "valkey_fenced"
        if durable
        else "process_local"
        if runs_available
        else "not_advertised",
        "replay": {
            "mode": "contract_only",
            "window_events": 0,
        },
        "operations": {
            "capabilities": {"available": True},
            "runs": {"available": runs_available, "reason": None if runs_available else "public_adapters_pending"},
            "artifacts": {"available": runs_available, "reason": None if runs_available else "public_adapters_pending"},
            "evidence": {"available": runs_available, "reason": None if runs_available else "public_adapters_pending"},
            "sessions": {
                "available": runs_available,
                "reason": None if runs_available else "public_adapters_pending",
                "mode": "attachment_only" if runs_available else None,
            },
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
    durable = _durable_ledger(request) if _durable_enabled() else None
    digest = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    existing = _IDEMPOTENCY.get((scope, key)) if durable is None else None
    if durable is not None:
        selected_run_id = str(uuid4())
        accepted_event = ProtocolEvent(
            protocol_version="research/1",
            run_id=selected_run_id,
            sequence=1,
            event="accepted",
            state="accepted",
        )
        admitted = durable.admit(
            scope,
            key,
            digest,
            run_id=selected_run_id,
            payload={
                "objective": payload.objective,
                "research_id": str(uuid4()),
                "events": [accepted_event.model_dump(mode="json")],
            },
        )
        research_id = str(admitted.payload.get("research_id", str(uuid4())))
        record = _RUNS.get(admitted.run_id)
        if record is None:
            record = _restore_durable_record(admitted)
            record.research_id = research_id
            record.durable_ledger = durable
            _RUNS[admitted.run_id] = record
        if record.task is None:
            record.task = asyncio.create_task(_execute_run(record))
        return {
            "protocol_version": "research/1",
            "run_id": record.run_id,
            "research_id": record.research_id,
            "state": record.state,
            "status_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}",
            "events_url": f"{_ROUTE_PREFIX}/runs/{record.run_id}/events",
        }
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
        if record.durable_ledger is not None:
            terminal_event = _build_event(record, "cancelled", "cancelled")
            terminal_payload = {
                "research_id": record.research_id,
                "events": [
                    event.model_dump(mode="json")
                    for event in (*record.events, terminal_event)
                ],
            }
            durable = record.durable_ledger.cancel(
                record.run_id, terminal_payload=terminal_payload
            )
            if durable.state == "completed":
                recovered = _restore_durable_record(durable)
                record.state = recovered.state
                record.result = recovered.result
                record.events = recovered.events
                record.durable_manifest = recovered.durable_manifest
                record.durable_artifacts = recovered.durable_artifacts
                return _record_projection(record)
            record.state = "cancelled"
            record.events.append(terminal_event)
            if record.task is not None and not record.task.done():
                record.task.cancel()
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


def _durable_read_records(request: Request) -> list[_RunRecord]:
    """Hydrate retained durable records for opaque artifact URLs."""
    if not _durable_enabled():
        return []
    ledger = _durable_ledger(request)
    scope = _scope_id(request)
    records: list[_RunRecord] = []
    for durable in ledger.retained():
        if durable.scope_id != scope:
            continue
        try:
            record = _restore_durable_record(durable)
        except DurableResearchError as exc:
            raise HTTPException(
                status_code=503, detail="Durable research projection unavailable"
            ) from exc
        record.durable_ledger = ledger
        _RUNS.setdefault(record.run_id, record)
        records.append(_RUNS[record.run_id])
    return records


@router.get(f"{_ROUTE_PREFIX}/artifact-sets/{{artifact_set_id}}")
async def get_experimental_artifact_set(artifact_set_id: str, request: Request) -> dict[str, Any]:
    """Return the exact audited manifest for a completed fixture run."""
    _require_runs()
    scope = _scope_id(request)
    records = list(_RUNS.values())
    records.extend(_durable_read_records(request))
    for record in records:
        if record.scope_id != scope or (
            record.journey is None and record.durable_manifest is None
        ):
            continue
        if record.journey is not None:
            manifest_bytes = record.journey.manifest_bytes
        else:
            if record.result is None or record.result.get("artifact_set_id") != artifact_set_id:
                continue
            manifest_bytes = record.durable_manifest
            if manifest_bytes is None:
                continue
        manifest_payload = json.loads(manifest_bytes)
        if manifest_payload.get("artifact_set_id") != artifact_set_id:
            continue
        if record.deleted:
            raise HTTPException(status_code=410, detail="Artifact set deleted")
        return manifest_payload
    raise HTTPException(status_code=404, detail="Artifact set not found")


@router.get(f"{_ROUTE_PREFIX}/artifacts/{{artifact_id}}")
async def get_experimental_artifact(artifact_id: str, request: Request) -> Response:
    """Return exact retained fixture bytes after scope and digest checks."""
    _require_runs()
    scope = _scope_id(request)
    records = list(_RUNS.values())
    records.extend(_durable_read_records(request))
    for record in records:
        if record.scope_id != scope:
            continue
        if record.deleted:
            raise HTTPException(status_code=410, detail="Artifact deleted")
        if record.journey is not None:
            reports = {
                report.artifact.artifact_id: (report.body, report.artifact.content_digest)
                for report in record.journey.reports
            }
        else:
            reports = record.durable_artifacts
        artifact = reports.get(artifact_id)
        if artifact is not None:
            body, content_digest = artifact
            if hashlib.sha256(body).hexdigest() != content_digest:
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


@router.post(f"{_ROUTE_PREFIX}/sessions/{{session_id}}/attachments", status_code=200)
async def attach_experimental_research_session(
    session_id: str, payload: AttachResearchSessionRequest, request: Request
) -> dict[str, Any]:
    """Attach a completed root with an expected-revision concurrency guard."""
    _require_runs()
    if len(session_id) > 200:
        raise HTTPException(status_code=400, detail="Session ID is too long")
    record = _find_run(payload.run_id, request)
    if record.state != "completed" or record.result is None:
        raise HTTPException(status_code=409, detail="Research run is not completed")
    key = (_scope_id(request), session_id)
    current = _SESSION_ATTACHMENTS.get(key)
    current_revision = current[0] if current is not None else 0
    if payload.expected_revision != current_revision:
        raise HTTPException(status_code=409, detail="Session revision conflict")
    if current is not None and current[1] == payload.run_id:
        return {
            "session_id": session_id,
            "revision": current_revision,
            "run_id": payload.run_id,
            "research_id": record.research_id,
            "artifact_set_id": record.result["artifact_set_id"],
        }
    revision = current_revision + 1
    _SESSION_ATTACHMENTS[key] = (revision, payload.run_id)
    return {
        "session_id": session_id,
        "revision": revision,
        "run_id": payload.run_id,
        "research_id": record.research_id,
        "artifact_set_id": record.result["artifact_set_id"],
    }
