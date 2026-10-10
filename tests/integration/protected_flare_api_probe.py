"""Local fixture-only end-to-end smoke test for the protected Flare profile."""

from __future__ import annotations

import json
import uuid

import httpx

BASE_URL = "http://candidate-flare-control:8191"
CONTROL_SOCKET = "/run/flare-control/control.sock"
FIXTURE_URL = "http://flare-origin.test/get"
_client = httpx.Client(
    transport=httpx.HTTPTransport(uds=CONTROL_SOCKET, retries=0),
    base_url=BASE_URL,
    trust_env=False,
    timeout=90.0,
)


def call(body: dict, *, expected_http_status: int = 200) -> dict:
    response = _client.post(
        "/v1",
        content=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_http_status, response.status_code
    return response.json()


session = f"protected-flare-ci-{uuid.uuid4()}"
created = call(
    {
        "cmd": "sessions.create",
        "session": session,
        "proxy": {"url": "http://127.0.0.1:8191"},
    }
)
assert created.get("status") == "ok", created

try:
    listed = call({"cmd": "sessions.list"})
    assert session in listed.get("sessions", []), listed

    got = call(
        {
            "cmd": "request.get",
            "url": FIXTURE_URL,
            "session": session,
            # This would fail to connect if the caller proxy were honored.
            "proxy": {"url": "http://127.0.0.1:8191"},
            "cookies": [{"name": "probe", "value": "cookie-ok"}],
            "returnScreenshot": True,
            "waitInSeconds": 2,
        }
    )
    get_solution = got.get("solution") or {}
    page = get_solution.get("response", "")
    assert got.get("status") == "ok", got
    assert get_solution.get("status") == 200, got
    assert "FLARE_GET_OK" in page, got
    assert "COOKIE:probe=cookie-ok" in page, got
    assert "CONTROL_API_BLOCKED" in page, got
    assert "PRIVATE_TARGET_BLOCKED" in page, got
    assert get_solution.get("screenshot"), "screenshot capture was not preserved"

    redirected = call(
        {
            "cmd": "request.get",
            "url": "http://flare-origin.test/redirect",
            "session": session,
            "waitInSeconds": 1,
        }
    )
    assert redirected.get("status") == "ok", redirected
    assert "FLARE_GET_OK" in (redirected.get("solution") or {}).get("response", "")

    posted = call(
        {
            "cmd": "request.post",
            "url": "http://flare-origin.test/post",
            "postData": "capture=posted",
            "session": session,
            "proxy": {"url": "http://127.0.0.1:8191"},
        }
    )
    assert posted.get("status") == "ok", posted
    assert "FLARE_POST_OK:capture=posted" in (posted.get("solution") or {}).get("response", "")

    rejected = call({"cmd": "request.get", "url": "file:///etc/passwd"}, expected_http_status=500)
    assert rejected == {"error": "request URL is not an allowed HTTP destination"}, rejected
finally:
    destroyed = call({"cmd": "sessions.destroy", "session": session})
    assert destroyed.get("status") == "ok", destroyed
    _client.close()
