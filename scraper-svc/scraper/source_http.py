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
MODEL_EGRESS_PROXY_ENV = "MODEL_EGRESS_PROXY_URL"
_PROTECTED_CONTROL_BASES = {
    "browser": ("candidate-browser-controller", 8012, ""),
    "flare": ("candidate-flare-control", 8191, "/v1"),
}
_PROTECTED_CONTROL_SOCKETS = {
    "browser": "/run/browser-control/controller.sock",
    "flare": "/run/flare-control/control.sock",
}
_TRUSTED_LLM_SOCKET = "/run/scraper-llm/control.sock"
_SCRAPER_API_SOCKET = "/run/scraper/app.sock"


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


def model_egress_proxy_url() -> str | None:
    """Return the dedicated model-only gateway, never the source gateway."""
    raw = os.environ.get(MODEL_EGRESS_PROXY_ENV, "")
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise SourceTransportConfigurationError("model-egress-proxy-invalid") from exc
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
        raise SourceTransportConfigurationError("model-egress-proxy-invalid")
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


def scraper_api_uds_client(socket_path: str) -> httpx.AsyncClient:
    """Fixed ingress transport for the three-route scraper API socket."""
    if socket_path != _SCRAPER_API_SOCKET:
        raise SourceTransportConfigurationError("scraper-api-socket-invalid")
    return httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(uds=_SCRAPER_API_SOCKET, retries=0),
        base_url="http://scraper.internal",
        trust_env=False,
    )


def trusted_control_httpx_client(
    *, service: str | None = None, **kwargs
) -> httpx.AsyncClient:
    """Create a fixed-control client, using a permissioned UDS in protected mode."""
    if "transport" in kwargs or "mounts" in kwargs:
        raise SourceTransportConfigurationError("custom-control-transport-forbidden")
    if protected_source_mode():
        socket_path = _PROTECTED_CONTROL_SOCKETS.get(service or "")
        if socket_path is None:
            raise SourceTransportConfigurationError("trusted-control-service-invalid")
        kwargs["transport"] = httpx.AsyncHTTPTransport(uds=socket_path, retries=0)
    kwargs["trust_env"] = False
    return httpx.AsyncClient(**kwargs)


def protected_llm_control_mode() -> bool:
    """Whether fixed model calls are brokered over the trusted UDS route."""
    return bool(os.environ.get("LLM_CONTROL_SOCKET"))


def trusted_llm_httpx_client(kind: str, **kwargs) -> httpx.AsyncClient:
    """Create a fixed chat-completions client, brokered in protected mode."""
    if kind not in {"recovery", "captcha"}:
        raise SourceTransportConfigurationError("trusted-model-kind-invalid")
    if protected_llm_control_mode():
        socket_path = os.environ.get("LLM_CONTROL_SOCKET", _TRUSTED_LLM_SOCKET)
        if not socket_path.startswith("/") or "\x00" in socket_path:
            raise SourceTransportConfigurationError("trusted-model-socket-invalid")
        kwargs["transport"] = httpx.AsyncHTTPTransport(uds=socket_path, retries=0)
        kwargs["base_url"] = "http://llm-control"
    elif "transport" in kwargs or "mounts" in kwargs:
        raise SourceTransportConfigurationError("custom-model-transport-forbidden")
    kwargs["trust_env"] = False
    return httpx.AsyncClient(**kwargs)


def trusted_llm_endpoint(kind: str, base_url: str) -> str:
    if kind not in {"recovery", "captcha"}:
        raise SourceTransportConfigurationError("trusted-model-kind-invalid")
    if protected_llm_control_mode():
        return f"/{kind}/chat/completions"
    return f"{base_url.rstrip('/')}/chat/completions"


def trusted_llm_headers(kind: str, api_key: str | None) -> dict[str, str]:
    if kind not in {"recovery", "captcha"}:
        raise SourceTransportConfigurationError("trusted-model-kind-invalid")
    if protected_llm_control_mode() or not api_key:
        return {"Content-Type": "application/json"}
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def trusted_llm_upstream_client(target_url: str, **kwargs) -> httpx.AsyncClient:
    """Route model traffic through its isolated, exact-authority gateway."""
    try:
        parsed = urlsplit(target_url)
    except ValueError as exc:
        raise SourceTransportConfigurationError("trusted-model-target-invalid") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise SourceTransportConfigurationError("trusted-model-target-invalid")
    # The model broker must never directly resolve or dial a private target.
    # The dedicated model egress gateway validates the configured authority,
    # resolves once, and dials the vetted numeric peer.
    proxy_url = model_egress_proxy_url()
    if not proxy_url:
        raise SourceTransportConfigurationError("model-egress-gateway-required")
    kwargs["follow_redirects"] = False
    if "transport" in kwargs or "mounts" in kwargs:
        raise SourceTransportConfigurationError("custom-model-transport-forbidden")
    kwargs["proxy"] = proxy_url
    kwargs["trust_env"] = False
    return httpx.AsyncClient(**kwargs)


def trusted_control_base_url(value: str, service: str) -> str:
    """Require fixed Compose control authorities in protected mode.

    This prevents source URLs or operator proxy settings from selecting the
    browser/Flare control authority. In the candidate composition these
    controls are reached through fixed permissioned Unix sockets; this URL
    validation remains compatibility-mode defense in depth.
    """
    if service not in _PROTECTED_CONTROL_BASES:
        raise SourceTransportConfigurationError("trusted-control-service-invalid")
    if not protected_source_mode():
        return value.rstrip("/")
    host, port, path = _PROTECTED_CONTROL_BASES[service]
    try:
        parsed = urlsplit(value)
        parsed_port = parsed.port
    except ValueError as exc:
        raise SourceTransportConfigurationError("trusted-control-url-invalid") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname != host
        or parsed_port != port
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path.rstrip("/") != path
        or parsed.query
        or parsed.fragment
    ):
        raise SourceTransportConfigurationError("trusted-control-url-invalid")
    return f"http://{host}:{port}{path}"


def require_unprotected_source_tool(tool_name: str) -> None:
    """Fail before dispatching a source fetch through an unqualified tool."""
    if protected_source_mode():
        raise ProtectedSourceToolUnavailableError(
            f"protected-source-tool-unavailable:{tool_name}"
        )
