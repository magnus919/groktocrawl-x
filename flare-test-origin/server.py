"""Local-only origin fixture for protected FlareSolverr integration tests."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://flare-origin.test/get")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path not in {"/", "/get"}:
            self.send_error(404)
            return
        cookie = self.headers.get("Cookie", "")
        body = f"""<!doctype html>
<html><head><title>Protected Flare Fixture</title></head><body>
<p>FLARE_GET_OK</p><p>COOKIE:{cookie}</p><p id="api-check">pending</p>
<script>
fetch('http://127.0.0.1:8191/health', {{mode:'no-cors'}})
  .then(() => document.getElementById('api-check').textContent='CONTROL_API_REACHABLE')
  .catch(() => document.getElementById('api-check').textContent='CONTROL_API_BLOCKED');
</script>
</body></html>""".encode()
        self._send(200, "text/html; charset=utf-8", body)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        fields = parse_qs(body, keep_blank_values=True)
        marker = "&".join(f"{key}={value[0]}" for key, value in sorted(fields.items()))
        response = f"<!doctype html><html><head><title>Flare POST</title></head><body>FLARE_POST_OK:{marker}</body></html>".encode()
        self._send(200, "text/html; charset=utf-8", response)

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("0.0.0.0", 80), FixtureHandler).serve_forever()
