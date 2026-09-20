# Plan: the secretary hears voice and passes files both ways

Mikhail talks to the factory from his phone. Today the bot takes only text: a voice message is dropped
in `Telegram.replies()`, a photo or a document never reaches anyone, and the secretary has no way to
send him a screenshot. bb-loop (`~/w/learning/bb-loop`, `bbloop/input/voice.py`,
`bbloop/input/telegram_listener.py`, `bbloop/output/telegram_sender.py`) does all three; this takes its
shape with a tenth of its code, because the factory is one bot, one chat, one person.

## What bb-loop does and what is taken

- Voice: Beseda's speech stack read in place — the GigaAM v3 GGUF model in
  `~/Library/Application Support/Beseda/runtime/models/`, Russian with punctuation — decoded by `ffmpeg`
  to 16 kHz mono. bb-loop loads the `CTranscribe.framework` library through ctypes in a throwaway
  process and cuts the audio into 25-second windows itself, because the model drops most of the speech
  past its training window. Here the built `transcribe-cli` from
  `~/w/learning/beseda/untracked/scripts/asr-bench/transcribe.cpp/build/bin/` does the same from the
  shell, and it was measured on 2026-09-20: the first 60 s of a Russian recording came back as 86 words
  in one call and 86 words (41+45) in two 30-second halves, two words lost in the one-call version,
  0.3 s per call. So: `ffmpeg` cuts the file into 30-second WAV pieces, the CLI reads each, the texts
  are joined. No ctypes, no windowing code, no paid fallback (`bb voice transcribe` stays unused).
- Files in: the largest `photo` size or the `document` is fetched with `getFile` and stored; the
  message carries the path. bb-loop validates images with Pillow and caps sizes; here the file is
  saved as it came, under a 20 MB cap that is Telegram's own limit for bots.
- Files out: `sendPhoto` for `.png`/`.jpg`, `sendDocument` for the rest, the text as the caption.
  bb-loop guards against double sends with a database claim; here a send is one board tick and a
  failure is a log line, as for text.

## The shape

```
Mikhail --voice/photo/document--> Telegram.replies(inbox) --text with the transcript or the path-->
    messages.jsonl (human -> secretary) --wake--> the secretary
secretary --contact_human(text, wait_minutes, files)--> messages.jsonl --board tick--> Telegram.send(text, files)
```

- A voice message becomes `(voice) <transcript>`; a failed transcription becomes
  `(voice message; transcription failed: <reason>)` so the secretary can ask him to type it.
- A file becomes `<caption>\n(file: /abs/path)`; the path is under the project's `.factory/inbox/`,
  reachable by every agent of the run and ignored by git like the rest of `.factory/`. The secretary
  hands the path to the planner with `tell_planner` when the file is work.
- `contact_human` gains `files`, a list of absolute paths; the message carries them and the board sends
  each after the text, photos inline.
- Multipart upload without a new dependency: `curl -F` is on every Mac; `urllib` has no multipart.

## Steps

- [ ] `factory/tools/voice.py`: `Voice(cli, model)` with `transcribe(audio: Path) -> str` — `ffmpeg`
  to 30-second 16 kHz mono WAV pieces in a temporary directory, `transcribe-cli -m -l ru -q -o` per
  piece, joined; a missing binary, model or `ffmpeg`, a non-zero exit or an empty text raise with a
  short reason. Test: a 5-second Russian clip made with macOS `say -v Milena` in `tests/fixtures/`,
  skipped when the CLI is not on this Mac. Check: `.venv/bin/python -m pytest -q`.
- [ ] `factory/tools/telegram.py`: `Telegram(voice: Voice)`; `replies(inbox: Path)` handles `voice`,
  `audio`, `photo`, `document` besides `text` — `getFile`, download from
  `https://api.telegram.org/file/bot<token>/<path>`, into `inbox/<message_id>-<name>`; `send(text,
  files)` posts the text, then `sendPhoto`/`sendDocument` per file through `curl -F`. Test: fake
  `call` and download, three shapes of update → three texts; `send` with a png → `sendPhoto`.
- [ ] `factory/core/board.py`: `replies(self.workspace.factory / "inbox")`; `send(m["text"],
  m.get("files") or [])`. `tests/test_board.py`, `tests/test_secretary.py`: the fakes take the new
  arguments; one test — a message with `files` reaches the fake as files.
- [ ] `.pi/extensions/factory.ts`: `contact_human` takes optional `files: string[]` and writes them
  into the message; the description says photos show inline and what a path must be.
- [ ] `factory/roles/prompts/secretary.md`: three lines — his voice comes as `(voice) …` and may be
  misheard, ask when it reads wrong; a file comes as a path, pass it on; screenshots and reports go
  to him as `files`, not as text. `tests/test_prompts.py` if it checks the prompt.
- [ ] `docs/architecture/overview.md`: `telegram.py` and `voice.py` lines; `docs/index.md` if needed.
- [ ] Live check with Mikhail's phone, the running bot: one voice message, one photo, one screenshot
  back. Recorded here without quoting the transcript.

## Not done

- No paid fallback, no duplicate-send guard, no image validation: one person, one chat, a board tick
  that logs its failures.
- The CLI path is a constant in `voice.py`; when Beseda moves its build, one line changes. Copying the
  binary and the model into the factory was considered and rejected: 261 MB that already lives here.
