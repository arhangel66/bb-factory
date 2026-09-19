"""Serves the timeline page: factory/ui/ and state/events/ as static files, plus the list of runs."""

import json
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from factory.state import EVENTS, ROOT

PORT = 8877
STALE_SECONDS = 60  # a run rewrites its file every tick; one this quiet without a report is gone


def run_summary(history: Path) -> dict:
    # what the page lists a run by: when it started, its goal, how it ended and how many tasks it had
    events = [json.loads(line) for line in history.read_text().splitlines() if line]
    messages = [e for e in events if e["kind"] == "message"]
    goal = next((m["text"] for m in messages if m["agent"]["role"] == "human"), "")
    report = next((m["status"] for m in messages if m["agent"]["role"] == "planner" and m["status"]), None)
    planner_stopped = any(e["kind"] == "agent" and e["action"] == "stopped" and e["agent"]["role"] == "planner"
                          for e in events)
    if report:
        status = report  # green, yellow or red
    elif planner_stopped or time.time() - history.stat().st_mtime > STALE_SECONDS:
        status = "aborted"
    else:
        status = "live"
    return {"name": history.name, "started": events[0]["at"] if events else "", "goal": goal, "status": status,
            "tasks": len({e["key"] for e in events if e["kind"] == "task"})}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/factory/ui/timeline.html"  # the page lives at the root, its file name stays out of the bar
        if self.path == "/runs":
            runs = sorted(EVENTS.glob("*.jsonl"), key=lambda history: history.name, reverse=True)
            body = json.dumps([run_summary(history) for history in runs], ensure_ascii=False).encode()
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
    print(f"timeline at http://localhost:{port}/", flush=True)
    ThreadingHTTPServer(("localhost", port), Handler).serve_forever()


if __name__ == "__main__":
    serve(PORT)
