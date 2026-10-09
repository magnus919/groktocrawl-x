"""Verify there is no TCP API listener in the isolated Flare network namespace."""

from __future__ import annotations

import socket
from pathlib import Path


def validate_process_status(status: dict[str, str]) -> None:
    for field in ("CapEff", "CapPrm", "CapBnd", "CapAmb"):
        if int(status.get(field, "-1"), 16) != 0:
            raise RuntimeError(f"Flare process retained capability field {field}")
    if status.get("NoNewPrivs") != "1":
        raise RuntimeError("Flare process permits privilege escalation")


def _status_for_flare_process() -> dict[str, str]:
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            command = (entry / "cmdline").read_bytes()
            if b"/app/flaresolverr.py" not in command:
                continue
            rows = (entry / "status").read_text(encoding="ascii").splitlines()
        except (OSError, UnicodeError):
            continue
        return {key: value.strip() for row in rows if ":" in row for key, value in [row.split(":", 1)]}
    raise RuntimeError("Flare process status was not found")


def main() -> None:
    validate_process_status(_status_for_flare_process())

    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            rows = Path(table).read_text(encoding="ascii").splitlines()[1:]
        except FileNotFoundError:
            continue
        for row in rows:
            local = row.split()[1]
            port = int(local.rsplit(":", 1)[1], 16)
            state = row.split()[3]
            assert not (port == 8191 and state == "0A"), "Flare API is reachable over TCP"

    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        client = socket.socket(family, socket.SOCK_STREAM)
        client.settimeout(1)
        try:
            try:
                target = (host, 8191) if family == socket.AF_INET else (host, 8191, 0, 0)
                client.connect(target)
            except OSError:
                pass
            else:
                raise AssertionError("Flare API accepted a loopback TCP connection")
        finally:
            client.close()


if __name__ == "__main__":
    main()
