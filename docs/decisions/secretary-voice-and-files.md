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
- A file becomes `<caption>\n(file: /abs/path)`; the path is under the run's own `inbox/`
  (`state/runs/<run>/inbox/`, resolved, so it stays right when `state/current` moves on), reachable by
  every agent by its absolute path. The secretary hands it to the planner with `tell_planner` when the
  file is work. Not `.factory/inbox/` in the project as first planned: `Telegram` would have needed the
  workspace for it, and the file belongs to the conversation it came in, not to the project.
- `contact_human` gains `files`, a list of absolute paths; the message carries them and the board sends
  each after the text, photos inline.
- Multipart upload without a new dependency: `curl -F` is on every Mac; `urllib` has no multipart.

## Steps

- [x] `transcribe-cli` installed for the whole Mac, at Mikhail's ask: the binary (4 MB, links only
  system frameworks) copied to `~/.local/bin/transcribe-cli`, which is on PATH, and the model to
  `~/.local/share/transcribe-cli/gigaam-v3-e2e-rnnt-Q8_0.gguf`; Beseda's copies stay untouched, and
  bb-loop could point at these too.
- [x] `factory/tools/voice.py`: `Voice(cli, model)` with `transcribe(audio: Path) -> str` — `ffmpeg`
  to 30-second 16 kHz mono WAV pieces in a temporary directory, `transcribe-cli -m -l ru -q -o` per
  piece, joined; a missing binary or model, an unreadable file, a non-zero exit or an empty text raise
  with a short reason. Test: a 3.5-second Russian clip made with macOS `say -v Milena` in
  `tests/fixtures/voice-ru.m4a`, skipped when the CLI is not on this Mac.
- [x] `factory/tools/telegram.py`: `Telegram(voice: Voice)`; `replies()` handles `voice`, `audio`,
  `photo` (the largest size), `document` besides `text` — `getFile`, download from
  `https://api.telegram.org/file/bot<token>/<path>` into the run's `inbox/<message_id>-<name>`;
  `send(text, files)` posts the text, then `sendPhoto`/`sendDocument` per file through `curl -F`.
  Tests in `tests/test_telegram.py` with a fake Bot API: five shapes in and out.
- [x] `factory/core/board.py`: `send(m["text"], m.get("files") or [])`; the fakes in
  `tests/test_board.py` and `tests/test_secretary.py` take `files`; one test — a message with `files`
  reaches the fake as files. `construct.py` wires `Telegram(voice=Voice())`.
- [x] `.pi/extensions/factory.ts`: `contact_human` takes optional `files: string[]` and writes them
  into the message; the description says a png or jpg shows as a picture, the rest as a document.
- [x] `factory/roles/prompts/secretary.md`: his voice as `(voice) …` may be misheard, ask about the
  word; a file as `(file: /path)`, pass the path on; screenshots and mockups go as `files`.
- [x] `docs/architecture/overview.md`: the `telegram.py` and `voice.py` lines.
- [ ] Live check with Mikhail's phone, on the first board that runs this code (the ios-kit board of
  2026-09-20 runs the old one and would eat the updates): one voice message, one photo, one picture
  back. Recorded here without quoting the transcript.

## Not done

- No paid fallback, no duplicate-send guard, no image validation: one person, one chat, a board tick
  that logs its failures.
- The binary and the model are copies under `~/.local`, not a build: when Beseda updates transcribe.cpp
  or its model, the copies stay as they are until someone copies again.
