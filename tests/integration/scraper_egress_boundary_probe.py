"""Run inside candidate-scraper to test denied direct and allowed brokered traffic."""

from __future__ import annotations

import asyncio
import ctypes
import hashlib
import json
import os
import socket
import stat
import sys
from contextlib import suppress
from uuid import uuid4

import httpx
from scraper.source_http import source_httpx_client
from scraper.valkey_control import RESERVE_SLOT_SCRIPT, ValkeyControlClient

PRIVATE_IP = "172.31.253.250"
CAPTURE_PEER_IP = "172.31.254.6"
CAPTURE_HOST_GATEWAY_IP = "172.31.254.1"
MODEL_GATEWAY_IP = "172.31.254.34"
FIXTURE_URL = "http://flare-origin.test/get"
STATE_SOCKET = "/run/scraper-state/control.sock"


def _direct_tcp_denied(host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.5)
    try:
        try:
            sock.connect((host, port))
        except OSError:
            return
        raise RuntimeError(f"direct TCP unexpectedly reached {host}:{port}")
    finally:
        sock.close()


def _assert_process_identity(pid: int, uid: int, gid: int) -> None:
    fields = {}
    with open(f"/proc/{pid}/status", encoding="ascii") as stream:
        for line in stream:
            if line.startswith(("Uid:", "Gid:", "CapEff:", "CapPrm:", "CapBnd:", "NoNewPrivs:")):
                name, value = line.split(":", 1)
                fields[name] = value.split()
    if [int(value) for value in fields.get("Uid", [])] != [uid] * 4:
        raise RuntimeError("protected scraper process has an unexpected UID")
    if [int(value) for value in fields.get("Gid", [])] != [gid] * 4:
        raise RuntimeError("protected scraper process has an unexpected GID")
    if any(int(fields.get(name, ["-1"])[0], 16) != 0 for name in ("CapEff", "CapPrm", "CapBnd")):
        raise RuntimeError("protected scraper process retained bootstrap capabilities")
    if fields.get("NoNewPrivs") != ["1"]:
        raise RuntimeError("protected scraper process lacks no-new-privileges")


def _drop_probe_capabilities() -> None:
    class Header(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]

    class Data(ctypes.Structure):
        _fields_ = [
            ("effective", ctypes.c_uint32),
            ("permitted", ctypes.c_uint32),
            ("inheritable", ctypes.c_uint32),
        ]

    header = Header(0x20080522, 0)
    data = (Data * 2)()
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.capset(ctypes.byref(header), ctypes.byref(data)) != 0:
        raise RuntimeError("boundary probe could not drop its own capabilities")


def _protected_worker_pid() -> int:
    matches = []
    for entry in os.scandir("/proc"):
        if not entry.name.isdecimal():
            continue
        try:
            with open(f"/proc/{entry.name}/cmdline", "rb") as stream:
                command = stream.read(4096)
        except OSError:
            continue
        if command.split(b"\x00") == [
            os.fsencode(sys.executable), b"-m", b"scraper.capture_firewall", b""
        ]:
            matches.append(int(entry.name))
    if len(matches) != 1:
        raise RuntimeError("unique protected scraper worker process was not found")
    return matches[0]


def _assert_control_socket_permissions() -> None:
    bindings = (
        ("/run/scraper/app.sock", 10001),
        ("/run/scraper-state/control.sock", 10002),
        ("/run/scraper-llm/control.sock", 10002),
        ("/run/browser-control/controller.sock", 0),
        ("/run/flare-control/control.sock", 10003),
    )
    for path, owner_uid in bindings:
        info = os.lstat(path)
        parent = os.lstat(os.path.dirname(path))
        if (
            not stat.S_ISSOCK(info.st_mode)
            or info.st_uid != owner_uid
            or info.st_gid != 20000
            or stat.S_IMODE(info.st_mode) != 0o660
            or not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != owner_uid
            or parent.st_gid != 20000
            or stat.S_IMODE(parent.st_mode) != 0o2710
        ):
            raise RuntimeError(
                "control socket permissions invalid: "
                f"path={path} owner={info.st_uid}:{info.st_gid} "
                f"mode={stat.S_IMODE(info.st_mode):04o}; "
                f"parent={os.path.dirname(path)} "
                f"owner={parent.st_uid}:{parent.st_gid} "
                f"mode={stat.S_IMODE(parent.st_mode):04o}; "
                f"expected socket={owner_uid}:20000/0660 "
                f"directory={owner_uid}:20000/2710"
            )


async def _raw_state_rpc(request: dict) -> dict:
    body = json.dumps(request, separators=(",", ":")).encode()
    if len(body) > 4096:
        raise RuntimeError("state RPC probe request exceeded its bound")
    reader, writer = await asyncio.wait_for(
        asyncio.open_unix_connection(STATE_SOCKET), timeout=2
    )
    try:
        writer.write(body + b"\n")
        await asyncio.wait_for(writer.drain(), timeout=2)
        line = await asyncio.wait_for(reader.readline(), timeout=5)
        if not line or len(line) > 4096 or not line.endswith(b"\n"):
            raise RuntimeError("state RPC probe response exceeded its bound")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("state RPC returned a non-object response")
        return value
    finally:
        writer.close()
        with suppress(OSError, TimeoutError):
            await asyncio.wait_for(writer.wait_closed(), timeout=1)


