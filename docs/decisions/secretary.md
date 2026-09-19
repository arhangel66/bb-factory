# Plan: the secretary

## What it is
A fifth agent, and the only door to Mikhail: nobody else writes to him, nobody else needs to know how.
The secretary knows where he reads, in what manner he wants to be written to and what is worth his
attention at all; the rest of the factory only says what it needs from him.

Its work is an `ask` task: the planner (or a lead) puts a question on the board, the secretary asks
Mikhail, waits as long as it said it would, and hands the answer back. The planner's final `report`
comes to it the same way — as a message to pass on, in its own words. Mikhail can also write first,
and what he says then reaches the planner through `tell_planner`. One thread per run, spawned with the
planner (every run ends with a report to it anyway), so several questions can become one message to him.

## The shape
```
planner --create_task(ask)--> board --brief--> secretary --contact_human(text, wait_minutes)-->
planner --report------------> board --wake-->      state/messages.jsonl (secretary -> human)
                                                       board tick (10 s): sendMessage, deadline noted
   answer -> message (human -> secretary) -> wake the secretary with it
   silence past the deadline             -> wake it with "no answer in N minutes"
secretary --handoff--> the ask task closes, whoever created it wakes with the answer
secretary --tell_planner--> message (secretary -> planner) -> wake the planner
```
No new store and no new page: `state/messages.jsonl` already carries `from`/`to`, and `factory/timeline.py`
already draws messages, so the conversation with Mikhail shows up on the dashboard by itself.

Nothing waits inside a tool: `contact_human` writes the message and returns. The board's 10-second tick is
the "separate loop" — sending, polling and timeouts all happen there, so an unanswered question blocks nothing.

## Steps

- [x] `state/telegram.json` (`state/` is already gitignored): `{"token": "...", "chat": null, "offset": 0}`.
      Mikhail pastes the token himself, so it never passes through an agent; `chat` fills in with the id of
      the first person who writes to the bot, `offset` keeps a restart from replaying old messages.
- [x] `factory/telegram.py` — one class over the Bot API, `urllib.request` from the stdlib, no new dependency:
      `Telegram.send(text)`, `Telegram.replies() -> list[str]` (getUpdates from the offset, only from `chat`).
- [x] `factory/board.py` — `relay_human()` in `tick()`, about a screen:
      unsent messages `to: "human"` go out and a `wait_minutes` question notes its deadline; every reply is
      appended as `human -> secretary` and wakes the secretary; a passed deadline wakes it with the timeout.
      `start()` spawns the secretary next to the planner; `tick()` stops when the planner has reported,
      the secretary is idle and no question is pending.
- [x] `Config.secretary: AgentConfig`, `ROLE_BY_LABEL["ask"] = "secretary"`, `.factory/planner/` as its
      directory (it writes no code). `construct.py` wires `Telegram()` into the `Board`; the test config
      puts the imitator in the secretary's place, and then nothing reaches Telegram.
- [x] `.pi/extensions/factory.ts`: role `secretary` = `contact_human`, `tell_planner`, `handoff`; `ask`
      added to the `create_task` types. Both new tools append one line to the messages file and return.
      `prompts/lead.md` says the same: a lead reaches Mikhail through an `ask` task too.
- [x] `prompts/secretary.md` + its row in `prompts/README.md`: the role, and a short "About Mikhail"
      section — where he reads, in which language, how short, what is worth waking him for. The one place
      to edit when the answer to "how do I reach him" changes. What to do on a timeout: ask once more,
      decide and hand off, or hand off `failed`. The report is retold to him, not forwarded as is.
- [x] `prompts/planner.md`: "There is no human to ask" becomes an `ask` task — for what only Mikhail can
      decide, not for what the planner should decide itself.

## Verify
- [x] `tests/test_secretary.py`, a fake Telegram and stub threads: a question goes out once and its answer
      wakes the secretary with the text; silence past the deadline wakes it with the timeout instead.
- [x] A real `ask` task: the question arrives in Telegram, the answer reaches the thread, the handoff wakes
      the planner. Then a report — Mikhail gets it in the secretary's words. Both visible in `state/run.log`.
- [ ] An imitator run still ends on the planner's report, with nothing sent to Telegram.

Found by the live run and fixed: the secretary took a message that had arrived *before* its question for
the answer to it. Every wake now carries the time the message was written, `contact_human` returns the time
its question went out, and the prompt says the two are to be compared. The `ask` label had to be created in
the tracker as well (`bb tasks label create --project FAB --name ask`).

## Left out
- One channel, Telegram, chosen in code. When there is a second one, the choice becomes the secretary's.
- Text only: no voice, no images, no attachments.
- One deadline at a time: a second question replaces the first one's timeout.
- Nothing survives a restart of the board — the pending question lives in memory, like `forwarded` today.
