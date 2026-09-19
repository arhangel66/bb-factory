"""Every file the factory keeps under state/: what is in it and who writes it. state/ is gitignored."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # paths below must not depend on the cwd
STATE = ROOT / "state"
ROLES = STATE / "roles.json"  # {role: [tool]}; written at the start of a run, the pi extension gates tools by it
TOKEN_FILE = STATE / "telegram.env"  # FACTORY_TELEGRAM_TOKEN=...; `bb secret request` owns it, no agent ever reads it
SETTINGS = STATE / "telegram.json"  # {"chat", "who", "offset"}; the chat is whoever writes to the bot first

# a run is a directory under runs/; `current` is a symlink to the newest, every path of a run goes through it
RUNS = STATE / "runs"
CURRENT = STATE / "current"
RUN_FILE = CURRENT / "run.json"  # {"goal", "started", "workdir", "planner", "secretary"}; the board writes it
WORKDIR = CURRENT / "workdir"  # a symlink to the project the run works on: where its results are
TASKS = CURRENT / "tasks.json"  # {key: task}; the board is its only writer, the agents' tools read it
INTENTS = CURRENT / "intents.jsonl"  # {"at", "thread", "intent", ...}; the agents' tools append, the board folds
MESSAGES = CURRENT / "messages.jsonl"  # {"at", "from", "to", "text", "status"}; the board and the agents' tools append
EVENTS = CURRENT / "events.jsonl"  # the timeline, appended by the board as things happen; the ui replays it
KEYS = CURRENT / "keys"  # one directory per task key handed out; mkdir is the atomic counter the tools share
COSTS = CURRENT / "costs.json"  # {thread: cost}: role, model, thinking, tasks, time, turns, items, tokens; the board writes it as threads end


def start_run(started: str, workdir: Path) -> Path:
    # a fresh directory for the run, empty files for the appenders, `current` pointed at it
    run = RUNS / started
    (run / "keys").mkdir(parents=True)
    for name in ("intents.jsonl", "messages.jsonl", "events.jsonl"):
        (run / name).write_text("")
    (run / "workdir").symlink_to(workdir)
    if CURRENT.is_symlink():
        CURRENT.unlink()
    CURRENT.symlink_to(os.path.relpath(run, CURRENT.parent))
    return run

