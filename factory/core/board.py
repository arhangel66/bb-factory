"""The board: the agents ask through intents, the board folds them, hands tasks out and brings the handoffs back."""

import json
import subprocess
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError

from factory.core.events import HUMAN, agent as agent_of_thread, emit
from factory.core.tracker import Tracker
from factory.core.workspace import Workspace
from factory.roles import ROLE_BY_LABEL, AgentConfig, Config, Role, prompt, save_tools_by_role
from factory.state import COSTS, EVENTS, RUN_FILE, start_run
from factory.tools.bb import Threads
from factory.tools.messages import messages, write_message
from factory.tools.telegram import Telegram

TICK = timedelta(seconds=10)
REVIEW = timedelta(minutes=15)  # how often the planner is asked to look at the whole
OUTAGE = timedelta(minutes=5)  # how long the network or bb may fail before the run gives up
TRANSIENT = (URLError, OSError, RuntimeError, subprocess.TimeoutExpired)  # what a tick may hit and the next may not
COLOR = {"ok": "green", "warning": "yellow", "failed": "red"}


def log(event: str) -> None:
    print(f"{datetime.now():%H:%M:%S}  {event}", flush=True)


def board_lines(tasks: list[dict]) -> str:
    return "\n".join(
        f"{t['key']}  {t['status']}  {t['priority']}  {t['type']}  {t['title']}" for t in tasks
    ) or "board is empty"


def handoff_body(handoff: dict) -> str:
    return f"handoff ({handoff['outcome']}): {handoff['summary']}\n\n{handoff['text']}"


