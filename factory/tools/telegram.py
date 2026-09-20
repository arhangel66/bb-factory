"""Telegram, the only channel to Mikhail: the secretary writes through it and his answers come back here."""

import json
import subprocess
import urllib.request
from pathlib import Path

from factory.state import CURRENT, SETTINGS, TOKEN_FILE
from factory.tools.voice import Voice

API = "https://api.telegram.org/bot{token}/{method}"
FILES = "https://api.telegram.org/file/bot{token}/{path}"
PHOTO = (".png", ".jpg", ".jpeg")  # shown inline; anything else arrives as a document


def token(path: Path = TOKEN_FILE) -> str:
    for line in path.read_text().splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "FACTORY_TELEGRAM_TOKEN":
            return value.strip().strip("\"'")
    raise RuntimeError(f"{path} has no FACTORY_TELEGRAM_TOKEN")


class Telegram:
    """One bot chat: the settings file keeps whose chat it is and how far its updates have been read."""

    def __init__(self, voice: Voice, settings: Path = SETTINGS, token_file: Path = TOKEN_FILE):
        self.voice = voice
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

    def send(self, text: str, files: list[str] = ()) -> None:
        state = self.state()
        if not state["chat"]:
            raise RuntimeError(f"nobody has written to the bot yet, so {self.settings} has no chat to send to")
        if text:
            self.call("sendMessage", chat_id=state["chat"], text=text)
        for file in files:
            self.upload(state["chat"], Path(file))

    def upload(self, chat: str, file: Path) -> None:
        # curl: urllib has no multipart
        field = "photo" if file.suffix.lower() in PHOTO else "document"
        method = "sendPhoto" if field == "photo" else "sendDocument"
        done = subprocess.run(["curl", "-sS", "-F", f"chat_id={chat}", "-F", f"{field}=@{file}",
                               API.format(token=token(self.token_file), method=method)],
                              capture_output=True, text=True, timeout=120)
        if done.returncode != 0 or not json.loads(done.stdout or "{}").get("ok"):
            raise RuntimeError(f"telegram {method} {file.name}: {done.stdout or done.stderr}")

    def replies(self) -> list[str]:
        # what Mikhail wrote since the last read, his voice as text, his files as paths; the offset is stored
        # so a restart does not replay it
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
            if chat == str(state["chat"]) and (text := self.text_of(message)):
                texts.append(text)
        state["offset"] = updates[-1]["update_id"] + 1
        self.settings.write_text(json.dumps(state, indent=2))
        return texts

    def text_of(self, message: dict) -> str:
        # a text as it is; a voice as its transcript; a photo or a document as the path it was saved to
        caption = message.get("text") or message.get("caption") or ""
        if audio := message.get("voice") or message.get("audio"):
            path = self.download(audio["file_id"], f"{message['message_id']}-{audio.get('file_name', 'voice.ogg')}")
            try:
                heard = f"(voice) {self.voice.transcribe(path)}"
            except (RuntimeError, subprocess.TimeoutExpired) as failure:
                heard = f"(voice message; transcription failed: {failure})"
            return "\n".join(part for part in (caption, heard) if part)
        if photo := message.get("photo"):  # every size of one picture; the largest is the picture
            largest = max(photo, key=lambda size: size.get("file_size", 0))
            path = self.download(largest["file_id"], f"{message['message_id']}.jpg")
        elif document := message.get("document"):
            path = self.download(document["file_id"], f"{message['message_id']}-{document.get('file_name', 'file')}")
        else:
            return caption
        return "\n".join(part for part in (caption, f"(file: {path})") if part)

    def download(self, file_id: str, name: str) -> Path:
        # into the run's inbox, resolved so the path stays right after state/current moves on to the next run
        inbox = CURRENT.resolve() / "inbox"
        inbox.mkdir(exist_ok=True)
        remote = self.call("getFile", file_id=file_id)["file_path"]
        path = inbox / name
        urllib.request.urlretrieve(FILES.format(token=token(self.token_file), path=remote), path)
        return path
