"""One agent, one task, no board: spawn it, wait for it to finish, print everything it sent outward.

Never while a run is going: it starts a run directory of its own and points state/current at it, and the
running board's agents would write there.
"""

from datetime import datetime
from pathlib import Path

from factory.core.board import handoff_body, log
from factory.core.tracker import Tracker, allocate_key, write_intent
from factory.core.workspace import Workspace
from factory.roles import LABEL_BY_ROLE, Model, Role, Thinking, prompt, save_tools_by_role
from factory.state import start_run
from factory.tools.bb import Threads, bb
from factory.tools.messages import messages


def run_agent_on_one_task(role: Role, title: str, description: str, workdir: Path, label: str | None = None,
                          model: Model = Model.gpt_5_6_terra, thinking: Thinking = Thinking.medium,
                          timeout_minutes: int = 20) -> None:
    # run one agent on a task of its own and print its handoff, its final output and what it wrote to Mikhail
    label = label or LABEL_BY_ROLE[role]  # the imitator plays whatever role its task needs, so it names its own
    tracker, threads, workspace = Tracker(), Threads(), Workspace(workdir)
    workspace.prepare()
    save_tools_by_role()
    start_run(datetime.now().strftime("%Y-%m-%d-%H%M%S"), workspace.workdir)

    key = allocate_key()
    write_intent("human", "create", key=key, type=label, title=title, description=description, priority="medium")
    tracker.fold()
    task_brief = prompt("task_brief", key=key, title=title, type=label, priority="medium", description=description)
    thread = threads.spawn(f"{role} {key} {model}", prompt(role) + "\n\n" + task_brief, model, thinking,
                           workspace.workdir)
    tracker.start(key, thread)
    tracker.save()
    log(f"{key} «{title}» → {role} {thread}")

    bb("thread", "wait", thread, "--status", "idle", "--timeout", f"{timeout_minutes}m",
       timeout=timeout_minutes * 60 + 30)
    tracker.fold()
    tracker.save()
    handoffs = tracker.tasks[key]["handoffs"]
    print(f"\n--- {handoff_body(handoffs[-1]) if handoffs else 'no handoff: the task is still open'}")
    # an agent that ends with `handoff` leaves no final text: the handoff is its answer
    print(f"\n--- final output\n{bb('thread', 'output', thread)['output'] or 'none'}")
    for message in messages():
        print(f"\n--- {message['from']} → {message['to']}\n{message['text']}")
    threads.archive(thread)
