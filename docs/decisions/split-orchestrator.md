# Plan: split the orchestrator, add a timeline

## Why
`factory/orchestrator.py` (200 lines) mixes four things: bb CLI calls, thread lifecycle (spawn/retry/archive),
board reading, and the loop itself. `tick()` alone forwards handoffs, dispatches, heartbeats and checks liveness.

## 1. Split by service (one service = one class, wired in construct.py)

- [x] `factory/bb.py` — `bb()` subprocess helper plus two thin classes over the CLI:
  - `Board`: tasks of the current run (`tasks()`, `create_goal()`, `set_status()`, `handoffs()`, `attach()`, `events()`)
  - `Threads`: `spawn()`, `tell()`, `status()`, `alive()` (holds the retry budget), `archive()`
- [x] `factory/orchestrator.py` — only the loop, ~90 lines: `start()`, `forward_handoffs()`, `dispatch_ready()`,
  `heartbeat()`, `run()`. Takes `config`, `board`, `threads`.
- [x] `factory/construct.py` — wiring: `board = Board()`, `threads = Threads()`, `factory(goal, config)`.
- [x] `blocked_by`, `board_lines`, prompt rendering stay as small module functions next to their only caller.

## 2. Timeline = read the board, write nothing

bb tasks already records every status change as a system comment with a timestamp
("Status changed to In Progress by agent (thr_…)"), and handoffs are agent comments. So:

- [x] `Board.events()` — status changes + handoffs of every task in the run, sorted by time.
- [x] `factory/timeline.py` — prints them, one line each:
  ```
  12:59:58  FAB-32  todo         Fix repeated equals and leading-decimal display
  13:00:04  FAB-32  in_progress
  13:00:09  FAB-32  in_review    ← repeated equals and leading decimal fixed
  13:00:19  FAB-32  done
  ```
  Run with `uv run python -m factory.timeline` (current run from `state/run.json`).

## 3. Ultra-short gist and answer

- [x] Gist = the task title. `create_task` description: "title: the gist in 4-6 words".
- [x] Answer = new `summary` parameter of `handoff` (4-6 words), stored as the first line of the comment:
  `handoff (ok): <summary>` then a blank line and the full text. The timeline shows the summary; the planner
  still gets the full text. `run.log` already prints the first 80 chars of a handoff, so it shows the summary too.

## Verify
- [x] `uv run python -m factory.construct` — an imitator run ends with `goal handed off`, no behaviour change.
- [x] `uv run python -m factory.timeline` — prints the history of that run with summaries.
- [ ] `wc -l factory/orchestrator.py` ≤ 100 — 158 with the two config dataclasses and helpers; the class itself is ~100.
