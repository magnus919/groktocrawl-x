"""Fixture-backed W6 run, replay, artifact, evidence, and deletion adapters."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from agent.routes import experimental_research as experimental
from fastapi import FastAPI


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("FEATURE_EXPERIMENTAL_RESEARCH", "true")
    monkeypatch.setenv("FEATURE_EXPERIMENTAL_RESEARCH_RUNS", "true")
    experimental._RUNS.clear()
    experimental._IDEMPOTENCY.clear()
    value = FastAPI()
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
    raise AssertionError("fixture run did not reach a terminal state")


@pytest.mark.asyncio
async def test_run_idempotency_status_replay_and_retained_reads(app: FastAPI) -> None:
    async with await _client(app) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "run-1"},
            json={"objective": "Assess the fictional pilot"},
        )
        assert created.status_code == 202
        admission = created.json()
        duplicate = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "run-1"},
            json={"objective": "Assess the fictional pilot"},
        )
        assert duplicate.status_code == 202
        assert duplicate.json()["run_id"] == admission["run_id"]

        conflict = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "run-1"},
            json={"objective": "A different objective"},
        )
        assert conflict.status_code == 409

        status = await _wait_for_terminal(client, admission["run_id"])
        assert status["state"] == "completed"
        result = status["result"]
        assert result["research_id"] == admission["research_id"]

        events = await client.get(admission["events_url"])
        assert events.status_code == 200
        assert "event: done" in events.text
        first_event_id = events.text.split("id: ", 1)[1].split("\n", 1)[0]
        replay = await client.get(
            admission["events_url"], headers={"Last-Event-ID": first_event_id}
        )
        assert replay.status_code == 200
        assert first_event_id not in replay.text

        manifest = await client.get(result["manifest_url"])
        assert manifest.status_code == 200
        artifact = await client.get(result["artifacts"]["summary"])
        assert artifact.status_code == 200
        evidence = await client.get(
            f"/experimental/research/v1/research/{result['research_id']}/evidence/source-1"
        )
        assert evidence.status_code == 200
        assert evidence.json()["content_digest"]

        deleted = await client.delete(
            f"/experimental/research/v1/research/{result['research_id']}"
        )
        assert deleted.status_code == 202
        assert (await client.get(result["manifest_url"])).status_code == 410
        assert (await client.get(result["artifacts"]["summary"])).status_code == 410
        assert (
            await client.get(
                f"/experimental/research/v1/research/{result['research_id']}/evidence/source-1"
            )
        ).status_code == 410


@pytest.mark.asyncio
async def test_cancel_returns_one_cancelled_terminal(app: FastAPI) -> None:
    async with await _client(app) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "cancel-1"},
            json={"objective": "Cancel the fictional pilot"},
        )
        run_id = created.json()["run_id"]
        cancelled = await client.post(
            f"/experimental/research/v1/runs/{run_id}/cancel"
        )
        assert cancelled.status_code == 202
        status = await _wait_for_terminal(client, run_id)
        assert status["state"] == "cancelled"
        events = await client.get(created.json()["events_url"])
        assert events.text.count("event: cancelled") == 1
        assert "event: done" not in events.text
