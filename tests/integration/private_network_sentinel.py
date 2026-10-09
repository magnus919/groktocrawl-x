"""CI-only private-network sentinel; any application traffic is recorded."""

from __future__ import annotations

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EVENTS = Path(os.environ.get("SENTINEL_EVENTS", "/state/events.jsonl"))


def record(kind: str, peer: object) -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"kind": kind, "peer": str(peer)}) + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _fmt: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            body = b"ok"
        else:
            record("http", self.client_address)
            body = b"sentinel"
        self.send_response(200)
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
