"""Valkey-backed ownership ledger for the bounded W5 recovery adapter.

This module persists admission, ownership, fencing, cancellation, and terminal
receipt state. It deliberately stores receipt identities rather than provider
payloads: artifact publication remains owned by the research stores, and an
ambiguous external effect is never treated as a successful result.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from redis import Redis


class DurableResearchError(RuntimeError):
    """Base error for a rejected durable transition."""


class DurableConflictError(DurableResearchError):
    """The requested transition conflicts with retained state."""


class LeaseLostError(DurableConflictError):
    """The caller no longer owns the fencing generation."""


@dataclass(frozen=True)
class DurableRun:
    """The persisted projection needed to recover one admitted run."""

    run_id: str
    scope_id: str
    request_digest: str
    state: str
    owner_id: str | None
    owner_generation: int
    attempt_id: str | None
    result_digest: str | None
    retry_deadline_ms: int
    created_at_ms: int
    payload: dict[str, Any]

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> DurableRun:
        return cls(
            run_id=str(record["run_id"]),
            scope_id=str(record["scope_id"]),
            request_digest=str(record["request_digest"]),
            state=str(record["state"]),
            owner_id=record.get("owner_id"),
            owner_generation=int(record["owner_generation"]),
            attempt_id=record.get("attempt_id"),
            result_digest=record.get("result_digest"),
            retry_deadline_ms=int(record["retry_deadline_ms"]),
            created_at_ms=int(record["created_at_ms"]),
            payload=dict(record.get("payload") or {}),
        )


_ADMIT_SCRIPT = """
local existing = redis.call('GET', KEYS[1])
if existing then
  local prior = cjson.decode(existing)
  if prior.request_digest ~= ARGV[2] then return {2, prior.run_id} end
  return {1, prior.run_id}
end
redis.call('SET', KEYS[1], cjson.encode({run_id=ARGV[1], request_digest=ARGV[2]}), 'PX', ARGV[4])
redis.call('SET', KEYS[2], ARGV[3], 'PX', ARGV[4])
redis.call('SADD', KEYS[3], ARGV[1])
return {0, ARGV[1]}
"""

_CLAIM_SCRIPT = """
local raw = redis.call('GET', KEYS[1])
if not raw then return {-1, 'missing'} end
local record = cjson.decode(raw)
if record.state == 'cancelled' or record.state == 'completed' or record.state == 'failed' then
  return {-2, record.state}
