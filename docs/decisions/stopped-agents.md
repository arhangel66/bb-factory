# Plan: the board notices an agent that stopped

Mikhail saw a tester stop with a provider error and never come back. The run had nothing to say about it:
FAB-27 stayed `in_progress` for half an hour with its thread in bb's `error` status, the slot held, the
planner waiting for a handoff that could not arrive. The provider's answer was
`429 {"type":"rate_limit_error","message":"The engine is currently overloaded"}` — bb retried inside the
turn, gave up, and marked the turn failed.

## Why the board did not see it

`tick()` asked `Threads.alive()` about the planner, the leads and the secretary only — a thread per call,
`bb thread show` each. A worker's or a tester's thread was never asked about at all: the board learns of it
only when its handoff arrives, so a thread that dies before it hands off is waited for forever. The second
way to stop is quieter still and was invisible the same way: a turn that ends without `handoff`, leaving
the thread idle and the task open.

## The shape

- `Threads.statuses()` — one `bb thread list --section <factory>` per tick instead of a call per thread:
  `{thread: "active" | "idle" | "error"}`. The tick's own liveness check reads it too, so the board makes
  fewer calls than before, not more.
- `Board.started[thread]` — when the board last set the thread to work: at `admit`, and at every word it
  sends (`Board.tell` wraps `Threads.tell`, `wake` goes through it). A thread that has just been told
  something is not stopped, it is starting.
- `Board.restart(thread, status, nudge)` — a stopped thread gets `STALL` (five minutes) to come back by
  itself, then `Threads.revive`: `bb thread retry` when the turn failed, the `stalled` prompt when the turn
  ended with the task open. Three tries in all (`MAX_RETRIES`, the budget `alive()` already used), so a
  provider outage has a quarter of an hour to pass.
- `Board.watch(statuses)` — every task in progress whose thread is not `active`: the workers and the
  testers. An epic's lead and the secretary are skipped, they wait by design.
- `Board.give_up(task, status)` — the tries are spent: the thread is archived (its slot freed, its
  processes killed), its worktree dropped, and the task redone by `Tracker.copy` for whoever created it,
  with the reason on top of the description. The planner hears it at its next review through
  `since_review`, the same way a conflict is told. That is the existing rule for a dead worker, now
  reached without waiting for a handoff.
- The critical threads keep their old ending: a planner, a lead or the secretary that will not come back
  ends the run, with the stall between tries instead of three tries in thirty seconds.

## Steps

- [x] `Threads.statuses()` and `Threads.revive(thread, status, nudge)`; `alive()` stays for the conflict
  path in `bring_home`.
- [x] `factory/roles/prompts/stalled.md`: your task is still open, go on, nothing but `handoff` closes it.
- [x] `Board.started`, `Board.tell`, `restart`, `watch`, `give_up`; the tick reads the statuses once.
- [x] Tests: a working agent is left alone; a stopped one is told to go on; one that does not come back has
  its task canceled, its worktree dropped and a copy made; a freshly dispatched one is given its stall.
  `.venv/bin/python -m pytest -q` green, 68 tests.
- [x] `docs/architecture/overview.md`: the watch in the tick's steps.
- [ ] Seen working on a live run: a worker stopped by a provider error comes back by itself, or its task is
  redone without Mikhail noticing first.
