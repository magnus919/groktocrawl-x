"""Opt-in SlopSearX provenance boundary selected by ADR-0082.

This module deliberately does not expose SlopSearX workflow state or transfer
research completion, verification, synthesis, or publication authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Protocol

PROFILE = "retrieval-provenance-v1"
HANDOFF_CONTRACT = "slopsearx.retrieval_handoff"
HANDOFF_VERSION = 1
REFERENCE_SCHEMA = "groktocrawl.slopsearx_provenance_reference/1"
REQUIRED_GRANT = "retrieval_receipts"
FORBIDDEN_GRANTS = frozenset(
    {"jobs", "research", "staged_search", "saved_searches", "dependency_dossier"}
)


class ProvenanceUnavailableError(RuntimeError):
    """The opt-in provenance dependency cannot prove a safe stable reference."""


class ToolCaller(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class CaptureObservation:
    status: str
    final_url: str | None = None
    content_sha256: str | None = None
    capture_ref: str | None = None
    captured_at: str | None = None
    failure_code: str | None = None

    def receipt_fields(self) -> dict[str, Any]:
        if self.status not in {"succeeded", "failed"}:
            raise ValueError("capture status must be succeeded or failed")
        fields = {key: value for key, value in asdict(self).items() if value is not None}
        if self.status == "succeeded" and not {
            "final_url",
            "content_sha256",
            "capture_ref",
            "captured_at",
        } <= fields.keys():
            raise ValueError("successful capture observation is incomplete")
        if self.status == "failed" and "failure_code" not in fields:
            raise ValueError("failed capture observation requires a failure code")
        return fields


@dataclass(frozen=True)
class ProvenanceReference:
    """Stable internal reference; deliberately contains no remote job state."""

    schema_version: str
    contract: str
    contract_version: int
    snapshot_id: str
    result_id: str
    receipt_id: str
    manifest_sha256: str
    observations_verified: bool = False
    publishable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def receipt_idempotency_key(
    *, owner_id: str, result_id: str, observation: CaptureObservation
) -> str:
    """Return a stable key across timeout, process restart, and replay."""
    payload = json.dumps(
        {
            "owner_id": owner_id,
            "result_id": result_id,
            "observation": observation.receipt_fields(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"gtcx-prov-{hashlib.sha256(payload).hexdigest()[:40]}"


def _object(value: Any, operation: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProvenanceUnavailableError(f"{operation} returned no object")
    if "error" in value:
        error = value["error"]
        code = error.get("code", "unknown") if isinstance(error, dict) else "unknown"
        raise ProvenanceUnavailableError(f"{operation} failed: {code}")
    return value


class SlopSearXProvenanceAdapter:
    """Least-privilege adapter for handoffs, receipts, and manifest references."""

    def __init__(self, caller: ToolCaller, *, profile: str = PROFILE) -> None:
        if profile != PROFILE:
            raise ValueError(f"unsupported SlopSearX provenance profile: {profile}")
        self._caller = caller

    async def check_profile(self) -> dict[str, Any]:
        capabilities = _object(
            await self._caller.call_tool("slopsearx_list_capabilities", {}),
            "capability check",
        )
        grants = capabilities.get("grants") or {}
        enabled = set(grants.get("enabled") or [])
        if REQUIRED_GRANT not in enabled or enabled & FORBIDDEN_GRANTS:
            raise ProvenanceUnavailableError("least-privilege provenance profile is not active")
        workflow = (capabilities.get("workflow_health") or {}).get("retrieval_receipt") or {}
        if workflow.get("status") != "available":
            raise ProvenanceUnavailableError("retrieval receipt workflow is unavailable")
        return {
            "profile": PROFILE,
            "status": "available",
            "snapshot_ttl_seconds": (capabilities.get("policy_bounds") or {}).get(
                "snapshot_ttl_seconds"
            ),
        }

    async def record(
        self,
        *,
        owner_id: str,
        result_id: str,
        retriever: str,
        observation: CaptureObservation,
    ) -> ProvenanceReference:
        if not owner_id or not result_id or not retriever:
            raise ValueError("owner, result, and retriever identities are required")
        expanded = _object(
            await self._caller.call_tool(
                "slopsearx_read_result", {"result_id": result_id}
            ),
            "read result",
        )
        handoff = expanded.get("retrieval")
        if (
            not isinstance(handoff, dict)
            or handoff.get("contract") != HANDOFF_CONTRACT
            or handoff.get("version") != HANDOFF_VERSION
            or handoff.get("result_id") != result_id
        ):
            raise ProvenanceUnavailableError("retrieval handoff contract mismatch")
        provenance = handoff.get("provenance") or {}
        snapshot_id = provenance.get("snapshot_cursor")
        if not isinstance(snapshot_id, str) or not snapshot_id:
            raise ProvenanceUnavailableError("retrieval snapshot identity is missing")

        receipt = _object(
            await self._caller.call_tool(
                "slopsearx_submit_retrieval_receipt",
                {
                    "result_id": result_id,
                    "retriever": retriever,
                    "idempotency_key": receipt_idempotency_key(
                        owner_id=owner_id,
                        result_id=result_id,
                        observation=observation,
                    ),
                    **observation.receipt_fields(),
                },
            ),
            "submit receipt",
        )
        if receipt.get("state") not in {"created", "replayed"}:
            raise ProvenanceUnavailableError("receipt was not durably accepted")
        receipt_value = receipt.get("receipt") or {}
        receipt_id = receipt_value.get("receipt_id")
        if not isinstance(receipt_id, str) or receipt_value.get("result_id") != result_id:
            raise ProvenanceUnavailableError("receipt identity is missing or mismatched")

        manifest = _object(
            await self._caller.call_tool(
                "slopsearx_export_research_manifest", {"result_ids": [result_id]}
            ),
            "export manifest",
        )
        items = manifest.get("items") or []
        if not any(item.get("result_id") == result_id for item in items):
            raise ProvenanceUnavailableError("research manifest omitted the result")
        if manifest.get("observations_verified") is not False:
            raise ProvenanceUnavailableError("manifest blurred observation and verification")
        manifest_bytes = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        ).encode()
        return ProvenanceReference(
            schema_version=REFERENCE_SCHEMA,
            contract=HANDOFF_CONTRACT,
            contract_version=HANDOFF_VERSION,
            snapshot_id=snapshot_id,
            result_id=result_id,
            receipt_id=receipt_id,
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        )
