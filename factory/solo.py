"""One agent, one task, no board: spawn it, wait for it to finish, print everything it sent outward.

Never while a run is going: its task lands on the run's board and a running board picks up the handoff,
and a secretary's message to Mikhail goes out through the run's Telegram.
"""

from pathlib import Path

from factory.bb import PROJECT, Tasks, Threads, bb
from factory.board import MESSAGES, log, messages, prompt
from factory.roles import LABEL_BY_ROLE, Role
from factory.workspace import Workspace


def create_task_and_return_key(title: str, description: str, label: str) -> str:
    task = bb("tasks", "create", "--project", PROJECT, "--title", title,
              "--description", description, "--priority", "medium", "--label", label)["task"]
    return task["key"]


def run_agent_on_one_task(role: Role, title: str, description: str, workdir: Path, label: str | None = None,
                          model: str = "openai-codex/gpt-5.6-terra", timeout_minutes: int = 20) -> None:
    # run one agent on a task of its own and print its handoff, its final output and what it wrote to Mikhail
    label = label or LABEL_BY_ROLE[role]  # the imitator plays whatever role its task needs, so it names its own
    tasks, threads, workspace = Tasks(), Threads(), Workspace(workdir)
    workspace.prepare()
    if not MESSAGES.exists():
        MESSAGES.write_text("")
    messages_before = len(messages())

    key = create_task_and_return_key(title, description, label)
    task_brief = prompt("task_brief", key=key, title=title, labels=label,
                        priority="medium", description=description, handoffs="")
    tasks.set_status(key, "in_progress")
    thread = threads.spawn(f"{role} {key} {model}", prompt(role) + "\n\n" + task_brief, model, workspace.workdir)
    tasks.attach(key, thread)
    log(f"{key} «{title}» → {role} {thread}")

    bb("thread", "wait", thread, "--status", "idle", "--timeout", f"{timeout_minutes}m",
       timeout=timeout_minutes * 60 + 30)
    handoffs = tasks.handoffs(key)
    print(f"\n--- {handoffs[-1]['body'] if handoffs else 'no handoff: the task is still open'}")
    # an agent that ends with `handoff` leaves no final text: the handoff is its answer
    print(f"\n--- final output\n{bb('thread', 'output', thread)['output'] or 'none'}")
    for message in messages()[messages_before:]:
        print(f"\n--- {message['from']} → {message['to']}\n{message['text']}")
    threads.archive(thread)
