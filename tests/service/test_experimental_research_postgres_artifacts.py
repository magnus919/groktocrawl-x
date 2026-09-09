"""PostgreSQL-authority route projection and reconciliation contracts."""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import os
import runpy
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from agent.experimental.artifact_authority import (
    ArtifactAuthority,
    RetainedArtifactSet,
)
from agent.experimental.durable_research import DurableResearchLedger
from agent.experimental.source_store import StorageConflictError
from agent.routes import experimental_research as experimental
from fastapi import FastAPI
from redis import Redis


class FakeAuthority:
    def __init__(self) -> None:
        self.values: dict[tuple[UUID, UUID], RetainedArtifactSet] = {}
        self.deleted: set[tuple[UUID, UUID]] = set()
        self.commits = 0
        self.deletions = 0

    async def ensure_scope(self, scope: UUID) -> None:
        return None

    async def commit(
        self,
        scope: UUID,
        research: UUID,
        run: UUID,
        artifact_set: UUID,
        manifest: bytes,
        artifacts: dict[str, tuple[str, bytes]],
    ) -> RetainedArtifactSet:
        self.commits += 1
        manifest_digest, retained, set_digest, _ = ArtifactAuthority._validate(
            manifest, artifacts
        )
        candidate = RetainedArtifactSet(
            scope,
            research,
            run,
            artifact_set,
            manifest,
            manifest_digest,
            set_digest,
            retained,
        )
        if (scope, research) in self.deleted:
            raise StorageConflictError("artifact set replay changed")
        prior = self.values.get((scope, research))
        if prior is not None and prior != candidate:
            raise StorageConflictError("artifact set replay changed")
        self.values[(scope, research)] = candidate
        return candidate

    async def read(self, scope: UUID, research: UUID) -> RetainedArtifactSet:
        if (scope, research) in self.deleted:
            raise StorageConflictError("artifact set unavailable")
        try:
            return self.values[(scope, research)]
        except KeyError as exc:
            raise StorageConflictError("artifact set unavailable") from exc

    async def find_run(self, scope: UUID, run: UUID) -> RetainedArtifactSet | None:
        return next(
            (
                value
                for value in self.values.values()
                if value.scope_id == scope and value.run_id == run
            ),
            None,
        )

    async def delete(self, scope: UUID, research: UUID) -> None:
        self.deletions += 1
        self.deleted.add((scope, research))
        self.values.pop((scope, research), None)


@pytest.fixture
def authority_app(monkeypatch: pytest.MonkeyPatch):
    url = os.environ.get("DURABLE_RESEARCH_REDIS_URL") or os.environ.get("VALKEY_URL")
    if url is None:
        raise RuntimeError("DURABLE_RESEARCH_REDIS_URL or VALKEY_URL is required")
    # The older durable-route suite flushes database 15. Give each xdist worker
    # a separate database so fixture cleanup cannot delete another test's run.
    worker = os.environ.get("PYTEST_XDIST_WORKER", "local")
    database = 14 if worker == "local" else 10 + int(worker.removeprefix("gw"))
    url = f"{url.rsplit('/', 1)[0]}/{database}"
    for name in (
        "EXPERIMENTAL_RESEARCH",
        "EXPERIMENTAL_RESEARCH_RUNS",
        "EXPERIMENTAL_RESEARCH_DURABLE",
        "EXPERIMENTAL_RESEARCH_POSTGRES_ARTIFACTS",
    ):
        monkeypatch.setenv(f"FEATURE_{name}", "true")
    Redis.from_url(url, decode_responses=True).flushdb()
    experimental._RUNS.clear()
    experimental._IDEMPOTENCY.clear()
    experimental._DURABLE_LEDGERS.clear()
    experimental._ARTIFACT_AUTHORITIES.clear()
    authority = FakeAuthority()
    experimental._ARTIFACT_AUTHORITIES["fixture-postgres"] = authority  # type: ignore[assignment]
    app = FastAPI()
    app.state.valkey_url = url
    app.state.research_postgres_dsn = "fixture-postgres"
    app.include_router(experimental.router)
    return app, authority, url


async def _wait(client: httpx.AsyncClient, url: str) -> dict:
    for _ in range(200):
        response = await client.get(url)
        if response.json()["state"] in {"completed", "failed", "cancelled"}:
            return response.json()
        await asyncio.sleep(0.01)
    raise AssertionError("run did not finish")


