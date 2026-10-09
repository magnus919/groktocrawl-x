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
    trusted_control_base_url,
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


@pytest.mark.parametrize(
    ("service", "value", "expected"),
    [
        (
            "browser",
            "http://candidate-browser-controller:8012",
            "http://candidate-browser-controller:8012",
        ),
        (
            "flare",
            "http://candidate-flare-control:8191/v1",
            "http://candidate-flare-control:8191/v1",
        ),
    ],
)
def test_protected_control_urls_are_fixed(service, value, expected, monkeypatch):
    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    assert trusted_control_base_url(value, service) == expected


@pytest.mark.parametrize(
    "value",
    [
        "http://candidate-valkey:6379",
        "http://candidate-browser-controller:8012/other",
        "http://user@candidate-browser-controller:8012",
        "https://candidate-flare-control:8191/v1",
    ],
)
def test_protected_control_url_rejects_nonfixed_authorities(value, monkeypatch):
    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    service = "flare" if "flare" in value else "browser"
    with pytest.raises(SourceTransportConfigurationError, match="trusted-control-url"):
        trusted_control_base_url(value, service)


def test_protected_tier3_delegates_to_isolated_browser_service(monkeypatch):
    from scraper import fetch_tiers

    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    monkeypatch.setattr(
        fetch_tiers, "FLARE_SOLVERR_URL", "http://candidate-flare-control:8191/v1"
    )
    isolated_fetch = AsyncMock(
        return_value={"markdown": "isolated", "source": "browser-svc"}
    )
    browser_fetch = AsyncMock(side_effect=AssertionError("browser must not launch"))
    monkeypatch.setattr(fetch_tiers, "_fetch_via_browser_svc", isolated_fetch)
    monkeypatch.setattr(fetch_tiers, "_playwright_fetch_with_proxy", browser_fetch)

    assert asyncio.run(fetch_tiers.fetch_via_playwright("https://source.example")) == {
        "markdown": "isolated",
        "source": "browser-svc",
    }
    isolated_fetch.assert_awaited_once_with("https://source.example")
    browser_fetch.assert_not_awaited()


def test_protected_flaresolverr_uses_separate_control_client(monkeypatch):
    from types import SimpleNamespace

    from scraper import fetch_tiers

    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    monkeypatch.setattr(
        fetch_tiers, "FLARE_SOLVERR_URL", "http://candidate-flare-control:8191/v1"
    )
    response = Mock(status_code=200)
    response.json.return_value = {
        "solution": {"status": 200, "response": "<html>fixture</html>"}
    }
    client = Mock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=response)
    constructor = Mock(return_value=client)
    monkeypatch.setattr(fetch_tiers, "trusted_control_httpx_client", constructor)
    monkeypatch.setattr(fetch_tiers, "html_to_markdown", Mock(return_value="x" * 80))
    monkeypatch.setattr(
        fetch_tiers,
        "_classify_barrier",
        Mock(return_value=SimpleNamespace(detected=False, confidence=0.0)),
    )

    result = asyncio.run(fetch_tiers.fetch_via_flaresolverr("https://source.example"))

    assert result["source"] == "flare-solverr"
    constructor.assert_called_once_with(timeout=60)
    client.post.assert_awaited_once()


def test_candidate_scraper_is_not_attached_to_direct_egress_network():
    import yaml

    compose_path = Path(__file__).parents[2] / "compose.experimental-candidate.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    scraper = compose["services"]["candidate-scraper"]
    networks = scraper["networks"]
    if isinstance(networks, dict):
        network_names = set(networks)
    else:
        network_names = set(networks)

    assert "candidate_egress" not in network_names
    assert {"candidate_capture", "candidate_private"} <= network_names
    assert compose["networks"]["candidate_capture"]["internal"] is True
    assert (
        scraper["environment"]["SCRAPER_CAPTURE_EGRESS_PROXY_URL"]
        == "http://172.31.254.2:8080"
    )


def test_adapter_browser_fallbacks_remain_available_in_protected_mode(monkeypatch):
    from scraper.adapters import bluesky, shopify, substack, youtube
    from scraper.adapters.base import AdapterContext

    monkeypatch.setenv(CAPTURE_EGRESS_PROXY_ENV, "http://egress-gateway.example:8080")
    context = AdapterContext(
        config={"BROWSER_SVC_URL": "http://candidate-browser-controller:8012"}
    )
    response = Mock(status_code=200)
    response.json.return_value = {
        "id": "session-1",
        "success": True,
        "result": {"script_result": "x" * 250},
    }
    client = Mock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=response)
    client.delete = AsyncMock(return_value=response)
    for module in (bluesky, shopify, substack, youtube):
        monkeypatch.setattr(
            module,
            "trusted_control_httpx_client",
            Mock(return_value=client),
        )

    assert asyncio.run(bluesky._fetch_via_browser("https://source.example", context))
    assert asyncio.run(shopify._fetch_via_browser("https://source.example", context))
    assert asyncio.run(substack._fetch_via_browser("https://source.example", context))
    assert asyncio.run(youtube._fetch_via_browser("https://source.example", "video", context))
    assert client.post.await_count > 0


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
