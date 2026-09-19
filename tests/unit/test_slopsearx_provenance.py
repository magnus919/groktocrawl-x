from __future__ import annotations

from typing import Any

import pytest
from agent.experimental.slopsearx_provenance import (
    CaptureObservation,
    ProvenanceUnavailableError,
    SlopSearXProvenanceAdapter,
    receipt_idempotency_key,
)

RESULT_ID = "snap-abc123:0"


class Caller:
    def __init__(self, *, fail_read: bool = False, broad_grant: bool = False) -> None:
        self.fail_read = fail_read
        self.broad_grant = broad_grant
        self.arguments: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.arguments.append((name, arguments))
        if name == "slopsearx_list_capabilities":
            enabled = ["retrieval_receipts"]
            if self.broad_grant:
                enabled.append("research")
            return {
                "grants": {"enabled": enabled},
                "workflow_health": {"retrieval_receipt": {"status": "available"}},
                "policy_bounds": {"snapshot_ttl_seconds": 3600},
            }
        if name == "slopsearx_read_result":
            if self.fail_read:
                return {"error": {"code": "snapshot_expired"}}
            return {
                "retrieval": {
                    "contract": "slopsearx.retrieval_handoff",
                    "version": 1,
                    "result_id": RESULT_ID,
                    "provenance": {"snapshot_cursor": "snap-abc123"},
                }
            }
        if name == "slopsearx_submit_retrieval_receipt":
            return {
                "state": "replayed",
                "receipt": {"receipt_id": "receipt-1", "result_id": RESULT_ID},
            }
        if name == "slopsearx_export_research_manifest":
            return {
                "contract": "slopsearx.research_manifest",
                "version": 1,
                "items": [{"result_id": RESULT_ID}],
                "observations_verified": False,
            }
        raise AssertionError(name)


def observation() -> CaptureObservation:
    return CaptureObservation(
        status="succeeded",
        final_url="https://example.test/evidence",
        content_sha256="a" * 64,
        capture_ref=f"urn:sha256:{'a' * 64}",
        captured_at="2026-09-19T00:00:00Z",
    )


@pytest.mark.asyncio
async def test_accepts_only_least_privilege_profile() -> None:
    assert (await SlopSearXProvenanceAdapter(Caller()).check_profile())["status"] == (
        "available"
    )
    with pytest.raises(ProvenanceUnavailableError, match="least-privilege"):
        await SlopSearXProvenanceAdapter(Caller(broad_grant=True)).check_profile()


@pytest.mark.asyncio
async def test_retains_only_stable_non_authoritative_reference() -> None:
    caller = Caller()
    reference = await SlopSearXProvenanceAdapter(caller).record(
        owner_id="run-1",
        result_id=RESULT_ID,
        retriever="groktocrawl-x",
        observation=observation(),
    )
    assert reference.snapshot_id == "snap-abc123"
    assert reference.receipt_id == "receipt-1"
    assert reference.observations_verified is False
    assert reference.publishable is False
    assert set(reference.as_dict()) == {
        "schema_version",
        "contract",
        "contract_version",
        "snapshot_id",
        "result_id",
        "receipt_id",
        "manifest_sha256",
        "observations_verified",
        "publishable",
    }


def test_receipt_key_is_stable_across_adapter_restarts() -> None:
    first = receipt_idempotency_key(
        owner_id="run-1", result_id=RESULT_ID, observation=observation()
    )
    second = receipt_idempotency_key(
        owner_id="run-1", result_id=RESULT_ID, observation=observation()
    )
    assert first == second
    assert len(first) <= 64


@pytest.mark.asyncio
async def test_expired_snapshot_fails_without_minting_reference() -> None:
    caller = Caller(fail_read=True)
    with pytest.raises(ProvenanceUnavailableError, match="snapshot_expired"):
        await SlopSearXProvenanceAdapter(caller).record(
            owner_id="run-1",
            result_id=RESULT_ID,
            retriever="groktocrawl-x",
            observation=observation(),
        )
    assert [name for name, _ in caller.arguments] == ["slopsearx_read_result"]


def test_observation_must_be_complete() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        CaptureObservation(status="succeeded").receipt_fields()
