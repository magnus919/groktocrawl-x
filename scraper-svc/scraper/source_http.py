"""HTTP clients for hostile source traffic and fixed trusted controls.

When ``SCRAPER_CAPTURE_EGRESS_PROXY_URL`` is configured, source clients are
forced through that proxy with environment proxy discovery disabled. Invalid
configuration fails before a request can be sent. This covers HTTPX and curl
source fetches; browser and remote recovery fetchers must use the guard below
until they have an independently qualified route through the gateway.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

import httpx
from curl_cffi.const import CurlOpt

CAPTURE_EGRESS_PROXY_ENV = "SCRAPER_CAPTURE_EGRESS_PROXY_URL"


class SourceTransportConfigurationError(RuntimeError):
    """The configured source route cannot be used safely."""


class ProtectedSourceToolUnavailableError(RuntimeError):
    """A source-fetching tool has no qualified protected-mode route."""


def capture_egress_proxy_url() -> str | None:
    """Return a validated HTTP gateway URL, or ``None`` in compatibility mode."""
    raw = os.environ.get(CAPTURE_EGRESS_PROXY_ENV, "")
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise SourceTransportConfigurationError("capture-egress-proxy-invalid") from exc
    if (
        parsed.scheme.lower() != "http"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
        or any(ch.isspace() for ch in raw)
    ):
        raise SourceTransportConfigurationError("capture-egress-proxy-invalid")
    return raw.rstrip("/")


def protected_source_mode() -> bool:
    """Whether source HTTP traffic is configured to require the gateway."""
    return bool(os.environ.get(CAPTURE_EGRESS_PROXY_ENV, ""))


def source_httpx_client(**kwargs) -> httpx.AsyncClient:
    """Create an HTTPX client for source-selected destinations.

    Default mode leaves HTTPX behavior untouched. Protected mode overrides any
    caller-supplied proxy and disables environment proxy discovery, so a bad
    gateway cannot trigger a direct retry. Custom transports and mounts are
    rejected because they can bypass the configured route.
    """
    proxy_url = capture_egress_proxy_url()
    if proxy_url is not None:
        if "transport" in kwargs or "mounts" in kwargs:
            raise SourceTransportConfigurationError("custom-source-transport-forbidden")
        kwargs["proxy"] = proxy_url
        kwargs["trust_env"] = False
    return httpx.AsyncClient(**kwargs)


def source_httpx_sync_client(**kwargs) -> httpx.Client:
    """Create a synchronous HTTPX client for source-selected destinations."""
    proxy_url = capture_egress_proxy_url()
    if proxy_url is not None:
        if "transport" in kwargs or "mounts" in kwargs:
            raise SourceTransportConfigurationError("custom-source-transport-forbidden")
        kwargs["proxy"] = proxy_url
        kwargs["trust_env"] = False
    return httpx.Client(**kwargs)


def source_curl_options(*, compatibility_proxy: str | None) -> dict[str, object]:
    """Build curl-cffi options, preserving the old proxy in default mode."""
    proxy_url = capture_egress_proxy_url()
    if proxy_url is not None:
        return {
            "proxy": proxy_url,
            "trust_env": False,
            "curl_options": {CurlOpt.NOPROXY: ""},
        }
    return {"proxy": compatibility_proxy}


def source_requests_session() -> Any | None:
    """Return a requests session pinned to the gateway, only in protected mode.

    ``None`` preserves third-party libraries' existing default session
    construction in compatibility mode.
    """
    proxy_url = capture_egress_proxy_url()
    if proxy_url is None:
        return None
    import requests

    session = requests.Session()
    session.trust_env = False
    session.proxies.update({"http": proxy_url, "https": proxy_url})
    return session


def trusted_control_httpx_client(**kwargs) -> httpx.AsyncClient:
    """Create an environment-independent client for a fixed control endpoint."""
    kwargs["trust_env"] = False
    return httpx.AsyncClient(**kwargs)


def require_unprotected_source_tool(tool_name: str) -> None:
    """Fail before dispatching a source fetch through an unqualified tool."""
    if protected_source_mode():
        raise ProtectedSourceToolUnavailableError(
            f"protected-source-tool-unavailable:{tool_name}"
        )