@pytest.mark.asyncio
async def test_valkey_has_pointers_and_postgres_recovers_exact_bytes(
    authority_app,
) -> None:
    app, authority, url = authority_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "postgres-authority"},
            json={"objective": "Retain exact artifacts"},
        )
        status = await _wait(client, created.json()["status_url"])
        raw = DurableResearchLedger(url).redis.get(
            DurableResearchLedger(url)._run_key(status["run_id"])
        )
        terminal = json.loads(raw)["terminal_payload"]
        assert "artifact_authority" in terminal
        assert "manifest" not in terminal
        assert "body_b64" not in json.dumps(terminal)
        assert "summary" not in terminal["result"]
        assert all(
            "summary" not in (event.get("result") or {}) for event in terminal["events"]
        )

        original = await client.get(status["result"]["artifacts"]["summary"])
        experimental._RUNS.clear()
        recovered = await client.get(status["result"]["artifacts"]["summary"])
        assert recovered.content == original.content
        assert authority.commits == 1


@pytest.mark.asyncio
async def test_postgres_commit_reconciles_after_valkey_interruption(
    authority_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, authority, url = authority_app
    original = DurableResearchLedger.commit_result
    interrupted = True

    def interrupt_once(self, *args, **kwargs):
        nonlocal interrupted
        if interrupted:
            interrupted = False
            raise RuntimeError("simulated projection interruption")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(DurableResearchLedger, "commit_result", interrupt_once)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "interrupted-projection"},
            json={"objective": "Reconcile committed artifacts"},
        )
        task = experimental._RUNS[created.json()["run_id"]].task
        assert task is not None
        with pytest.raises(RuntimeError, match="projection interruption"):
            await task
        ledger = DurableResearchLedger(url)
        ledger.redis.delete(ledger._lease_key(created.json()["run_id"]))
        experimental._RUNS.clear()
        await client.get(created.json()["status_url"])
        status = await _wait(client, created.json()["status_url"])
        assert status["state"] == "completed"
        assert authority.commits == 1
        assert len(authority.values) == 1


@pytest.mark.asyncio
async def test_deletion_reaches_postgres_before_valkey(authority_app) -> None:
    app, authority, _ = authority_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "delete-authority"},
            json={"objective": "Delete retained artifacts"},
        )
        status = await _wait(client, created.json()["status_url"])
        deleted = await client.delete(
            f"/experimental/research/v1/research/{status['research_id']}"
        )
        assert deleted.status_code == 202
        assert authority.deletions == 1
        experimental._RUNS.clear()
        assert (await client.get(created.json()["status_url"])).status_code == 410


@pytest.mark.asyncio
async def test_recovered_bytes_match_http_sse_cli_and_mcp(
    authority_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One recovered authority set remains identical on every W6 client surface."""
    app, _, _ = authority_app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/experimental/research/v1/runs",
            headers={"Idempotency-Key": "recovered-client-parity"},
            json={"objective": "Preserve one result across every client"},
        )
        original_status = await _wait(client, created.json()["status_url"])
        summary_url = original_status["result"]["artifacts"]["summary"]
        original_bytes = (await client.get(summary_url)).content

        # Simulate loss of all process-local route state. Subsequent reads must
        # reconstruct the result from Valkey pointers and PostgreSQL bytes.
        experimental._RUNS.clear()
        recovered_status = (await client.get(created.json()["status_url"])).json()
        manifest = (await client.get(recovered_status["result"]["manifest_url"])).json()
        recovered_bytes = (await client.get(summary_url)).content
        events = await client.get(created.json()["events_url"])

        assert recovered_bytes == original_bytes
        assert (
            manifest["artifact_set_id"] == recovered_status["result"]["artifact_set_id"]
        )
        assert "event: done" in events.text
        assert recovered_status["result"]["artifact_set_id"] in events.text

        summary_id = summary_url.rsplit("/", 1)[-1]

        cli_ns = runpy.run_path(
            str(Path(__file__).resolve().parents[2] / "groktocrawl")
        )
        cli_client = cli_ns["Client"](server="http://test")
        cli_response = httpx.Response(200, content=recovered_bytes)
        monkeypatch.setattr("requests.get", lambda *args, **kwargs: cli_response)
        assert (
            cli_client.experimental_research_artifact_bytes(summary_id)
            == original_bytes
        )

        module_path = (
            Path(__file__).resolve().parents[2] / "mcp-svc/groktocrawl_client.py"
        )
        spec = importlib.util.spec_from_file_location(
            "recovered_mcp_client", module_path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        mcp_client = module.GroktocrawlClient(base_url="http://test")
        mcp_client._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        mcp_artifact = await mcp_client.experimental_research_artifact(summary_id)
        await mcp_client.close()
        assert base64.b64decode(mcp_artifact["content_base64"]) == original_bytes

        foreign = await client.get(
            created.json()["status_url"], headers={"Authorization": "Bearer foreign"}
        )
        assert foreign.status_code == 404
        deleted = await client.delete(
            f"/experimental/research/v1/research/{recovered_status['research_id']}"
        )
        assert deleted.status_code == 202
        experimental._RUNS.clear()
        assert (await client.get(summary_url)).status_code == 410
        assert (await client.get(created.json()["events_url"])).status_code == 410
