import shutil
from pathlib import Path

import pytest

from factory.tools.voice import MODEL, Voice

FIXTURE = Path(__file__).parent / "fixtures/voice-ru.m4a"  # macOS `say -v Milena`, 3.5 s
on_this_mac = pytest.mark.skipif(not shutil.which("transcribe-cli") or not MODEL.exists(),
                                 reason="transcribe-cli and its model are installed under ~/.local on Mikhail's Mac only")


@on_this_mac
def test_a_russian_clip_comes_back_as_its_words() -> None:
    voice = Voice()

    text = voice.transcribe(FIXTURE)

    assert "второй вариант" in text.lower()
    assert "кольцом" in text.lower()


@on_this_mac
def test_a_file_that_is_not_audio_fails_with_a_reason(tmp_path: Path) -> None:
    voice = Voice()
    (tmp_path / "notes.txt").write_text("not audio")

    with pytest.raises(RuntimeError, match="ffmpeg could not read"):
        voice.transcribe(tmp_path / "notes.txt")


def test_a_missing_engine_fails_with_a_reason(tmp_path: Path) -> None:
    voice = Voice(cli="no-such-cli", model=tmp_path / "no-model.gguf")

    with pytest.raises(RuntimeError, match="not on this Mac"):
        voice.transcribe(FIXTURE)
