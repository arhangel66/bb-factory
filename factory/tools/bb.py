"""A thin wrapper over the bb CLI: the agent threads (bb thread)."""

import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from factory.roles import Model, Thinking

BB_PROJECT = "proj_x6sd774izb"
SECTION = "sec_62zku3gn5a"  # sidebar section "Factory · агенты" that holds every thread of a run
MAX_RETRIES = 3


def bb(*args: str, timeout: int = 60) -> dict:
    done = subprocess.run(["bb", *args, "--json"], capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        raise RuntimeError(f"bb {' '.join(args)}: {done.stderr.strip() or done.stdout.strip()}")
    return json.loads(done.stdout)


def usage_from_log(events: list[dict]) -> dict:
    # what a thread spent, from bb's event log: turns, items by type, the token total of its last usage report
    tokens = {}
    for e in events:
        if e["type"] == "thread/tokenUsage/updated":
            total = e["data"]["tokenUsage"]["total"]
            tokens = {"input": total["inputTokens"], "cached_input": total["cachedInputTokens"],
                      "output": total["outputTokens"], "reasoning": total["reasoningOutputTokens"],
                      "total": total["totalTokens"]}
    items = Counter(e["data"]["item"]["type"] for e in events if e["type"] == "item/completed")
    return {"turns": sum(e["type"] == "turn/completed" for e in events), "items": dict(items), "tokens": tokens}


class Threads:
    """Agent threads on bb's pi provider; a thread that hits a provider error is retried a few times."""

    def __init__(self):
        self.retries: dict[str, int] = {}

    def spawn(self, title: str, prompt: str, model: Model, thinking: Thinking, path: Path) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(prompt)
        thread = bb(
            "thread", "spawn", "--project", BB_PROJECT, "--environment", str(path),
            "--provider", "pi", "--model", model, "--reasoning-level", thinking, "--permission-mode", "full",
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

    def unarchive(self, thread: str) -> None:
        bb("thread", "unarchive", thread)

    def usage(self, thread: str) -> dict:
        return usage_from_log(bb("thread", "log", thread, "--all"))
