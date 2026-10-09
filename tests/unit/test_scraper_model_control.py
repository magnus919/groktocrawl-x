"""Model calls are fixed-target UDS capabilities, not scraper-selected URLs."""

from __future__ import annotations

import asyncio

import httpx
from scraper import llm_control
from scraper.source_http import trusted_llm_upstream_client


def test_model_broker_injects_secret_and_uses_only_configured_endpoint(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://model.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "broker-only-test-key")
    observed = []

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"choices":[]}'

        async def aclose(self):
            return None

    async def upstream(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(
            200, headers={"content-type": "application/json"}, stream=Stream()
        )

    async def run():
        llm_control.app.state.clients = {
            "recovery": httpx.AsyncClient(transport=httpx.MockTransport(upstream)),
            "captcha": httpx.AsyncClient(transport=httpx.MockTransport(upstream)),
        }
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=llm_control.app),
            base_url="http://control.sock",
        ) as client:
            response = await client.post(
                "/recovery/chat/completions",
                json={"model": "operator-alias", "messages": [{"role": "user", "content": "page"}]},
            )
            denied = await client.post("/recovery/v1/chat/completions", json={})
        for client in llm_control.app.state.clients.values():
            await client.aclose()
        return response, denied

    response, denied = asyncio.run(run())
    assert response.status_code == 200
    assert denied.status_code == 404
    assert len(observed) == 1
    request = observed[0]
    assert request.url == "https://model.example/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer broker-only-test-key"
    assert b"operator-alias" in request.content


def test_upstream_client_routes_all_targets_through_model_gateway(monkeypatch):
    monkeypatch.setenv("MODEL_EGRESS_PROXY_URL", "http://gateway.internal:8080")
    calls = []

    def fake_client(**kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)
    trusted_llm_upstream_client(
        "http://llm-svc:4001/v1/chat/completions"
    )
    trusted_llm_upstream_client(
        "https://model.example/v1/chat/completions"
    )

    expected = {
        "follow_redirects": False,
        "proxy": "http://gateway.internal:8080",
        "trust_env": False,
    }
    assert calls == [expected, expected]
