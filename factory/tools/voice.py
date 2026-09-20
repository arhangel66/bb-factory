"""A voice message becomes text on this Mac: transcribe.cpp's CLI and the GigaAM v3 model (Russian, with
punctuation), both from Beseda's build, installed once for the whole Mac under ~/.local."""

import shutil
import subprocess
import tempfile
from pathlib import Path

CLI = "transcribe-cli"  # ~/.local/bin, copied from ~/w/learning/beseda/untracked/scripts/asr-bench/transcribe.cpp/build/bin
MODEL = Path.home() / ".local/share/transcribe-cli/gigaam-v3-e2e-rnnt-Q8_0.gguf"
# GigaAM drops speech past its training window: 60 s in one call lost two words, 30 s pieces lost none
PIECE_SECONDS = 30


class Voice:
    """Speech to text through transcribe-cli, in 30-second pieces; raises with a short reason, never the tools' output."""

    def __init__(self, cli: str = CLI, model: Path = MODEL):
        self.cli = cli
        self.model = model

    def transcribe(self, audio: Path) -> str:
        # any container ffmpeg reads: Telegram's ogg/opus, an m4a, a wav
        if not shutil.which(self.cli) or not self.model.exists():
            raise RuntimeError(f"{self.cli} or {self.model} is not on this Mac")
        with tempfile.TemporaryDirectory(prefix="factory-voice-") as directory:
            pieces = Path(directory)
            cut = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio), "-ac", "1", "-ar", "16000",
                                  "-sample_fmt", "s16", "-f", "segment", "-segment_time", str(PIECE_SECONDS),
                                  str(pieces / "%03d.wav")], capture_output=True, timeout=120)
            if cut.returncode != 0:
                raise RuntimeError("ffmpeg could not read the audio")
            texts = [self.piece(wav) for wav in sorted(pieces.glob("*.wav"))]
        text = " ".join(text for text in texts if text)
        if not text:
            raise RuntimeError("no speech recognized")
        return text

    def piece(self, wav: Path) -> str:
        out = wav.with_suffix(".txt")
        done = subprocess.run([self.cli, "-m", str(self.model), "-l", "ru", "-q", "-o", str(out), str(wav)],
                              capture_output=True, timeout=120)
        if done.returncode != 0:
            raise RuntimeError(f"{self.cli} failed on a piece")
        return out.read_text().strip()