async def _exercise_valkey_capability() -> None:
    token = hashlib.sha256(uuid4().bytes).hexdigest()
    client = ValkeyControlClient(STATE_SOCKET)
    if not await client.ping():
        raise RuntimeError("Valkey RPC ping failed")

    keys = {
        "cache": f"scrape_cache:{token}",
        "robots": f"politeness:robots:{token}",
        "rate": f"politeness:rate:{token}",
        "clearance": f"cf:clearance:probe-{token[:16]}.fixture.test",
    }
    for namespace, key in keys.items():
        value = f"rpc-probe:{namespace}:{token}"
        await client.setex(key, 60, value)
        if await client.get(key) != value:
            raise RuntimeError(f"Valkey RPC round-trip failed for {namespace}")

    wait_ms = await client.eval(
        RESERVE_SLOT_SCRIPT,
        1,
        f"politeness:rate:{token}:slots",
        0,
        30000,
    )
    if not 0 <= wait_ms <= 30000:
        raise RuntimeError("Valkey reservation script returned an invalid wait")

    denied_key = await _raw_state_rpc(
        {"operation": "get", "key": f"admin:probe:{token}"}
    )
    denied_operation = await _raw_state_rpc({"operation": "flushall"})
    if denied_key.get("ok") is not False or denied_operation.get("ok") is not False:
        raise RuntimeError("Valkey RPC accepted an unapproved key or operation")
    await client.aclose()


async def main() -> None:
    _drop_probe_capabilities()
    if (os.getuid(), os.getgid()) != (10001, 20000) or 20000 not in os.getgroups():
        raise RuntimeError("scraper did not run as the designated unprivileged identity")
    _assert_process_identity(_protected_worker_pid(), 10001, 20000)
    _assert_process_identity(1, 10001, 20000)
    _assert_control_socket_permissions()
    _direct_tcp_denied(PRIVATE_IP, 19001)
    _direct_tcp_denied(CAPTURE_PEER_IP, 19001)
    _direct_tcp_denied(CAPTURE_HOST_GATEWAY_IP, 19001)
    _direct_tcp_denied("1.1.1.1", 80)
    _direct_tcp_denied(MODEL_GATEWAY_IP, 8080)
    for target in (PRIVATE_IP, CAPTURE_PEER_IP, CAPTURE_HOST_GATEWAY_IP):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            with suppress(OSError):
                udp.sendto(b"private-egress-probe", (target, 19002))
        finally:
            udp.close()

    async with source_httpx_client(timeout=15) as client:
        response = await client.get(FIXTURE_URL)
    response.raise_for_status()
    if "FLARE_GET_OK" not in response.text:
        raise RuntimeError("source request did not traverse the capture gateway")

    await _exercise_valkey_capability()

    # Exercise the private operator model through its fixed UDS broker. The
    # scraper has no model URL/key and is not attached to candidate_private.
    model_transport = httpx.AsyncHTTPTransport(
        uds="/run/scraper-llm/control.sock", retries=0
    )
    async with httpx.AsyncClient(
        transport=model_transport, base_url="http://llm-control", trust_env=False
    ) as model:
        completion = await model.post(
            "/recovery/chat/completions",
            headers={"content-type": "application/json"},
            json={
                "model": "fixture-model",
                "messages": [{"role": "user", "content": "transport probe"}],
            },
        )
        if completion.status_code != 200:
            payload = completion.json() if completion.headers.get("content-type", "").startswith("application/json") else {}
            error_code = payload.get("error_code") if isinstance(payload, dict) else None
            if error_code not in {
                "configuration_unavailable",
                "client_unavailable",
                "upstream_transport_unavailable",
                "upstream_response_unavailable",
            }:
                error_code = "unknown"
            raise RuntimeError(
                f"private model broker failed status={completion.status_code} error_code={error_code}"
            )
        if not completion.json().get("choices"):
            raise RuntimeError("private model broker returned no completion")

    api = "http://candidate-browser-controller:8012"
    transport = httpx.AsyncHTTPTransport(
        uds="/run/browser-control/controller.sock", retries=0
    )
    async with httpx.AsyncClient(
        transport=transport, base_url=api, trust_env=False, timeout=45
    ) as browser:
        created = await browser.post("/browsers", json={"ttl": 60})
        created.raise_for_status()
        session_id = created.json()["id"]
        try:
            navigation = await browser.post(
                f"/browsers/{session_id}/execute",
                json={"action": "navigate", "url": FIXTURE_URL, "timeout": 30000},
            )
            navigation.raise_for_status()
            script = await browser.post(
                f"/browsers/{session_id}/execute",
                json={
                    "action": "executeScript",
                    "script": (
                        "async () => { const end = Date.now() + 5000; "
                        "while (document.querySelector('#private-check')?.textContent "
                        "=== 'pending' && Date.now() < end) "
                        "await new Promise(resolve => setTimeout(resolve, 50)); "
                        "return document.body.innerText; }"
                    ),
                },
            )
            script.raise_for_status()
            text = script.json().get("result", {}).get("script_result", "")
            if "PRIVATE_TARGET_BLOCKED" not in text:
                raise RuntimeError("browser renderer reached private sentinel")
        finally:
            await browser.delete(f"/browsers/{session_id}")

    print("scraper_capture_boundary=pass")


if __name__ == "__main__":
    asyncio.run(main())
