import json
import subprocess
from pathlib import Path

import pytest

from factory.tools import telegram as module
from factory.tools.telegram import Telegram


class FakeVoice:
    def transcribe(self, audio: Path) -> str:
        return f"heard {audio.name}"


class DeafVoice:
    def transcribe(self, audio: Path) -> str:
        raise RuntimeError("no speech recognized")


@pytest.fixture
def bot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Telegram:
    (tmp_path / "run").mkdir()
    monkeypatch.setattr(module, "CURRENT", tmp_path / "run")
    (tmp_path / "telegram.env").write_text("FACTORY_TELEGRAM_TOKEN=t0k\n")
    (tmp_path / "telegram.json").write_text(json.dumps({"chat": "7", "who": "Mikhail", "offset": 0}))
    return Telegram(FakeVoice(), settings=tmp_path / "telegram.json", token_file=tmp_path / "telegram.env")


def arriving(bot: Telegram, monkeypatch: pytest.MonkeyPatch, *messages: dict) -> list[str]:
    # the Bot API answers these messages from chat 7; every download writes a small file
    def call(method: str, **params: object) -> list | dict:
        if method == "getUpdates":
            return [{"update_id": 100 + n, "message": {"message_id": 10 + n, "chat": {"id": 7}, **message}}
                    for n, message in enumerate(messages)]
        if method == "getFile":
            return {"file_path": f"files/{params['file_id']}"}
        raise AssertionError(method)
    monkeypatch.setattr(bot, "call", call)
    monkeypatch.setattr(module.urllib.request, "urlretrieve", lambda url, path: Path(path).write_bytes(b"bytes"))
    return bot.replies()


def test_a_voice_message_arrives_as_its_transcript(bot: Telegram, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    texts = arriving(bot, monkeypatch, {"voice": {"file_id": "v1"}})

    assert texts == ["(voice) heard 10-voice.ogg"]
    assert (tmp_path / "run/inbox/10-voice.ogg").read_bytes() == b"bytes"


def test_a_transcription_that_fails_says_so(bot: Telegram, monkeypatch: pytest.MonkeyPatch) -> None:
    bot.voice = DeafVoice()

    texts = arriving(bot, monkeypatch, {"voice": {"file_id": "v1"}})

    assert texts == ["(voice message; transcription failed: no speech recognized)"]


def test_a_photo_with_a_caption_arrives_as_its_path(bot: Telegram, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sizes = [{"file_id": "small", "file_size": 1}, {"file_id": "large", "file_size": 9}]

    texts = arriving(bot, monkeypatch, {"caption": "вот скрин", "photo": sizes})

    assert texts == [f"вот скрин\n(file: {tmp_path / 'run/inbox/10.jpg'})"]
    assert (tmp_path / "run/inbox/10.jpg").exists()


def test_a_document_keeps_its_name(bot: Telegram, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    texts = arriving(bot, monkeypatch, {"document": {"file_id": "d1", "file_name": "brief.pdf"}})

    assert texts == [f"(file: {tmp_path / 'run/inbox/10-brief.pdf'})"]


def test_a_png_goes_out_as_a_photo_and_a_pdf_as_a_document(bot: Telegram, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple] = []
    uploads: list[list[str]] = []
    monkeypatch.setattr(bot, "call", lambda method, **params: calls.append((method, params)))
    monkeypatch.setattr(module.subprocess, "run", lambda argv, **kw: uploads.append(argv) or
                        subprocess.CompletedProcess(argv, 0, stdout='{"ok": true}', stderr=""))

    bot.send("look", [str(tmp_path / "screen.png"), str(tmp_path / "report.pdf")])

    assert calls == [("sendMessage", {"chat_id": "7", "text": "look"})]
    assert [argv[-1].rsplit("/", 1)[1] for argv in uploads] == ["sendPhoto", "sendDocument"]
    assert uploads[0][-2] == f"photo=@{tmp_path / 'screen.png'}"
    assert uploads[1][-2] == f"document=@{tmp_path / 'report.pdf'}"
