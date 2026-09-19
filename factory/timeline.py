"""The history of the current run as JSON lines, one event per line: tasks, messages, agents."""

import json
import re
from datetime import datetime

from factory.bb import Tasks, Threads, run_info
from factory.board import messages
from factory.roles import ROLE_BY_LABEL, Role

COLOR = {"ok": "green", "warning": "yellow", "failed": "red"}


def local(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000).astimezone()


def event(at: datetime, agent: dict, kind: str, action: str, key: str, text: str = "", status: str | None = None,
          type: str | None = None, parent: str | None = None) -> dict:
    return {"at": at.isoformat(), "agent": agent, "kind": kind, "action": action, "key": key, "type": type,
            "parent": parent, "text": text, "status": status}


def agent_of(title: str, thread: str, label_role: Role) -> dict:
    # a thread title is "<prompt> [<task>] <model>"; the imitator's role is whatever its current task needs
    words = title.split(" ")
    imitator = words[0] == Role.imitator
    return {"role": label_role if imitator else words[0], "model": words[-1], "imitator": imitator, "thread": thread}


def type_of(shown: dict) -> str | None:
    return shown["labels"][0]["name"] if shown["labels"] else None


def role_of(shown: dict) -> Role:
    return ROLE_BY_LABEL.get(type_of(shown), Role.planner)


def events(tasks: Tasks, threads: Threads) -> list[dict]:
    # tasks: bb's system comments ("Status changed to X by agent (thr_…)", "by cli" when the board did it) and handoff comments
    # ("handoff (ok|warning|failed): <summary>"; the Done change right after a handoff is implied by it)
    out = [event(datetime.fromisoformat(m["at"]).astimezone(), {"role": m["from"], "model": None, "imitator": False, "thread": None},
                 "message", "sent", m["to"], m["text"], m["status"]) for m in messages()]
    shown_by_key = {t["key"]: tasks.show(t["key"]) for t in tasks.all()}
    key_by_id = {s["task"]["id"]: k for k, s in shown_by_key.items()}
    titles = {t["threadId"]: t["title"] for s in shown_by_key.values() for t in s["taskThreads"]}

    def title_of(thread: str) -> str:
        # a thread can comment on a task without being attached to one: the planner, a lead, a leftover of a previous run
        if thread not in titles:
            titles[thread] = threads.show(thread)["title"]
        return titles[thread]

    title_of(run_info()["planner"])
    for shown in shown_by_key.values():
        task, role, type = shown["task"], role_of(shown), type_of(shown)
        parent = key_by_id.get(task["parentTaskId"])
        first = True
        for c in shown["comments"]:
            at = datetime.fromisoformat(c["createdAt"]).astimezone()
            handoff = re.match(r"handoff \((\w+)\): (.*)", c["body"])
            changed = re.match(r"Status changed to (.+?) by (?:agent \((thr_\w+)\)|cli)", c["body"])
            if handoff:
                agent = agent_of(title_of(c["threadId"]), c["threadId"], role)
                out.append(event(at, agent, "task", "handed_off", task["key"], handoff.group(2), COLOR[handoff.group(1)], type, parent))
            elif changed and changed.group(1) == "In Progress":
                # the board sets the status and attaches the agent's thread right after, so the nearest attachment is that agent;
                # an agent that takes a task itself attaches nothing and is named in the comment
                near = min(shown["taskThreads"], default=None,
                           key=lambda t: abs(datetime.fromisoformat(t["attachedAt"]).astimezone() - at))
                thread = near["threadId"] if near else changed.group(2)
                if thread:
                    agent = agent_of(title_of(thread), thread, role)
                    out.append(event(at, agent, "task", "started", task["key"], type=type, parent=parent))
            elif changed and changed.group(1) in ("Todo", "Canceled") and changed.group(2):  # the board's own reopen has no agent
                agent = agent_of(title_of(changed.group(2)), changed.group(2), Role.planner)
                action = "canceled" if changed.group(1) == "Canceled" else "created" if first else "reopened"
                text, status = (task["title"], None) if first else ("", "yellow" if action == "reopened" else None)
                out.append(event(at, agent, "task", action, task["key"], text, status, type, parent))
                first = False
    for thread, thread_title in list(titles.items()):
        shown = threads.show(thread)
        first_task = next((s for s in shown_by_key.values() if any(t["threadId"] == thread for t in s["taskThreads"])), None)
        agent = agent_of(thread_title, thread, role_of(first_task) if first_task else Role.planner)
        out.append(event(local(shown["createdAt"]), agent, "agent", "started", thread))
        if shown["archivedAt"]:
            out.append(event(local(shown["archivedAt"]), agent, "agent", "stopped", thread))
    return sorted(out, key=lambda e: e["at"])


if __name__ == "__main__":
    for e in events(Tasks(), Threads()):
        print(json.dumps(e, ensure_ascii=False))
