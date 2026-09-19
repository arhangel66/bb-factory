"""Thin wrappers over the bb CLI: the tracker (bb tasks) and the agent threads (bb thread)."""

import json
import subprocess
import tempfile
from pathlib import Path

PROJECT = "FAB"
BB_PROJECT = "proj_x6sd774izb"
SECTION = "sec_62zku3gn5a"  # sidebar section "Factory · агенты" that holds every thread of a run
MAX_RETRIES = 3
ROOT = Path(__file__).resolve().parent.parent  # paths below must not depend on the cwd
EVENTS = ROOT / "state/events"  # one <started>-<first task>.jsonl per run, rewritten every tick
RUN_FILE = ROOT / "state/run.json"  # {"number": first task number of the run, "planner": its thread}


def bb(*args: str, timeout: int = 60) -> dict:
    done = subprocess.run(["bb", *args, "--json"], capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        raise RuntimeError(f"bb {' '.join(args)}: {done.stderr.strip() or done.stdout.strip()}")
    return json.loads(done.stdout)


def run_info() -> dict:
    return json.loads(RUN_FILE.read_text())


class Tasks:
    """Tasks of the current run: everything numbered from the run's start."""

    def next_number(self) -> int:
        return bb("tasks", "project", "show", PROJECT)["project"]["nextTaskNumber"]

    def all(self) -> list[dict]:
        start = run_info()["number"]
        return [t for t in bb("tasks", "list", "--project", PROJECT)["tasks"] if t["number"] >= start]

    def show(self, key: str) -> dict:
        return bb("tasks", "show", key)  # task, labels, comments, taskThreads, ...

    def handoffs(self, key: str) -> list[dict]:
        return [c for c in self.show(key)["comments"] if c["body"].startswith("handoff")]

    def set_status(self, key: str, status: str) -> None:
        bb("tasks", "update", key, "--status", status)

    def attach(self, key: str, thread: str) -> None:
        bb("tasks", "attach", key, "--thread", thread)

    def reopen(self, key: str, note: str) -> None:
        description = (self.show(key)["task"]["description"] or "").strip()
        bb("tasks", "update", key, "--status", "todo", "--description", f"{description}\n\n{note}")


class Threads:
    """Agent threads on bb's pi provider; a thread that hits a provider error is retried a few times."""

    def __init__(self):
        self.retries: dict[str, int] = {}

    def spawn(self, title: str, prompt: str, model: str, path: Path) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(prompt)
        thread = bb(
            "thread", "spawn", "--project", BB_PROJECT, "--environment", str(path),
            "--provider", "pi", "--model", model, "--permission-mode", "full",
            "--section", SECTION, "--title", title, "--prompt-file", f.name,
        )
        return thread["id"]

    def tell(self, thread: str, text: str) -> None:
        bb("thread", "tell", thread, text, "--mode", "queue")

    def show(self, thread: str) -> dict:
        return bb("thread", "show", thread)["thread"]  # status, title, createdAt, archivedAt (ms), ...

    def status(self, thread: str) -> str:
        return self.show(thread)["status"]

    def alive(self, thread: str) -> bool:
        # retried on "error" (usually "fetch failed" from the provider) until the budget runs out
        if self.status(thread) != "error":
            return True
        self.retries[thread] = self.retries.get(thread, 0) + 1
        if self.retries[thread] > MAX_RETRIES:
            return False
        bb("thread", "retry", thread)
        return True

    def archive(self, thread: str) -> None:
        bb("thread", "archive", thread)
