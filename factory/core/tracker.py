"""The run's tasks: the agents append intents, the board folds them into tasks.json — nothing else writes a task."""

import json
import os
from collections.abc import Collection
from datetime import datetime
from pathlib import Path

from factory.state import INTENTS, KEYS, TASKS

PRIORITY = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


def write_intent(thread: str, intent: str, **fields) -> None:
    # what the agents' tools do in .pi/extensions/factory.ts; solo runs and tests do it from here
    line = {"at": datetime.now().astimezone().isoformat(), "thread": thread, "intent": intent, **fields}
    with INTENTS.open("a") as file:
        file.write(json.dumps(line, ensure_ascii=False) + "\n")


def allocate_key() -> str:
    # mkdir is atomic: the first number nobody has taken is the key, whoever asks
    n = len(os.listdir(KEYS)) + 1
    while True:
        try:
            (KEYS / str(n)).mkdir()
            return f"FAB-{n}"
        except FileExistsError:
            n += 1


class Tracker:
    """The tasks of the run and the rules an intent is applied by; the board reads and acts, the tools only read."""

    def __init__(self, tasks_file: Path = TASKS, intents_file: Path = INTENTS):
        self.tasks_file = tasks_file
        self.intents_file = intents_file
        self.tasks: dict[str, dict] = {}
        self.folded = 0  # intents already applied; the rest of the file is new
        self.strays: list[dict] = []  # intents of threads the caller did not name; the board logs and clears them

    def fold(self, known: Collection[str] | None = None) -> list[dict]:
        # apply the intents appended since the last fold, in order; returns those that changed a task.
        # with `known`, an intent from any other thread is a stray (an agent of an earlier run) and lands in
        # self.strays instead
        applied = []
        for line in self.intents_file.read_text().splitlines()[self.folded:]:
            try:
                intent = json.loads(line)
            except json.JSONDecodeError:
                break  # an agent is still writing this line; next tick
            self.folded += 1
            if known is not None and intent["thread"] not in known:
                self.strays.append(intent)
            elif self.apply(intent):
                applied.append(intent)
        return applied

    def apply(self, intent: dict) -> bool:
        # the rules: a task is created once, canceled or amended while open, reprioritized while waiting, handed off once
        kind, key = intent["intent"], intent["key"]
        task = self.tasks.get(key)
        if kind == "create":
            if task:
                return False
            self.tasks[key] = {"key": key, "type": intent["type"], "title": intent["title"],
                               "description": intent["description"], "priority": intent["priority"],
                               "blocked_by": intent.get("blocked_by") or [], "parent": intent.get("parent"),
                               "status": "todo", "thread": None, "handoffs": [], "amendments": [],
                               "created_by": intent["thread"]}
            return True
        if task is None:
            return False
        if kind == "cancel" and task["status"] in ("todo", "in_progress"):
            task["status"] = "canceled"
            return True
        if kind == "amend" and task["status"] in ("todo", "in_progress"):
            task.setdefault("amendments", []).append({field: intent[field] for field in ("at", "thread", "text")})
            return True
        if kind == "priority" and task["status"] == "todo":
            task["priority"] = intent["priority"]
            return True
        if kind == "handoff" and (task["status"] == "in_progress"
                                  or task["status"] == "canceled" and not task["handoffs"]):
            task["handoffs"].append({field: intent[field] for field in ("at", "thread", "outcome", "summary", "text")})
            if task["status"] == "in_progress":
                task["status"] = "done"  # a canceled task keeps its status: the board drops the work
            return True
        return False

    def start(self, key: str, thread: str) -> None:
        self.tasks[key].update(status="in_progress", thread=thread, started=datetime.now().astimezone().isoformat())

    def hand_back(self, key: str) -> None:
        # the work did not merge: the task is the worker's again, its next handoff counts
        self.tasks[key]["status"] = "in_progress"

    def copy(self, key: str, note: str) -> dict:
        # the board's own create: the same task again with the note on top, for whoever created the original.
        # the original is canceled — its work is not in the project — and whatever waited on it waits on the
        # copy; the copy waits on the code tasks in flight, so it starts on a settled project instead of
        # conflicting with them in turn
        original = self.tasks[key]
        original["status"] = "canceled"
        new_key = allocate_key()
        in_flight = [t["key"] for t in self.tasks.values() if t["status"] == "in_progress" and t["type"] == "code"]
        self.tasks[new_key] = {**original, "key": new_key, "description": f"{note}\n\n{original['description']}",
                               "blocked_by": in_flight, "status": "todo", "thread": None, "handoffs": []}
        for task in self.tasks.values():
            task["blocked_by"] = [new_key if k == key else k for k in task["blocked_by"]]
        return self.tasks[new_key]

    def ready(self) -> list[dict]:
        # todo tasks whose blockers are all done, urgent first
        todo = [t for t in self.tasks.values() if t["status"] == "todo"
                and all(self.tasks.get(k, {}).get("status") == "done" for k in t["blocked_by"])]
        return sorted(todo, key=lambda t: PRIORITY[t["priority"]])

    def floor(self, parent: str | None) -> list[dict]:
        # the planner's board is the top level, a lead's the sub-tasks of its epic
        return [t for t in self.tasks.values() if t["parent"] == parent]

    def save(self) -> None:
        # the whole file at once: a tool reading it never sees half a write
        draft = self.tasks_file.with_suffix(".tmp")
        draft.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=1))
        draft.replace(self.tasks_file)
