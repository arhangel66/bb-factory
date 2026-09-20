# Lessons of the Meditate run

The first app built with the iOS kit (2026-09-20, started 12:45 with `kit=ios` and 10 slots, 41 tasks,
report due at 20:00). It is also the first run the board did not survive in one piece: it died at 15:43
and was resumed at 15:55, and everything below comes from that seam. Four defects, all of them the
board's own, all of them silent.

## Seen

- **A running board is the code it started with.** The board died at 15:43 of a screenshot path whose
  worktree it had already dropped — exactly the failure [board-survives-its-own-errors](board-survives-its-own-errors.md)
  was written for, and whose first half (244ba11) was already committed. The process had been started
  at 12:45 from the code as it was then. A fix lands on the next run or the next resume, never on the
  one that is going.

- **The resume left the agents at work in the archive.** `serve()`'s `finally` archives every thread;
  `resume()` unarchived the planner and the secretary and re-admitted the rest without unarchiving them.
  From 16:05 to 17:32 every amendment the planner made to FAB-5 — the one open epic — came back as
  `HTTP 409: Thread is archived`. Thirteen of them, an hour and a half of steering an epic that was
  told nothing. The board said `tick failed, retrying` and no more: a `Remote` error is `TRANSIENT`, so
  not even a traceback. Cleared by hand at 17:35, after which the epic closed.

- **One intent that failed took the rest of its batch with it.** `fold()` applies a batch of intents to
  the tasks, then acts on them one by one inside the tick's single `try`. At 16:05:53 the amendment of
  FAB-5 raised and swallowed FAB-25's handoff, written five seconds before it: the task reads `done` in
  `tasks.json`, the merge never ran, the worktree was never dropped, the thread was still sitting idle
  three hours later, and the planner was never told. That worker happened to have committed nothing, so
  this time nothing was lost — and it took no rare condition to get there, only two intents in one tick.

- **The resume wiped what the run had cost.** `costs.json` is rewritten from what the board holds in
  memory, and the resumed board started with none. The first thread it archived replaced the file: the
  12:45–15:43 half of the run, some twenty-five threads, is gone. What is left reads 17 threads and
  1.2 M tokens for a run of 41 tasks.

- **The agents' clocks were four hours behind.** The pi extension stamps intents and messages with
  `new Date().toISOString()` — UTC; the board stamps its own with `datetime.now().astimezone()` — local.
  Two places printed an agent's stamp raw: a task brief said `## Added at 12:05` for an amendment made
  at 16:05, and the secretary was told "Message from the planner at 14:56" at 18:56. Every time an
  agent read from another agent was wrong by the offset.

- **A false alarm reached Mikhail's Telegram.** The three notifications on his board at 16:11–16:19,
  one of them routed to Telegram, were the unit tests of the alarm itself: pytest's `tmp_path` name
  sat in the dedupe key, so they did not even collapse into one. The fixture patches `notify` now.
  Nothing in a test may reach a live bus, not even to be deduplicated there.

What held. The stopped-agent watch earned its keep: FAB-31's tester stopped answering at 18:24 and the
same task was on the board as FAB-38 within the tick. The quarter-hour review carried the planner across
the whole gap — it is what kept the run going while the epic heard nothing. And the run itself answered
Mikhail's messages, screenshots and corrections throughout.

## Plan

- [x] `resume()` unarchives every thread it takes back, not only the planner and the secretary: the
      board that went archived them all. Test: a resumed board unarchives the worker and the lead too
- [x] `fold()` acts on one intent at a time: a failure is a log line and a note for the planner's next
      review, and the intents behind it go on. Test: a handoff written behind an amendment that will
      not go through is still merged, its thread archived, its planner woken
- [x] `resume()` reads `costs.json` back before it archives anything, so the earlier board's threads
      stay counted. Test: a thread archived after the resume joins the file instead of replacing it
- [x] Both timestamps are read as the clock said, whoever wrote them: `datetime.fromisoformat(...)
      .astimezone()` in the task brief and in the wake that carries a message. Tests: an amendment and
      a message stamped in UTC reach their reader in local time
- [ ] An epic's lead is watched like everyone else. `watch()` skips epics because a lead is idle by
      design, and that is right — but idle by design is not the same as archived, gone, or refusing
      every word the board sends it. A thread the board cannot reach should be noticed the tick it
      happens, not at the next review
- [ ] The board outlives the shell that started it: a launchd agent that keeps `resume()` alive.
      Open since [board-survives-its-own-errors](board-survives-its-own-errors.md); the board has now
      died twice on a real run, and the second time nobody would have noticed for an hour
