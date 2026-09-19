"""The timeline of a run, appended by the board as things happen; the form is docs/examples/events.jsonl."""

import json
from datetime import datetime

from factory.state import EVENTS


def agent(role: str, model: str | None = None, thread: str | None = None, imitator: bool = False) -> dict:
    return {"role": role, "model": model, "imitator": imitator, "thread": thread}


HUMAN = agent("human")


def emit(agent: dict, kind: str, action: str, key: str, text: str = "", status: str | None = None,
         type: str | None = None, parent: str | None = None) -> None:
    line = {"at": datetime.now().astimezone().isoformat(), "agent": agent, "kind": kind, "action": action,
            "key": key, "type": type, "parent": parent, "text": text, "status": status}
    with EVENTS.open("a") as file:
        file.write(json.dumps(line, ensure_ascii=False) + "\n")
