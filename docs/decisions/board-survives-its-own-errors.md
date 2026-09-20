# Plan: the board survives its own errors

On 2026-09-20 at 15:38 the secretary sent Mikhail three screenshots whose paths were in the worktree of
FAB-23, a task the board had already closed and whose tree it had dropped. `curl` could not open the
file, `upload` raised, and the run died at 15:43:56 after sending Mikhail the same text twenty-six
times. One missing file cost the whole run and fifteen minutes of Mikhail's attention.

The file part is fixed already (244ba11: a file that will not send is logged, the text goes once). This
plan is about the shape of the loop that turned one bad path into that, because the next bad path will
not be a file.

## What actually went wrong

Three separate things, each of which alone would have been survivable.

1. **A tick replays its own side effects.** `deliver()` sends a message and only then advances
   `self.relayed`. An error anywhere after the send means the next tick sends it again. The tick is a
   sequence of five steps over shared state, retried as a whole, so a failure in step three replays
   steps one and two. That is the engine that produced twenty-six copies of one message.
2. **`TRANSIENT` means "almost anything".** It is `(URLError, OSError, RuntimeError,
   subprocess.TimeoutExpired)`, and `RuntimeError` is what the factory's own code raises when something
   is wrong. So a bug is treated exactly like a network blip: retried every ten seconds for five
   minutes, and only then fatal. A blip deserves that. A path that will never exist does not.
3. **An error that escapes ends the run.** `serve()`'s `finally` archives every agent. That is right
   when the board is going away for good — a stray planner would write intents into whatever run
   `state/current` points at next — but it makes every unhandled error cost a manual resume, and the
   board is the only thing that can bring a run home.

And one thing outside the loop: **nobody is told.** The board went silent at 15:43 and Mikhail found out
by noticing that the messages looked wrong. The run had a planner, a secretary and three agents at work,
and no way to say "I am dead".

## The shape

The principle: **one failing item fails alone.** A tick touches many independent things — a message, a
thread, a task — and the failure of one must not replay, block or end the others.

- `deliver()` handles each message on its own: the message is counted as relayed first, then acted on,
  and a failure is a log line plus a note for the planner's next review. Same for the loop that wakes
  threads: one thread that will not take a message does not hold up the rest.
- `TRANSIENT` narrows to what is really remote and really temporary: `URLError`, `OSError`,
  `subprocess.TimeoutExpired`, and a `Remote` error raised by `bb.py` and `telegram.py` when the other
  side answers badly. A bare `RuntimeError` from the factory's own code is a bug, not weather.
- A tick that raises anything else logs it with its traceback and the board goes on to the next tick.
  The run ends only when the same step fails through the whole `OUTAGE` window — which is what that
  window was always for.
- The board says when it is in trouble: `bb notify` on the first non-transient error (`digest`, it is
  recovering), and on giving up (`telegram`, the run is down and needs a resume). One `dedupe_key` per
  run, so a repeated condition counts instead of filling the board.

## What this does not fix

The board dies when the shell that started it dies — twice today, because it was a background process of
a chat session. `nohup` is the current answer and it is not one. A launchd agent that keeps
`resume()` alive is the real fix, and it is its own plan: it needs the run to be resumable from cold,
which it now is, and a way to not restart a run that ended on purpose.

## Steps

- [x] `deliver()` per message: count first, act in a `try`, a failure is a log line and a
  `since_review` note. The wake loop the same way. Tests: a message whose send raises is not sent twice
  and does not stop the ones after it; a thread that will not take a message does not stop the others.
- [x] `Remote` in `factory/tools/`, raised by `bb.py` and `telegram.py` where they now raise
  `RuntimeError`; `TRANSIENT` becomes `(URLError, OSError, subprocess.TimeoutExpired, Remote)`. The two
  `RuntimeError`s telegram.py keeps are configuration — no token, no chat — and stay what they are. Test:
  a fault of the board's own is logged with the traceback that says where it is, the other side's is not.
- [x] `serve()`: a non-transient error logs its traceback and the tick is skipped, not fatal; the run
  ends when a step has failed for the whole `OUTAGE`. Test: a tick that raises once keeps the run alive,
  a tick that raises for longer than `OUTAGE` ends it.
- [x] `bb notify` from the board: `digest` on the first error it recovered from, `telegram` on giving
  up, `dedupe_key` per run. Test: the fake notifier hears both.
- [x] `docs/architecture/overview.md`: the tick is a sequence of independent items, not one transaction.
- [ ] Seen on a live run: an agent hands the board a path that is not there, the board says so and the
  run goes on.