end
local lease = redis.call('GET', KEYS[2])
if lease then return {0, lease} end
local generation = tonumber(record.owner_generation or 0) + 1
record.owner_generation = generation
record.owner_id = ARGV[1]
record.attempt_id = ARGV[2]
record.state = 'running'
local now = redis.call('TIME')
local now_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
record.lease_expires_at_ms = now_ms + tonumber(ARGV[3])
redis.call('SET', KEYS[1], cjson.encode(record), 'PX', ARGV[4])
redis.call('SET', KEYS[2], ARGV[1] .. ':' .. generation, 'PX', ARGV[3])
return {1, generation, cjson.encode(record)}
"""

_HEARTBEAT_SCRIPT = """
local raw = redis.call('GET', KEYS[1])
local lease = redis.call('GET', KEYS[2])
if not raw or lease ~= ARGV[1] then return 0 end
local record = cjson.decode(raw)
if record.state ~= 'running' or record.owner_id .. ':' .. record.owner_generation ~= ARGV[1] then return 0 end
local now = redis.call('TIME')
local now_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
record.lease_expires_at_ms = now_ms + tonumber(ARGV[2])
redis.call('SET', KEYS[1], cjson.encode(record), 'PX', ARGV[3])
redis.call('PEXPIRE', KEYS[2], ARGV[2])
return 1
"""

_COMMIT_SCRIPT = """
local raw = redis.call('GET', KEYS[1])
local lease = redis.call('GET', KEYS[2])
if not raw then return {-1, 'missing'} end
local record = cjson.decode(raw)
if record.state == 'completed' and record.result_digest == ARGV[2] then return {1, 'completed'} end
if record.state == 'cancelled' then return {-2, 'cancelled'} end
if lease ~= ARGV[1] or record.owner_id .. ':' .. record.owner_generation ~= ARGV[1] then return {0, 'lease_lost'} end
if record.state ~= 'running' then return {-3, record.state} end
record.state = 'completed'
record.result_digest = ARGV[2]
record.owner_id = false
record.lease_expires_at_ms = false
redis.call('SET', KEYS[1], cjson.encode(record), 'PX', ARGV[3])
redis.call('DEL', KEYS[2])
return {1, 'completed'}
"""

_CANCEL_SCRIPT = """
local raw = redis.call('GET', KEYS[1])
if not raw then return {-1, 'missing'} end
local record = cjson.decode(raw)
if record.state == 'completed' or record.state == 'cancelled' or record.state == 'failed' then return {1, record.state} end
record.state = 'cancelled'
record.owner_id = false
record.lease_expires_at_ms = false
record.cancel_requested = true
redis.call('SET', KEYS[1], cjson.encode(record), 'PX', ARGV[1])
redis.call('DEL', KEYS[2])
return {1, 'cancelled'}
"""


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DurableResearchLedger:
    """Small Valkey-native owner/lease ledger for the W5 fixture adapter."""

    def __init__(
        self,
        redis_url: str,
        *,
        namespace: str = "groktocrawl:experimental-research:v1",
        lease_ms: int = 2_000,
        retention_ms: int = 86_400_000,
        retry_window_ms: int = 3_600_000,
        redis: Redis | None = None,
    ) -> None:
        if lease_ms <= 0 or retention_ms <= 0 or retry_window_ms <= 0:
            raise ValueError("durable recovery bounds must be positive")
        if retry_window_ms > retention_ms:
            raise ValueError("retry window cannot exceed retention")
        self.redis = redis or Redis.from_url(redis_url, decode_responses=True)
        self.namespace = namespace
        self.lease_ms = lease_ms
        self.retention_ms = retention_ms
        self.retry_window_ms = retry_window_ms

    def _key(self, kind: str, value: str) -> str:
        return f"{self.namespace}:{kind}:{value}"

    def _run_key(self, run_id: str) -> str:
        return self._key("run", run_id)

    def _lease_key(self, run_id: str) -> str:
        return self._key("lease", run_id)

    def _idempotency_key(self, scope_id: str, key: str) -> str:
        return self._key("idempotency", f"{_digest(scope_id)}:{_digest(key)}")

    def _index_key(self) -> str:
        return self._key("index", "runs")

    def admit(
        self,
        scope_id: str,
        idempotency_key: str,
        request_digest: str,
        *,
        payload: dict[str, Any] | None = None,
        run_id: str | None = None,
        now_ms: int | None = None,
    ) -> DurableRun:
        """Durably admit once, returning the same run for identical retries."""
        selected_run_id = run_id or str(uuid4())
        created_at = int(time.time() * 1000) if now_ms is None else now_ms
        record = {
            "schema_version": "durable-research/1",
            "run_id": selected_run_id,
            "scope_id": scope_id,
            "request_digest": request_digest,
            "state": "admitted",
            "owner_id": None,
            "owner_generation": 0,
            "attempt_id": None,
            "result_digest": None,
            "retry_deadline_ms": created_at + self.retry_window_ms,
            "created_at_ms": created_at,
            "payload": payload or {},
        }
        result = self.redis.eval(
            _ADMIT_SCRIPT,
            3,
            self._idempotency_key(scope_id, idempotency_key),
            self._run_key(selected_run_id),
            self._index_key(),
            selected_run_id,
            request_digest,
            json.dumps(record, separators=(",", ":")),
            str(self.retention_ms),
        )
        code, returned_id = int(result[0]), str(result[1])
        if code == 2:
            raise DurableConflictError("idempotency key conflicts with retained input")
        raw = self.redis.get(self._run_key(returned_id))
        if raw is None:
            raise DurableResearchError("admitted run disappeared before read")
        return DurableRun.from_record(json.loads(raw))

    def get(self, run_id: str) -> DurableRun | None:
        raw = self.redis.get(self._run_key(run_id))
        return None if raw is None else DurableRun.from_record(json.loads(raw))

    def claim(self, run_id: str, owner_id: str, *, attempt_id: str | None = None) -> DurableRun:
        """Claim or reclaim work with a monotonic fencing generation."""
        result = self.redis.eval(
            _CLAIM_SCRIPT,
            2,
            self._run_key(run_id),
            self._lease_key(run_id),
            owner_id,
            attempt_id or str(uuid4()),
            str(self.lease_ms),
            str(self.retention_ms),
        )
        code = int(result[0])
        if code == 0:
            raise DurableConflictError("run is owned by another live lease")
        if code == -1:
            raise DurableResearchError("run is missing")
        if code == -2:
            raise DurableConflictError(f"run is already terminal: {result[1]}")
        return DurableRun.from_record(json.loads(str(result[2])))

    def heartbeat(self, run_id: str, owner_id: str, generation: int) -> None:
        token = f"{owner_id}:{generation}"
        result = self.redis.eval(
            _HEARTBEAT_SCRIPT,
            2,
            self._run_key(run_id),
            self._lease_key(run_id),
            token,
            str(self.lease_ms),
            str(self.retention_ms),
        )
        if int(result) != 1:
            raise LeaseLostError("heartbeat rejected by the fencing authority")

    def commit_result(self, run_id: str, owner_id: str, generation: int, result_digest: str) -> DurableRun:
        """Commit one terminal receipt, rejecting stale owners and cancellation."""
        token = f"{owner_id}:{generation}"
        result = self.redis.eval(
            _COMMIT_SCRIPT,
            2,
            self._run_key(run_id),
            self._lease_key(run_id),
            token,
            result_digest,
            str(self.retention_ms),
        )
        code, detail = int(result[0]), str(result[1])
        if code == 0:
            raise LeaseLostError("terminal commit rejected for stale owner")
        if code == -1:
            raise DurableResearchError("run is missing")
        if code == -2:
            raise DurableConflictError("cancellation already won the terminal race")
        if code == -3:
            raise DurableConflictError(f"run is not committable: {detail}")
        snapshot = self.get(run_id)
        if snapshot is None:
            raise DurableResearchError("committed run disappeared before read")
        return snapshot

    def cancel(self, run_id: str) -> DurableRun:
        """Persist cancellation before any worker can publish a result."""
        result = self.redis.eval(
            _CANCEL_SCRIPT,
            2,
            self._run_key(run_id),
            self._lease_key(run_id),
            str(self.retention_ms),
        )
        if int(result[0]) == -1:
            raise DurableResearchError("run is missing")
        snapshot = self.get(run_id)
        if snapshot is None:
            raise DurableResearchError("cancelled run disappeared before read")
        return snapshot

    def reclaimable(self) -> list[DurableRun]:
        """Return admitted/running work whose lease is absent for recovery."""
        runs: list[DurableRun] = []
        for run_id in self.redis.smembers(self._index_key()):
            snapshot = self.get(str(run_id))
            if snapshot is None or snapshot.state not in {"admitted", "running"}:
                continue
            if self.redis.exists(self._lease_key(snapshot.run_id)):
                continue
            runs.append(snapshot)
        return sorted(runs, key=lambda item: item.created_at_ms)
