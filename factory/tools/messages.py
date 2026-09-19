"""state/messages.jsonl, the run's conversation: the board and the agents' own tools append to it the same way."""

import json
from datetime import datetime

from factory.state import MESSAGES


def write_message(sender: str, to: str, text: str) -> None:
    message = {"at": datetime.now().astimezone().isoformat(), "from": sender, "to": to, "text": text, "status": None}
    with MESSAGES.open("a") as file:
        file.write(json.dumps(message, ensure_ascii=False) + "\n")


def messages() -> list[dict]:
    return [json.loads(line) for line in MESSAGES.read_text().splitlines() if line]
