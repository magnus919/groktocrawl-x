"""Bounded durable status recovery through the experimental route."""

from __future__ import annotations

import asyncio
import os

import httpx
import pytest
from agent.experimental.durable_research import DurableResearchLedger
from agent.routes import experimental_research as experimental
from fastapi import FastAPI
from redis import Redis


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    # The dedicated URL is used by the isolated Valkey lanes. The compose
    # integration lane already provides the same durable store as VALKEY_URL.
    url = os.environ.get("DURABLE_RESEARCH_REDIS_URL") or os.environ.get("VALKEY_URL")
    if url is None:
        raise RuntimeError("DURABLE_RESEARCH_REDIS_URL or VALKEY_URL is required")
    monkeypatch.setenv("FEATURE_EXPERIMENTAL_RESEARCH", "true")
    monkeypatch.setenv("FEATURE_EXPERIMENTAL_RESEARCH_RUNS", "true")
    monkeypatch.setenv("FEATURE_EXPERIMENTAL_RESEARCH_DURABLE", "true")
    Redis.from_url(url, decode_responses=True).flushdb()
    experimental._RUNS.clear()
    experimental._IDEMPOTENCY.clear()
    experimental._DURABLE_LEDGERS.clear()
    value = FastAPI()
    value.state.valkey_url = url
    value.include_router(experimental.router)
    return value


async def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def _wait_for_terminal(client: httpx.AsyncClient, run_id: str) -> dict:
    for _ in range(100):
        response = await client.get(f"/experimental/research/v1/runs/{run_id}")
        payload = response.json()
        if payload["state"] in {"completed", "failed", "cancelled"}:
            return payload
        await asyncio.sleep(0)
    raise AssertionError("durable fixture run did not reach a terminal state")


@pytest.mark.asyncio
async def test_status_recovers_from_durable_terminal_projection(app: FastAPI) -> None:
    async with await _client(app) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "durable-status-1"},
            json={"objective": "Recover durable status"},
        )
        assert created.status_code == 202
        admission = created.json()
        status = await _wait_for_terminal(client, admission["run_id"])
        assert status["state"] == "completed"

        url = os.environ.get("DURABLE_RESEARCH_REDIS_URL") or os.environ["VALKEY_URL"]
        ledger = DurableResearchLedger(url)
        durable = ledger.get(admission["run_id"])
        assert durable is not None
        assert durable.checkpoint_name == "terminal_projection"
        assert durable.terminal_payload is not None

        experimental._RUNS.clear()
        recovered = await client.get(admission["status_url"])
        assert recovered.status_code == 200
        assert recovered.json()["state"] == "completed"
        assert recovered.json()["result"] == status["result"]


@pytest.mark.asyncio
async def test_cancel_persists_durable_terminal_state(app: FastAPI) -> None:
    async with await _client(app) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "durable-cancel-1"},
            json={"objective": "Cancel durable status"},
        )
        assert created.status_code == 202
        run_id = created.json()["run_id"]
        cancelled = await client.post(
            f"/experimental/research/v1/runs/{run_id}/cancel"
        )
        assert cancelled.status_code == 202
        assert cancelled.json()["state"] == "cancelled"

        durable = DurableResearchLedger(
            os.environ.get("DURABLE_RESEARCH_REDIS_URL") or os.environ["VALKEY_URL"]
        ).get(run_id)
        assert durable is not None
        assert durable.state == "cancelled"
