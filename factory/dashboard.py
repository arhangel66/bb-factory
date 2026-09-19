"""Serves the board page: dashboard/ and state/events/ as static files, plus the list of runs."""

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from factory.bb import EVENTS, ROOT

PORT = 8877


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/dashboard/board.dc.html")
            self.end_headers()
        elif self.path == "/runs":
            body = json.dumps(sorted((p.name for p in EVENTS.glob("*.jsonl")), reverse=True)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")  # the current run rewrites its file every tick
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass  # the page polls every few seconds


def serve(port: int) -> None:
    print(f"board at http://localhost:{port}/", flush=True)
    ThreadingHTTPServer(("localhost", port), Handler).serve_forever()


if __name__ == "__main__":
    serve(PORT)
