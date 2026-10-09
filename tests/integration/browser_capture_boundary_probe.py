"""Hostile-navigation probe to run inside candidate-browser-controller.

The script uses only the local browser API and data URLs. It makes no public
network requests and fails unless the renderer can render a local fixture while
unable to reach the controller over loopback or the Compose service name.
"""

from __future__ import annotations

import httpx

API = "http://127.0.0.1:8012"
BLOCKED_TARGETS = (
    "http://127.0.0.1:8012/health",
    "http://candidate-browser-controller:8012/health",
)


def main() -> None:
    with httpx.Client(base_url=API, trust_env=False, timeout=45.0) as client:
        created = client.post("/browsers", json={"ttl": 60})
        created.raise_for_status()
        session_id = created.json()["id"]
        try:
            local = client.post(
                f"/browsers/{session_id}/execute",
                json={
                    "action": "navigate",
                    "url": "data:text/html,%3Ctitle%3Elocal-fixture%3C/title%3E",
                },
            )
            local.raise_for_status()
            local_result = local.json()
            if not local_result.get("success") or local_result["result"].get(
                "title"
            ) != "local-fixture":
                raise RuntimeError("local browser fixture did not render")

            for target in BLOCKED_TARGETS:
                attempted = client.post(
                    f"/browsers/{session_id}/execute",
                    json={"action": "navigate", "url": target},
                )
                attempted.raise_for_status()
                if attempted.json().get("success") is not False:
                    raise RuntimeError("renderer reached its controller API")
        finally:
            client.delete(f"/browsers/{session_id}")
    print("protected_browser_boundary=pass")


if __name__ == "__main__":
    main()
