from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from curl_cffi.const import CurlOpt

_SCRAPER_SVC = Path(__file__).parents[2] / "scraper-svc"
if str(_SCRAPER_SVC) not in sys.path:
    sys.path.insert(0, str(_SCRAPER_SVC))

from scraper.source_http import (
    CAPTURE_EGRESS_PROXY_ENV,
    SourceTransportConfigurationError,
    source_curl_options,
    source_httpx_client,
    source_httpx_sync_client,
    trusted_control_httpx_client,
)


def test_source_httpx_client_preserves_default_constructor(monkeypatch):
    monkeypatch.delenv(CAPTURE_EGRESS_PROXY_ENV, raising=False)
    constructor = Mock(return_value="client")
    monkeypatch.setattr(httpx, "AsyncClient", constructor)

    assert source_httpx_client(timeout=12) == "client"
    constructor.assert_called_once_with(timeout=12)


def test_protected_source_httpx_forces_gateway_and_disables_environment(monkeypatch):
    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080/")
    constructor = Mock(return_value="client")
    monkeypatch.setattr(httpx, "AsyncClient", constructor)

    source_httpx_client(timeout=12, proxy="http://caller-proxy.example:3128")

    constructor.assert_called_once_with(
        timeout=12,
        proxy="http://egress-gateway.example:8080",
        trust_env=False,
    )


@pytest.mark.parametrize(
    "value",
    [
        "https://egress.example:8080",
        "http://user:secret@egress.example:8080",
        "http://egress.example:99999",
        "http://egress.example/path",
        "http://[broken:8080",
    ],
)
def test_invalid_gateway_configuration_fails_before_client_creation(monkeypatch, value):
    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, value)
    constructor = Mock()
    monkeypatch.setattr(httpx, "AsyncClient", constructor)

    with pytest.raises(SourceTransportConfigurationError):
        source_httpx_client(timeout=2)
    constructor.assert_not_called()


@pytest.mark.parametrize(
    "bypass", [{"transport": object()}, {"mounts": {"all://": object()}}]
)
def test_protected_source_httpx_rejects_custom_transport_bypass(monkeypatch, bypass):
    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    constructor = Mock()
    monkeypatch.setattr(httpx, "AsyncClient", constructor)

    with pytest.raises(
        SourceTransportConfigurationError, match="custom-source-transport"
    ):
        source_httpx_client(**bypass)
    constructor.assert_not_called()


def test_sync_substack_source_probe_uses_gateway(monkeypatch):
    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    constructor = Mock(return_value="client")
    monkeypatch.setattr(httpx, "Client", constructor)

    source_httpx_sync_client(follow_redirects=True)

    constructor.assert_called_once_with(
        follow_redirects=True,
        proxy="http://egress-gateway.example:8080",
        trust_env=False,
    )


def test_curl_options_override_residential_proxy_only_when_protected(monkeypatch):
    monkeypatch.delenv(CAPTURE_EGRESS_PROXY_ENV, raising=False)
    assert source_curl_options(compatibility_proxy="http://residential.example") == {
        "proxy": "http://residential.example"
    }

    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    assert source_curl_options(compatibility_proxy="http://residential.example") == {
        "proxy": "http://egress-gateway.example:8080",
        "trust_env": False,
        "curl_options": {CurlOpt.NOPROXY: ""},
    }


def test_fixed_control_client_does_not_inherit_source_proxy(monkeypatch):
    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    constructor = Mock(return_value="control")
    monkeypatch.setattr(httpx, "AsyncClient", constructor)

    assert trusted_control_httpx_client(timeout=7) == "control"
    constructor.assert_called_once_with(timeout=7, trust_env=False)


def test_unqualified_nested_source_tools_are_refused_before_dispatch(monkeypatch):
    from scraper import fetch_tiers

    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    control_client = Mock(
        side_effect=AssertionError("control request must not be sent")
    )
    browser_fetch = AsyncMock(side_effect=AssertionError("browser must not launch"))
    monkeypatch.setattr(fetch_tiers, "trusted_control_httpx_client", control_client)
    monkeypatch.setattr(fetch_tiers, "_playwright_fetch_with_proxy", browser_fetch)

    assert (
        asyncio.run(fetch_tiers.fetch_via_playwright("https://source.example")) is None
    )
    assert (
        asyncio.run(fetch_tiers.fetch_via_flaresolverr("https://source.example"))
        is None
    )
    assert (
        asyncio.run(fetch_tiers._fetch_via_browser_svc("https://source.example"))
        is None
    )
    browser_fetch.assert_not_awaited()
    control_client.assert_not_called()


