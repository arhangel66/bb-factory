"""Serves the timeline page: factory/ui/ and state/runs/ as static files, plus the list of runs."""

import json
import subprocess
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from factory.state import ROOT, RUNS

PORT = 8877
STALE_SECONDS = 60  # a run rewrites its file every tick; one this quiet without a report is gone


def run_summary(history: Path) -> dict:
    # what the page lists a run by: when it started, its goal, how it ended and how many tasks it had,
    # plus where its project is and what the secretary told Mikhail last: the way to run the result
    events = [json.loads(line) for line in history.read_text().splitlines() if line]
    messages = [e for e in events if e["kind"] == "message"]
    goal = next((m["text"] for m in messages if m["agent"]["role"] == "human"), "")
    told = next((m["text"] for m in reversed(messages) if m["agent"]["role"] == "secretary" and m["key"] == "human"), None)
    run_file = history.parent / "run.json"
    workdir = json.loads(run_file.read_text()).get("workdir") if run_file.exists() else None
    report = next((m["status"] for m in messages if m["agent"]["role"] == "planner" and m["status"]), None)
    planner_stopped = any(e["kind"] == "agent" and e["action"] == "stopped" and e["agent"]["role"] == "planner"
                          for e in events)
    if report:
        status = report  # green, yellow or red
    elif planner_stopped or time.time() - history.stat().st_mtime > STALE_SECONDS:
        status = "aborted"
    else:
        status = "live"
    return {"name": history.parent.name, "started": events[0]["at"] if events else "", "goal": goal, "status": status,
            "tasks": len({e["key"] for e in events if e["kind"] == "task"}), "workdir": workdir, "report": told}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/factory/ui/timeline.html"  # the page lives at the root, its file name stays out of the bar
        if self.path == "/runs":
            # a solo run (factory/core/solo.py) has a directory but no events: nothing to replay
            runs = sorted((h for h in RUNS.glob("*/events.jsonl") if h.stat().st_size),
                          key=lambda history: history.parent.name, reverse=True)
            body = json.dumps([run_summary(history) for history in runs], ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/open/"):
            # the project of a run in Finder; the page is local, so is the folder
            run_file = RUNS / Path(self.path).name / "run.json"
            subprocess.run(["open", json.loads(run_file.read_text())["workdir"]])
            self.send_response(204)
            self.end_headers()
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
