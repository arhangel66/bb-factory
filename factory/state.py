"""Every file the factory keeps under state/: what is in it and who writes it. state/ is gitignored."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # paths below must not depend on the cwd
STATE = ROOT / "state"
RUN_FILE = STATE / "run.json"  # {"number": first task number of the run, "planner": its thread}; the board writes it
EVENTS = STATE / "events"  # one <started>-<first task>.jsonl per run, rewritten every tick by construct.py
MESSAGES = STATE / "messages.jsonl"  # {"at", "from", "to", "text", "status"}; the board and the agents' tools append
TOKEN_FILE = STATE / "telegram.env"  # FACTORY_TELEGRAM_TOKEN=...; `bb secret request` owns it, no agent ever reads it
SETTINGS = STATE / "telegram.json"  # {"chat", "who", "offset"}; the chat is whoever writes to the bot first


def run_info() -> dict:
    return json.loads(RUN_FILE.read_text())