def test_adapter_browser_fallbacks_are_refused_before_control_dispatch(monkeypatch):
    from scraper.adapters import bluesky, shopify, substack, youtube
    from scraper.adapters.base import AdapterContext

    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    context = AdapterContext()
    for module in (bluesky, shopify, substack, youtube):
        monkeypatch.setattr(
            module,
            "trusted_control_httpx_client",
            Mock(side_effect=AssertionError("browser control must not be called")),
        )

    assert (
        asyncio.run(bluesky._fetch_via_browser("https://source.example", context))
        is None
    )
    assert (
        asyncio.run(shopify._fetch_via_browser("https://source.example", context))
        is None
    )
    assert (
        asyncio.run(substack._fetch_via_browser("https://source.example", context))
        is None
    )
    assert (
        asyncio.run(
            youtube._fetch_via_browser("https://source.example", "video", context)
        )
        is None
    )


def test_all_adapter_http_clients_use_the_source_factory():
    adapters_dir = Path(__file__).parents[2] / "scraper-svc" / "scraper" / "adapters"
    for path in adapters_dir.glob("*.py"):
        tree = ast.parse(path.read_text())
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "httpx"
            and node.func.attr in {"AsyncClient", "Client", "get", "post", "request"}
        ]
        assert not calls, f"direct source HTTP client remains in {path.name}"
    helper = (adapters_dir / "_helpers.py").read_text()
    assert "source_httpx_client(" in helper


def test_all_scraper_httpx_clients_are_classified_by_the_factory():
    scraper_dir = Path(__file__).parents[2] / "scraper-svc" / "scraper"
    for path in scraper_dir.rglob("*.py"):
        if path.name == "source_http.py":
            continue
        tree = ast.parse(path.read_text())
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "httpx"
            and node.func.attr in {"AsyncClient", "Client", "get", "post", "request"}
        ]
        assert not calls, (
            f"unclassified HTTPX client remains in {path.relative_to(scraper_dir)}"
        )


def test_protected_curl_ignores_no_proxy_with_local_proxy_fixture(monkeypatch):
    from curl_cffi import requests as curl_requests

    async def scenario():
        proxy_requests = []
        origin_requests = []

        async def respond(reader, writer, captured, body):
            request = await reader.readuntil(b"\r\n\r\n")
            captured.append(request)
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                + f"Content-Length: {len(body)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + body
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        async def proxy_handler(reader, writer):
            await respond(reader, writer, proxy_requests, b"gateway")

        async def origin_handler(reader, writer):
            await respond(reader, writer, origin_requests, b"origin")

        origin = await asyncio.start_server(origin_handler, "127.0.0.1", 0)
        proxy = await asyncio.start_server(proxy_handler, "127.0.0.1", 0)
        origin_port = origin.sockets[0].getsockname()[1]
        proxy_port = proxy.sockets[0].getsockname()[1]
        monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, f"http://127.0.0.1:{proxy_port}")
        monkeypatch.setenv("NO_PROXY", "127.0.0.1")
        monkeypatch.setenv("no_proxy", "127.0.0.1")
        try:
            async with curl_requests.AsyncSession(
                timeout=3,
                **source_curl_options(compatibility_proxy=None),
            ) as client:
                response = await client.get(f"http://127.0.0.1:{origin_port}/proof")
            assert response.text == "gateway"
            assert len(proxy_requests) == 1
            assert proxy_requests[0].startswith(
                f"GET http://127.0.0.1:{origin_port}/proof ".encode()
            )
            assert origin_requests == []
        finally:
            proxy.close()
            origin.close()
            await proxy.wait_closed()
            await origin.wait_closed()

    asyncio.run(scenario())
