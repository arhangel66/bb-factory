"""The board: the planner puts tasks on it, it hands them to agents and brings the handoffs back."""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from factory.core.workspace import Workspace
from factory.roles import ROLE_BY_LABEL, AgentConfig, Config, Role, prompt, save_tools_by_role
from factory.state import MESSAGES, RUN_FILE
from factory.tools.bb import Tasks, Threads
from factory.tools.messages import messages, write_message
from factory.tools.telegram import Telegram

TICK = timedelta(seconds=10)
HEARTBEAT = timedelta(minutes=5)
PRIORITY = {"urgent": 0, "high": 1, "medium": 2, "low": 3, "none": 4}


def log(event: str) -> None:
    print(f"{datetime.now():%H:%M:%S}  {event}", flush=True)


def blocked_by(task: dict) -> list[str]:
    found = re.search(r"blocked-by: (.+)", task.get("description") or "")
    keys = [k.strip() for k in found.group(1).split(",")] if found else []
    return [k for k in keys if k.lower() != "none"]


def board_lines(tasks: list[dict]) -> str:
    return "\n".join(
        f"{t['key']}  {t['status']}  {t['priority']}  {','.join(t['labels'])}  {t['title']}" for t in tasks
    ) or "board is empty"


class Board:
    def __init__(self, config: Config, tasks: Tasks, threads: Threads, workspace: Workspace, telegram: Telegram,
                 slots: int = 2):
        self.config = config
        self.tasks = tasks
        self.threads = threads
        self.workspace = workspace
        self.telegram = telegram
        self.slots = slots  # per-task threads running at once
        self.planner = ""
        self.secretary = ""
        self.leads: dict[str, str] = {}  # epic key -> its lead's thread
        self.shared: dict[AgentConfig, str] = {}  # shared agent -> its thread
        self.forwarded: set[str] = set()  # ponytail: in-memory; persist when the loop must survive restarts
        self.relayed = 0  # messages already delivered; the rest of the file is the postman's queue
        self.waiting: datetime | None = None  # when the answer the secretary is waiting for stops being worth it
        self.last_wake = datetime.now()

    def start(self, goal: str) -> None:
        # the goal is a message to the planner; the run is every task numbered from here on
        self.workspace.prepare()
        save_tools_by_role()
        number = self.tasks.next_number()
        MESSAGES.write_text("")
        write_message("human", Role.planner, goal)
        self.relayed = 1  # the goal is in the planner's prompt, it is not delivered twice
        planner, secretary = self.config[Role.planner], self.config[Role.secretary]
        self.planner = self.threads.spawn(f"{planner.prompt} {planner.model}", prompt(planner.prompt, goal=goal),
                                          planner.model, planner.thinking, self.workspace.agent_dir(Role.planner))
        # the secretary starts with the planner: every run ends with a report for it to pass on
        self.secretary = self.shared[secretary] = self.threads.spawn(
            f"{secretary.prompt} {secretary.model}", prompt(secretary.prompt), secretary.model, secretary.thinking,
            self.workspace.agent_dir(Role.planner))
        RUN_FILE.write_text(json.dumps({"number": number, "planner": self.planner}))
        log(f"goal «{goal}» → planner {self.planner}, secretary {self.secretary}, tasks from {number}")

    def wake(self, thread: str, event: str, floor: list[dict]) -> None:
        self.threads.tell(thread, prompt("wake", event=event, board=board_lines(floor)))
        if thread == self.planner:
            self.last_wake = datetime.now()

    def forward_handoffs(self, tasks: list[dict]) -> None:
        # a handoff closes its task and wakes whoever planned it: the lead of its epic, else the planner
        key_by_id = {t["id"]: t["key"] for t in tasks}
        for t in tasks:
            if t["status"] != "done" or t["key"] in self.forwarded:
                continue
            last = self.tasks.handoffs(t["key"])[-1]
            if last["threadId"] not in self.shared.values():
                self.threads.archive(last["threadId"])  # a per-task thread is done
                self.leads.pop(t["key"], None)
                log(f"archived {last['threadId']}")
            conflict = self.workspace.merge(t["key"], t["title"])
            if conflict:
                self.tasks.reopen(t["key"], f"The merge of your work into the project failed:\n\n```\n{conflict}"
                                            "\n```\n\nDo the task again, in a fresh worktree of the current code.")
                log(f"{t['key']} conflicts with the project → todo")
                continue
            self.forwarded.add(t["key"])
            epic = key_by_id.get(t["parentTaskId"])
            planner = self.leads[epic] if epic else self.planner
            floor = [f for f in tasks if f["parentTaskId"] == t["parentTaskId"]]
            self.wake(planner, f"{t['key']} «{t['title']}»\n{last['body']}", floor)
            log(f"handoff {t['key']} → {'lead of ' + epic if epic else 'planner'}: {last['body'].splitlines()[0]!r}")

    def dispatch_ready(self, tasks: list[dict]) -> None:
        # todo tasks whose blockers are done, urgent first, while an agent is free
        by_key = {t["key"]: t for t in tasks}
        running = sum(t["status"] == "in_progress" and "epic" not in t["labels"] for t in tasks)
        for t in sorted(tasks, key=lambda t: PRIORITY[t["priority"]]):
            role = ROLE_BY_LABEL.get(t["labels"][0]) if t["labels"] else None
            if t["status"] != "todo" or role is None:
                continue
            if any(by_key.get(k, {}).get("status") != "done" for k in blocked_by(t)):
                continue
            agent = self.config[role]
            if role != Role.lead and not self.free(agent, running):
                continue
            self.dispatch(t, agent, role)
            running += role != Role.lead  # a lead waits for its sub-tasks most of the time, it takes no slot

    def free(self, agent: AgentConfig, running: int) -> bool:
        if agent.mode == "shared":
            return agent not in self.shared or self.threads.status(self.shared[agent]) == "idle"
        return running < self.slots

    def dir_for(self, agent: AgentConfig, role: Role, key: str) -> Path:
        # a worker codes in a worktree of its task, a tester in the project itself, the rest write no code
        if agent.mode == "shared" or role == Role.lead:
            return self.workspace.agent_dir(Role.planner)
        return self.workspace.worktree(key) if role == Role.worker else self.workspace.workdir

    def dispatch(self, task: dict, agent: AgentConfig, role: Role) -> None:
        # a shared agent gets the task as a message; anyone else gets a thread of their own
        brief = prompt(
            "task_brief", key=task["key"], title=task["title"], labels=",".join(task["labels"]),
            priority=task["priority"], description=task["description"],
            handoffs="\n".join(f"Previous handoff:\n{h['body']}" for h in self.tasks.handoffs(task["key"])),
        )
        self.tasks.set_status(task["key"], "in_progress")
        # thread title = "<prompt> [<task>] <model>": the pi extension gates tools by the first word, the timeline reads the rest
        if agent.mode == "per_task":
            thread = self.threads.spawn(f"{agent.prompt} {task['key']} {agent.model}", prompt(agent.prompt) + "\n\n" + brief,
                                        agent.model, agent.thinking, self.dir_for(agent, role, task["key"]))
        elif agent in self.shared:
            thread = self.shared[agent]
            self.threads.tell(thread, brief)
        else:  # spawned with its first task: left idle, it invents work for itself
            thread = self.shared[agent] = self.threads.spawn(f"{agent.prompt} {agent.model}", prompt(agent.prompt) + "\n\n" + brief,
                                                             agent.model, agent.thinking, self.dir_for(agent, role, task["key"]))
        self.tasks.attach(task["key"], thread)
        if agent is self.config[Role.lead]:
            self.leads[task["key"]] = thread
        self.forwarded.discard(task["key"])  # a reopened task will hand off again
        log(f"task {task['key']} «{task['title']}» → {agent.prompt} {thread}")

    def deliver(self, tasks: list[dict]) -> bool:
        # the board is the postman: Mikhail's Telegram on one side, the agents' threads on the other
        for text in self.telegram.replies():
            write_message("human", Role.secretary, text)
            self.waiting = None
        floor = [t for t in tasks if t["parentTaskId"] is None]
        undelivered = messages()[self.relayed:]
        for m in undelivered:
            if m["to"] == "human":
                self.telegram.send(m["text"])
                wait = m.get("wait_minutes") or 0
                self.waiting = datetime.now() + timedelta(minutes=wait) if wait else None
            else:
                thread = self.secretary if m["to"] == Role.secretary else self.planner
                sender = "Mikhail" if m["from"] == "human" else f"the {m['from']}"
                when = datetime.fromisoformat(m["at"]).strftime("%H:%M:%S")  # the secretary tells his answer from what he said before it
                self.wake(thread, f"Message from {sender} at {when}:\n{m['text']}\n{m.get('details', '')}".strip(), floor)
            self.relayed += 1
            log(f"message {m['from']} → {m['to']}: {m['text'].splitlines()[0]!r}")
        if self.waiting and datetime.now() > self.waiting:
            self.waiting = None
            self.wake(self.secretary, "Mikhail has not answered within the time you gave him.", floor)
            log("Mikhail did not answer → secretary")
            return True
        return bool(undelivered)

    def reported(self) -> bool:
        return any(m["from"] == Role.planner and m["to"] == Role.secretary for m in messages())

    def tick(self) -> bool:
        # one pass; False when Mikhail has the report or an agent is dead
        tasks = self.tasks.all()
        delivered = self.deliver(tasks)
        # the run ends when the secretary is through with Mikhail: the report passed on, no answer awaited
        if self.reported() and not delivered and not self.waiting and self.threads.status(self.secretary) == "idle":
            log("the secretary is done with Mikhail; the run ends")
            return False
        self.forward_handoffs(tasks)
        self.dispatch_ready(tasks)
        if datetime.now() - self.last_wake > HEARTBEAT:
            self.wake(self.planner, f"Heartbeat: {HEARTBEAT.seconds // 60} quiet minutes.", [t for t in tasks if t["parentTaskId"] is None])
            log("heartbeat → planner")
        for thread in (self.planner, *self.leads.values(), *self.shared.values()):
            if not self.threads.alive(thread):
                log(f"{thread} keeps failing: bb thread log {thread}")
                return False
        return True

    def run(self, goal: str, after_tick: Callable[[], None] = lambda: None) -> None:
        self.start(goal)
        while self.tick():
            after_tick()
            time.sleep(TICK.seconds)
        for thread in (self.planner, *self.shared.values()):
            self.threads.archive(thread)  # archived threads stay readable in bb
        log(f"archived planner {self.planner}, secretary {self.secretary} and shared agents")
