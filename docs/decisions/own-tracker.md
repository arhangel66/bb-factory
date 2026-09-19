# Plan: the board owns the tasks

## Why

Two races in one evening, both from the same root: a task's status in bb's tracker is written by the board,
the planner and the worker, and it means two things at once — what the planner wants and where the task is
in execution. Any writer erases the other's meaning:

- the planner rewrote a task the board had just handed out; the `todo` that came with the rewrite made the
  board hand it out again, onto an existing worktree;
- a `canceled` set while a worker is busy is erased by the `done` of its handoff.

An agent's write into shared state is always based on a stale view: it reads the board, thinks for a
minute, then writes. No ordering of the tick closes that window. The fix is structural, not a guard:
**the board is the only writer of tasks; agents write intents, the board folds them.** It is how messages
already work (`state/messages.jsonl`, the board is the postman).

bb's tracker also costs more than it gives: every call is a 0.5 s subprocess, `blocked-by` lives as text in
the description, `create` lands in `backlog`, the run is scoped by a task number, the list is paged, and the
timeline is rebuilt every tick by parsing bb's system comments with regexes. bb's threads stay — they are
what bb is for.

## Model

A run is a directory; everything the run produces lives in it and nothing of it is shared with another run:

```
state/
  roles.json  telegram.env  telegram.json   — the factory's, as today
  current -> runs/<started>                  — a symlink; the pi extension finds the run through it
  runs/<YYYY-MM-DD-HHMMSS>/
    run.json        {goal, started, workdir, planner, secretary}
    workdir ->      the project the run works on: where to look for its results
    tasks.json      the board's view of the tasks
    intents.jsonl   what the agents asked for
    messages.jsonl  the post between Mikhail, the secretary and the planner
    events.jsonl    the timeline the ui shows
    keys/<n>/       the tools' atomic key counter
```

Keys are numbered per run, `FAB-1` up; a run is a directory, so the number needs no other scope. Worktree
branches of a previous run with the same key are removed by `prepare()`; thread titles repeat across runs,
the timeline tells threads by id.

`tasks.json` — the board's, written once per tick (temp file + rename):
`{key: {key, type, title, description, priority, blocked_by, parent, status, thread, handoffs, created_by}}`.
`type` is `code | test | epic | ask`, `status` is `todo | in_progress | done | canceled`, `handoffs` is
`[{at, thread, outcome, summary, text}]`.

`intents.jsonl` — the agents append, one line each, `{at, thread, intent, ...}`:

- `create` — `key, type, title, description, priority, blocked_by, parent` (the tool folds motivation and
  definition of done into the description)
- `cancel` — `key, why`
- `priority` — `key, priority`
- `handoff` — `key, outcome, summary, text`

The key is allocated by the tool, so a task can depend on one created a call earlier: `mkdir keys/<n>`
is atomic, the tool takes the first `n` that succeeds. `blocked_by` must name keys of this run — an
invented `FAB-1` fails right away instead of being fixed later by rewriting tasks.

Tasks are immutable after creation. To change a task: cancel it and create another. No `todo` from anyone
but the board; no description edits.

Fold rules, the only place they live (`factory/core/tracker.py`):

| intent | on status | effect |
|---|---|---|
| create | — | `todo`; a known key is ignored |
| cancel | todo, in_progress | `canceled` |
| priority | todo | set |
| handoff | in_progress | record, `done`, merge, wake the creator |
| handoff | canceled | record, drop the worktree, archive the thread, wake nobody |
| anything else | — | ignored, logged |
| any, from a thread this board did not spawn | — | ignored, logged: a leftover agent of an earlier run |

The board also archives every thread it spawned when it stops for any reason, an interrupt or a crash
included; a planner that outlives its board would otherwise keep writing into the next run.

A merge conflict is the board's own doing: it creates a copy of the task with the conflict on top of the
description, `blocked_by` none, for the same creator; the original stays `done` with its handoff, and
nobody is woken for it — the copy's handoff is the one that counts.

Events (`events.jsonl`) are appended by the board as it folds and dispatches, in the form of
`docs/examples/events.jsonl` — no reconstruction. A quiet tick touches the file so the ui's staleness
check still sees the run alive.

## Steps

- [x] `factory/state.py`: the run directory — `Run` with the paths above, `start(goal)` makes the directory
  and points `current` at it; `run.json`, `messages.jsonl`, `events` move under it; `state/run.json`,
  `state/events/` and `state/messages.jsonl` go. Test: a second start points `current` at the new directory.
- [x] `factory/core/tracker.py`: `Tracker` — load/save `tasks.json`, `fold(intent)` with the rules above,
  `ready()` (todo, blockers done), `key_exists`. Tests: each rule, cancel during work discards the handoff,
  duplicate create ignored, priority on a running task ignored.
- [x] `.pi/extensions/factory.ts`: tools append intents and read `tasks.json`; `board` also lists creates
  not folded yet as `pending`; `update_task` becomes `cancel_task(key, why)` and `set_priority(key, priority)`;
  `create_task` allocates the key and validates `blocked_by`. `factory/roles`: tool lists. Check: a solo
  imitator run leaves the expected lines in `intents.jsonl`.
- [x] `factory/core/board.py` on the tracker: `Tasks` and `handed_out` go, `forward_handoffs` becomes the
  handoff fold, dispatch marks `in_progress` itself, events are emitted where things happen. `factory/tools/bb.py`
  keeps `Threads` only. Tests: dispatch, secretary, the conflict copy.
- [x] `factory/core/timeline.py` and `construct.save` go; the board appends events. `test_timeline.py`
  becomes tests of the emitted events. `ui`: `/runs` lists `runs/*/events.jsonl`, the page loads
  `/state/runs/<run>/events.jsonl` and labels a run by its directory. Check: the page shows a live imitator run.
- [x] `factory/core/workspace.py`: `prepare()` removes leftover worktrees under `.factory/work/`
  (`FAB-95`, `FAB-100` are there today). Test.
- [x] Prompts: planner and lead — no "send the same task back", follow-up or cancel + create instead;
  `solo.py` on the tracker. Docs: `architecture/overview.md`, this file's index entry, `events-model.md`
  marked superseded on the timeline source.
- [x] Real run of the calculator goal end to end; the run log clean.

## Not in this step

Killing a worker on cancel (it finishes, its handoff is dropped). A `recall_task` for the planner —
add it when a run shows the planner needs it. Persisting the board's in-memory state across restarts.
