"""Valkey-backed W5 ownership, fencing, and recovery matrix."""

from __future__ import annotations

import os
import time
from uuid import uuid4

import pytest
from agent.experimental.durable_research import (
    DurableConflictError,
    DurableResearchLedger,
    LeaseLostError,
)
from redis import Redis


@pytest.fixture
def ledger() -> DurableResearchLedger:
    url = os.environ.get("DURABLE_RESEARCH_REDIS_URL")
    if url is None:
        raise RuntimeError("DURABLE_RESEARCH_REDIS_URL is required")
    redis = Redis.from_url(url, decode_responses=True)
    redis.flushdb()
    return DurableResearchLedger(
        url,
        namespace=f"groktocrawl:test:{uuid4()}",
        lease_ms=100,
        retention_ms=10_000,
        retry_window_ms=5_000,
    )


def test_admission_is_idempotent_and_conflicts_are_explicit(
    ledger: DurableResearchLedger,
) -> None:
    first = ledger.admit(
        "scope-a", "request-1", "digest-a", payload={"objective": "fixture"}
    )
    duplicate = ledger.admit("scope-a", "request-1", "digest-a")
    assert duplicate == first
    with pytest.raises(DurableConflictError, match="idempotency"):
        ledger.admit("scope-a", "request-1", "digest-b")


def test_expired_lease_reclaims_and_fences_old_owner(
    ledger: DurableResearchLedger,
) -> None:
    admitted = ledger.admit("scope-a", "request-2", "digest-a")
    first = ledger.claim(admitted.run_id, "owner-a", attempt_id="attempt-a")
    assert first.owner_generation == 1
    with pytest.raises(DurableConflictError, match="live lease"):
        ledger.claim(admitted.run_id, "owner-b", attempt_id="attempt-b")

    time.sleep(0.15)
    second = ledger.claim(admitted.run_id, "owner-b", attempt_id="attempt-b")
    assert second.owner_generation == 2
    with pytest.raises(LeaseLostError):
        ledger.commit_result(admitted.run_id, "owner-a", 1, "result-a")
    checkpointed = ledger.checkpoint(
        admitted.run_id, "owner-b", 2, "knowledge_ir", "checkpoint-b"
    )
    assert checkpointed.checkpoint_name == "knowledge_ir"
    committed = ledger.commit_result(
        admitted.run_id,
        "owner-b",
        2,
        "result-b",
        terminal_payload={"state": "completed", "artifact_set_id": "artifact-b"},
    )
    assert committed.state == "completed"
    assert committed.result_digest == "result-b"
    restarted = DurableResearchLedger(
        os.environ["DURABLE_RESEARCH_REDIS_URL"],
        namespace=ledger.namespace,
        lease_ms=100,
        retention_ms=10_000,
        retry_window_ms=5_000,
    )
    recovered = restarted.get(admitted.run_id)
    assert recovered is not None
    assert recovered.checkpoint_digest == "checkpoint-b"
    assert recovered.terminal_payload == {
        "state": "completed",
        "artifact_set_id": "artifact-b",
    }


def test_cancellation_survives_late_worker_completion(
    ledger: DurableResearchLedger,
) -> None:
    admitted = ledger.admit("scope-a", "request-3", "digest-a")
    claimed = ledger.claim(admitted.run_id, "owner-a")
    cancelled = ledger.cancel(admitted.run_id)
    assert cancelled.state == "cancelled"
    with pytest.raises(DurableConflictError, match="cancellation"):
        ledger.commit_result(
            admitted.run_id,
            "owner-a",
            claimed.owner_generation,
            "late-result",
        )


def test_new_ledger_instance_can_recover_after_process_loss(
    ledger: DurableResearchLedger,
) -> None:
    admitted = ledger.admit("scope-a", "request-4", "digest-a")
    first = ledger.claim(admitted.run_id, "crashed-owner")
    time.sleep(0.15)

    restarted = DurableResearchLedger(
        os.environ["DURABLE_RESEARCH_REDIS_URL"],
        namespace=ledger.namespace,
        lease_ms=100,
        retention_ms=10_000,
        retry_window_ms=5_000,
    )
    reclaimable = restarted.reclaimable()
    assert [item.run_id for item in reclaimable] == [admitted.run_id]
    recovered = restarted.claim(admitted.run_id, "restarted-owner")
    assert recovered.owner_generation == first.owner_generation + 1
