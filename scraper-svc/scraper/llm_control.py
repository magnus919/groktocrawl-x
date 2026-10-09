"""Fixed-target chat-completion broker for the isolated scraper."""

from __future__ import annotations

import os
import stat
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .source_http import trusted_llm_upstream_client

MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
_KINDS = {"recovery": ("LLM_BASE_URL", "LLM_API_KEY"), "captcha": ("CAPTCHA_VISION_BASE_URL", "CAPTCHA_VISION_API_KEY")}


def _target(kind: str) -> tuple[str, str | None]:
    if kind not in _KINDS:
        raise ValueError("unknown trusted model route")
    base_name, key_name = _KINDS[kind]
    base = os.environ.get(base_name, "").rstrip("/")
    if not base:
        raise ValueError("trusted model route is not configured")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("invalid trusted model route")
    return f"{base}/chat/completions", os.environ.get(key_name) or None


@asynccontextmanager
async def lifespan(app: FastAPI):
    socket_path = Path(os.environ.get("MODEL_CONTROL_SOCKET", "/run/scraper-llm/control.sock"))
    try:
        socket_stat = socket_path.lstat()
    except OSError as exc:
        raise RuntimeError("model control socket is unavailable") from exc
    if (
        not stat.S_ISSOCK(socket_stat.st_mode)
        or socket_stat.st_uid != os.getuid()
        or socket_stat.st_gid != 20000
        or stat.S_IMODE(socket_stat.st_mode) != 0o660
    ):
        raise RuntimeError("model control socket permissions are invalid")
    app.state.clients = {}
    for kind, _ in _KINDS.items():
        try:
            target_url, _ = _target(kind)
        except ValueError:
            continue
        client = trusted_llm_upstream_client(target_url, trust_env=False)
        app.state.clients[kind] = client
    try:
        yield
    finally:
        for client in app.state.clients.values():
            await client.aclose()


app = FastAPI(title="Trusted model control", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "routes": sorted(app.state.clients)}


@app.post("/{kind}/chat/completions")
async def forward(kind: str, request: Request):
    if kind not in _KINDS or request.url.query or request.headers.get("content-encoding"):
        return JSONResponse({"detail": "not found"}, status_code=404)
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return JSONResponse({"detail": "application/json required"}, status_code=415)
    declared = request.headers.get("content-length")
    if declared and (not declared.isdecimal() or int(declared) > MAX_REQUEST_BYTES):
        return JSONResponse({"detail": "request too large"}, status_code=413)
    body_buffer = bytearray()
    async for chunk in request.stream():
        if len(body_buffer) + len(chunk) > MAX_REQUEST_BYTES:
            return JSONResponse({"detail": "request too large"}, status_code=413)
        body_buffer.extend(chunk)
    body = bytes(body_buffer)
    if not body:
        return JSONResponse({"detail": "request body required"}, status_code=400)
    try:
        target_url, api_key = _target(kind)
    except ValueError:
        return JSONResponse({"detail": "trusted model unavailable"}, status_code=503)
    client = app.state.clients.get(kind)
    if client is None:
        return JSONResponse({"detail": "trusted model unavailable"}, status_code=503)
    headers = {"content-type": "application/json", "accept": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    try:
        upstream_request = client.build_request(
            "POST", target_url, content=body, headers=headers, timeout=120
        )
        upstream = await client.send(upstream_request, stream=True)
    except httpx.HTTPError:
        return JSONResponse({"detail": "trusted model unavailable"}, status_code=503)
    response_body = bytearray()
    try:
        async for chunk in upstream.aiter_raw():
            if len(response_body) + len(chunk) > MAX_RESPONSE_BYTES:
                return JSONResponse({"detail": "trusted model response too large"}, status_code=502)
            response_body.extend(chunk)
    finally:
        await upstream.aclose()
    return Response(
        content=bytes(response_body),
        status_code=upstream.status_code,
        headers={"content-type": upstream.headers.get("content-type", "application/json")},
    )
