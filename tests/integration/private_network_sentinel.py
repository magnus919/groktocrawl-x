"""CI-only private-network sentinel; any application traffic is recorded."""

from __future__ import annotations

import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

EVENTS = Path(os.environ.get("SENTINEL_EVENTS", "/state/events.jsonl"))
POSITIVE_EVENTS = Path(
    os.environ.get("SENTINEL_POSITIVE_EVENTS", "/state/positive-control.jsonl")
)
POSITIVE_CONTROL_PREFIX = b"PRIVATE_SENTINEL_RESPONSE_V1:"

# Keep the negative event file separate and append-only. The independent
# positive control has its own retained file and can never clear a negative hit.
EVENTS.parent.mkdir(parents=True, exist_ok=True)
EVENTS.touch(exist_ok=True)
POSITIVE_EVENTS.touch(exist_ok=True)


def record(kind: str, peer: object, destination: Path = EVENTS) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"kind": kind, "peer": str(peer)}) + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _fmt: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        elif self.path.startswith("/positive-control/"):
            record("positive-control", self.client_address, POSITIVE_EVENTS)
        else:
            record("http", self.client_address)
        parts = urlsplit(self.path).path.split("/")
        nonce = parts[-1] if len(parts) == 3 else ""
        valid_nonce = re.fullmatch(r"[0-9a-f]{32}", nonce) is not None
        status = 200 if valid_nonce else 400
        body = POSITIVE_CONTROL_PREFIX + nonce.encode("ascii", errors="ignore") if valid_nonce else b"invalid nonce"
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def udp_sink() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 19002))
    while True:
        _data, peer = sock.recvfrom(4096)
        record("udp", peer)


threading.Thread(target=udp_sink, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 19001), Handler).serve_forever()