class Board:
    def __init__(self, config: Config, tracker: Tracker, threads: Threads, workspace: Workspace, telegram: Telegram,
                 slots: int = 2, linger: bool = False):
        self.config = config
        self.tracker = tracker
        self.threads = threads
        self.workspace = workspace
        self.telegram = telegram
        self.slots = slots  # per-task threads running at once
        self.linger = linger  # after the report the board goes on: Mikhail talks to the run through the secretary
        self.planner = ""
        self.secretary = ""
        self.project = ""  # the bb project of the workdir: where the run's threads are made
        self.agents: dict[str, dict] = {}  # thread -> who runs in it, as the timeline names them
        self.alive: set[str] = set()  # threads spawned and not archived yet
        self.costs: dict[str, dict] = {}  # thread -> what it cost, complete once it is archived; written to COSTS
        self.leads: dict[str, str] = {}  # epic key -> its lead's thread
        self.shared: dict[AgentConfig, str] = {}  # shared agent -> its thread
        self.relayed = 0  # messages already delivered; the rest of the file is the postman's queue
        self.waiting: datetime | None = None  # when the answer the secretary is waiting for stops being worth it
        self.last_review = datetime.now()
        self.since_review: list[str] = []  # what went wrong since: the next review tells the planner

    def spawn(self, agent: AgentConfig, role: Role, title: str, text: str, path: Path) -> str:
        thread = self.threads.spawn(title, text, agent.model, agent.thinking, path, self.project)
        self.admit(thread, agent, role)
        return thread

    def admit(self, thread: str, agent: AgentConfig, role: Role) -> None:
        # a thread the board answers for from now on: named for the timeline, kept alive, its cost counted
        self.agents[thread] = agent_of_thread(role, agent.model, thread, imitator=agent.prompt == Role.imitator)
        self.alive.add(thread)
        self.costs[thread] = {"role": role, "model": agent.model, "thinking": agent.thinking,
                              "started": datetime.now().astimezone().isoformat()}
        emit(self.agents[thread], "agent", "started", thread)

    def archive(self, thread: str) -> None:
        self.threads.archive(thread)  # archived threads stay readable in bb
        self.alive.discard(thread)
        emit(self.agents[thread], "agent", "stopped", thread)
        self.record_cost(thread)

    def record_cost(self, thread: str) -> None:
        # the thread is through: its time, its tasks and what bb recorded of its tokens go to costs.json
        cost = self.costs[thread]
        ended = datetime.now().astimezone()
        cost.update(ended=ended.isoformat(), seconds=int((ended - datetime.fromisoformat(cost["started"])).total_seconds()),
                    tasks=[t["key"] for t in self.tracker.tasks.values() if t["thread"] == thread],
                    **self.threads.usage(thread))
        COSTS.write_text(json.dumps({t: c for t, c in self.costs.items() if "ended" in c}, ensure_ascii=False, indent=1))

    def agent_of(self, thread: str, task: dict) -> dict:
        # the imitator plays whatever role its current task needs
        agent = self.agents.get(thread) or agent_of_thread(ROLE_BY_LABEL[task["type"]], thread=thread)
        return {**agent, "role": ROLE_BY_LABEL[task["type"]]} if agent["imitator"] else agent

    def start(self, goal: str) -> None:
        # the goal is a message to the planner; the run is a directory of its own from here on
        self.workspace.prepare()
        self.project = self.threads.project_for(self.workspace.workdir)
        save_tools_by_role()
        started = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        start_run(started, self.workspace.workdir)
        write_message("human", Role.planner, goal)
        self.relayed = 1  # the goal is in the planner's prompt, it is not delivered twice
        emit(HUMAN, "message", "sent", Role.planner, goal)
        planner, secretary = self.config[Role.planner], self.config[Role.secretary]
        self.planner = self.spawn(planner, Role.planner, f"{planner.prompt} {planner.model}",
                                  prompt(planner.prompt, goal=goal), self.workspace.agent_dir(Role.planner))
        # the secretary starts with the planner: every run ends with a report for it to pass on
        self.secretary = self.shared[secretary] = self.spawn(
            secretary, Role.secretary, f"{secretary.prompt} {secretary.model}", prompt(secretary.prompt),
            self.workspace.agent_dir(secretary.prompt))
        RUN_FILE.write_text(json.dumps({"goal": goal, "started": started, "workdir": str(self.workspace.workdir),
                                        "planner": self.planner, "secretary": self.secretary}, ensure_ascii=False))
        log(f"goal «{goal}» → planner {self.planner}, secretary {self.secretary}, run {started}, "
            f"results in {self.workspace.workdir}")

    def wake(self, thread: str, event: str, floor: list[dict]) -> None:
        self.threads.tell(thread, prompt("wake", event=event, board=board_lines(floor)))

    def fold(self) -> None:
        # the agents' intents since the last tick: a create or a cancel is noted, a handoff brings the work home;
        # only this board's agents count — a thread it never spawned is a leftover of an earlier run
        for intent in self.tracker.fold(known=self.agents):
            task = self.tracker.tasks[intent["key"]]
            agent = self.agent_of(intent["thread"], task)
            if intent["intent"] == "create":
                emit(agent, "task", "created", task["key"], task["title"], type=task["type"], parent=task["parent"])
                log(f"{task['key']} «{task['title']}» created by the {agent['role']}")
            elif intent["intent"] == "cancel":
                emit(agent, "task", "canceled", task["key"], type=task["type"], parent=task["parent"])
                log(f"{task['key']} canceled by the {agent['role']}: {intent['why']!r}")
                self.since_review.append(f"{task['key']} canceled by the {agent['role']}: {intent['why']!r}")
                if task["thread"] in self.alive:  # canceled while running: its agent stops now, not at its handoff
                    self.release(task)
                    self.workspace.drop(task["key"])
            elif intent["intent"] == "amend":
                emit(agent, "task", "amended", task["key"], intent["text"], type=task["type"], parent=task["parent"])
                log(f"{task['key']} amended by the {agent['role']}: {intent['text'].splitlines()[0]!r}")
                if task["thread"] in self.alive:  # at work already: its agent reads the change now, not a waiting task's brief
                    self.threads.tell(task["thread"], prompt("amended", key=task["key"], who=agent["role"], text=intent["text"]))
            elif intent["intent"] == "handoff":
                self.bring_home(task, intent)
        for stray in self.tracker.strays:
            log(f"ignored {stray['intent']} {stray['key']} from {stray['thread']}: not an agent of this run")
        self.tracker.strays.clear()

    def bring_home(self, task: dict, handoff: dict) -> None:
        # the task's agent is through: its work is merged, its thread goes, whoever planned the task is woken.
        # work that does not merge goes back to its worker, still there, to merge the main branch in and hand
        # off again; only a dead worker's task is redone by a copy
        key = task["key"]
        agent = self.agent_of(handoff["thread"], task)
        emit(agent, "task", "handed_off", key, handoff["summary"], COLOR[handoff["outcome"]], task["type"], task["parent"])
        if handoff["outcome"] == "failed":
            self.since_review.append(f"{key} handed off red: {handoff['summary']!r}")
        if task["status"] == "canceled":
            self.workspace.drop(key)
            self.release(task)
            log(f"handoff {key} dropped: the task was canceled")
            return
        conflict = self.workspace.merge(key, task["title"])
        if conflict and self.threads.alive(task["thread"]):
            self.tracker.hand_back(key)
            emit(agent, "task", "returned", key, "not merged: the worker resolves the conflict",
                 type=task["type"], parent=task["parent"])
            self.threads.tell(task["thread"], prompt("conflict", conflict=conflict, main=self.workspace.main_branch()))
            log(f"{key} conflicts with the project → back to its worker {task['thread']}")
            self.since_review.append(f"{key} came back with a conflict")
            return
        self.release(task)
        if conflict:
            copy = self.tracker.copy(key, f"Redo of {key}: the merge of its work into the project failed:\n\n```\n"
                                          f"{conflict}\n```\n\nDo the task again, in a fresh worktree of the current code.")
            emit(agent, "task", "canceled", key, f"not merged, redone as {copy['key']}",
                 type=task["type"], parent=task["parent"])
            emit(self.agent_of(copy["created_by"], copy), "task", "created", copy["key"], copy["title"],
                 type=copy["type"], parent=copy["parent"])
            log(f"{key} conflicts with the project → {copy['key']}, after {copy['blocked_by'] or 'nothing'}")
            return
        planner = self.leads[task["parent"]] if task["parent"] else self.planner
        self.wake(planner, f"{key} «{task['title']}»\n{handoff_body(handoff)}", self.tracker.floor(task["parent"]))
        log(f"handoff {key} → {'lead of ' + task['parent'] if task['parent'] else 'planner'}: {handoff['summary']!r}")

    def release(self, task: dict) -> None:
        # a per-task thread is done with its task; a shared one goes on, an archived one stays archived
        if task["thread"] in self.alive and task["thread"] not in self.shared.values():
            self.archive(task["thread"])
            self.leads.pop(task["key"], None)

    def dispatch_ready(self) -> None:
        # todo tasks whose blockers are done, urgent first, while an agent is free
        running = sum(t["status"] == "in_progress" and t["type"] != "epic" for t in self.tracker.tasks.values())
        for t in self.tracker.ready():
            role = ROLE_BY_LABEL[t["type"]]
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
        # a worker codes in a worktree of its task, a tester in the project itself, the rest write no code;
        # bb gives a directory to one thread at a time, so nobody shares one
        if agent.mode == "shared":
            return self.workspace.agent_dir(agent.prompt)
        if role == Role.lead:
            return self.workspace.agent_dir(f"lead/{key}")
        return self.workspace.worktree(key) if role == Role.worker else self.workspace.workdir

    def brief(self, task: dict) -> str:
        # the task with what its reader cannot see otherwise: what was added to it while it waited, the epic it
        # is part of, the handoffs it waited on
        context = ""
        for amendment in task.get("amendments", []):
            context += f"\n\n## Added at {amendment['at'][11:16]}\n{amendment['text']}"
        if task["parent"]:
            epic = self.tracker.tasks[task["parent"]]
            context += f"\n\n## Epic {epic['key']} «{epic['title']}»\n{epic['description']}"
        for key in task["blocked_by"]:
            before = self.tracker.tasks.get(key)
            for handoff in before["handoffs"] if before else []:
                context += f"\n\n## Before this task: {key} «{before['title']}» ({handoff['outcome']})\n{handoff['text']}"
        return prompt("task_brief", key=task["key"], title=task["title"], type=task["type"],
                      priority=task["priority"], description=task["description"] + context)

    def dispatch(self, task: dict, agent: AgentConfig, role: Role) -> None:
        # a shared agent gets the task as a message; anyone else gets a thread of their own
        brief = self.brief(task)
        # thread title = "<prompt> [<task>] <model>": the pi extension gates tools by the first word, a lead's epic is the second
        if agent.mode == "per_task":
            thread = self.spawn(agent, role, f"{agent.prompt} {task['key']} {agent.model}",
                                prompt(agent.prompt) + "\n\n" + brief, self.dir_for(agent, role, task["key"]))
        elif agent in self.shared:
            thread = self.shared[agent]
            self.threads.tell(thread, brief)
        else:  # spawned with its first task: left idle, it invents work for itself
            thread = self.shared[agent] = self.spawn(agent, role, f"{agent.prompt} {agent.model}",
                                                     prompt(agent.prompt) + "\n\n" + brief,
                                                     self.dir_for(agent, role, task["key"]))
        self.tracker.start(task["key"], thread)
        emit(self.agent_of(thread, task), "task", "started", task["key"], type=task["type"], parent=task["parent"])
        if agent is self.config[Role.lead]:
            self.leads[task["key"]] = thread
        log(f"task {task['key']} «{task['title']}» → {agent.prompt} {thread}")

    def deliver(self) -> bool:
        # the board is the postman: Mikhail's Telegram on one side, the agents' threads on the other
        for text in self.telegram.replies():
            write_message("human", Role.secretary, text)
            self.waiting = None
        floor = self.tracker.floor(None)
        undelivered = messages()[self.relayed:]
        for m in undelivered:
            sender_thread = {Role.secretary: self.secretary, Role.planner: self.planner}.get(m["from"])
            emit(self.agents.get(sender_thread, HUMAN), "message", "sent", m["to"], m["text"], m["status"])
            if m["to"] == "human":
                self.telegram.send(m["text"], m.get("files") or [])
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
        self.fold()
        delivered = self.deliver()
        # the run ends when the secretary is through with Mikhail: the report passed on, no answer awaited;
        # a lingering board stays for what Mikhail writes next, and stops nudging the planner
        reported = self.reported()
        if reported and not self.linger and not delivered and not self.waiting \
                and self.threads.status(self.secretary) == "idle":
            log("the secretary is done with Mikhail; the run ends")
            return False
        self.dispatch_ready()
        if not reported and datetime.now() - self.last_review > REVIEW:
            self.wake(self.planner, self.review(), self.tracker.floor(None))
            self.last_review = datetime.now()
            log("review → planner")
        for thread in (self.planner, *self.leads.values(), *self.shared.values()):
            if not self.threads.alive(thread):
                log(f"{thread} keeps failing: bb thread log {thread}")
                return False
        return True

    def review(self) -> str:
        # what the planner judges every quarter hour: each open epic with its age and its sub-tasks by status,
        # and what was canceled, came back or failed since the last look — sub-tasks included, which it never sees otherwise
        now = datetime.now().astimezone()
        lines = [f"Review: {REVIEW.seconds // 60} minutes since the last look at the whole. It is {now:%H:%M}."]
        for epic in self.tracker.tasks.values():
            if epic["type"] == "epic" and epic["status"] == "in_progress":
                minutes = int((now - datetime.fromisoformat(epic["started"])).total_seconds() // 60)
                counts = Counter(t["status"] for t in self.tracker.floor(epic["key"]))
                lines.append(f"- {epic['key']} «{epic['title']}»: {minutes} minutes in, sub-tasks "
                             + (", ".join(f"{n} {status}" for status, n in counts.items()) or "none yet"))
        if self.since_review:
            lines.append("Since the last look: " + "; ".join(self.since_review))
        lines.append("A verdict per epic: goes on as it is, gets an amendment, or is canceled. Then what is stuck, "
                     "what is wasted, and what the clock says against the goal's deadline.")
        self.since_review = []
        return "\n".join(lines)

    def run(self, goal: str) -> None:
        self.start(goal)
        self.serve()

    def resume(self) -> None:
        # the run state/current points at, its board gone: the planner and the secretary come back from the
        # archive, the tasks are as tasks.json left them, and the board lingers for Mikhail's messages
        run = json.loads(RUN_FILE.read_text())
        save_tools_by_role()  # the tools may have changed since the run started
        self.project = self.threads.project_for(self.workspace.workdir)
        self.tracker.tasks = json.loads(self.tracker.tasks_file.read_text())
        self.tracker.folded = len(self.tracker.intents_file.read_text().splitlines())
        self.relayed = len(messages())
        self.linger = True
        for role in (Role.planner, Role.secretary):
            self.threads.unarchive(run[role])
            self.admit(run[role], self.config[role], role)
        self.planner, self.secretary = run[Role.planner], run[Role.secretary]
        self.shared[self.config[Role.secretary]] = self.secretary
        log(f"resumed run {run['started']}: planner {self.planner}, secretary {self.secretary}")
        self.serve()

    def serve(self) -> None:
        # tick until the run is over; a failing network or bb is retried for a while, not fatal at once
        failing_since: datetime | None = None
        try:
            while True:
                try:
                    going = self.tick()
                    failing_since = None
                except TRANSIENT as error:
                    failing_since = failing_since or datetime.now()
                    if datetime.now() - failing_since > OUTAGE:
                        raise
                    log(f"tick failed, retrying: {error}")
                    going = True
                self.tracker.save()
                EVENTS.touch()  # a quiet tick still tells the ui the run is alive
                if not going:
                    break
                time.sleep(TICK.seconds)
        finally:
            # a board that is interrupted or crashes leaves no agent behind: a stray planner would keep
            # writing intents into whatever run state/current points at next
            for thread in sorted(self.alive):
                self.archive(thread)
            log(f"archived planner {self.planner}, secretary {self.secretary} and every other agent")
