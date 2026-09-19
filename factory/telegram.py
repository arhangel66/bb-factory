"""Telegram, the only channel to Mikhail: the secretary writes through it and his answers come back here."""

import json
import urllib.request
from pathlib import Path

from factory.bb import ROOT

# state/ is gitignored. Two files, one writer each: `bb secret request` owns the token, the board owns the rest
TOKEN_FILE = ROOT / "state/telegram.env"  # FACTORY_TELEGRAM_TOKEN=...; no agent ever reads it
SETTINGS = ROOT / "state/telegram.json"  # {"chat", "who", "offset"}; the chat is whoever writes to the bot first
API = "https://api.telegram.org/bot{token}/{method}"


def token(path: Path = TOKEN_FILE) -> str:
    for line in path.read_text().splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "FACTORY_TELEGRAM_TOKEN":
            return value.strip().strip("\"'")
    raise RuntimeError(f"{path} has no FACTORY_TELEGRAM_TOKEN")


class Telegram:
    """One bot chat: the settings file keeps whose chat it is and how far its updates have been read."""

    def __init__(self, settings: Path = SETTINGS, token_file: Path = TOKEN_FILE):
        self.settings = settings
        self.token_file = token_file

    def call(self, method: str, **params: object) -> list | dict:
        request = urllib.request.Request(API.format(token=token(self.token_file), method=method),
                                         data=json.dumps(params).encode(),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            answer = json.load(response)
        if not answer["ok"]:
            raise RuntimeError(f"telegram {method}: {answer}")
        return answer["result"]

    def state(self) -> dict:
        return json.loads(self.settings.read_text()) if self.settings.exists() else {"chat": None, "who": "", "offset": 0}

    def send(self, text: str) -> None:
        state = self.state()
        if not state["chat"]:
            raise RuntimeError(f"nobody has written to the bot yet, so {self.settings} has no chat to send to")
        self.call("sendMessage", chat_id=state["chat"], text=text)

    def replies(self) -> list[str]:
        # what Mikhail wrote since the last read; the offset is stored so a restart does not replay it
        if not self.token_file.exists():
            return []  # no bot on this machine: a test run talks to nobody
        state = self.state()
        updates = self.call("getUpdates", offset=state["offset"], timeout=0)
        if not updates:
            return []
        texts = []
        for update in updates:
            message = update.get("message", {})
            sender = message.get("chat", {})
            chat = str(sender.get("id", ""))
            if not state["chat"]:  # ponytail: the first chat to write to the bot is his, and `who` says whose it is
                state["chat"], state["who"] = chat, sender.get("username") or sender.get("first_name", "")
            if chat == str(state["chat"]) and message.get("text"):
                texts.append(message["text"])
        state["offset"] = updates[-1]["update_id"] + 1
        self.settings.write_text(json.dumps(state, indent=2))
        return texts
