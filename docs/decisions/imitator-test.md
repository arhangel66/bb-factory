# Plan: first live run with an imitator

Goal: watch the loop planner → task → imitator → handoff → planner on real bb threads,
with every step printed to stdout as it happens. No secretary, no leads, no code written by anyone.

Engine: bb tasks is the task store. Planner and imitator run on bb's **pi** provider: a project
extension declares their tools (thin wrappers over `bb tasks`), and `.pi/settings.json` turns every
built-in tool off — so "the planner never sees code" is enforced, not prompted. Our Python is only
the tick loop.

## Setup (once)

- [ ] tracker project `FAB` linked to `proj_x6sd774izb`; labels `code`, `test`
- [ ] `.pi/settings.json`: `{"defaultTools": []}` (no read/bash/edit for any pi thread in this checkout)
- [ ] `.pi/extensions/factory.ts`, tools via `pi.registerTool` + `pi.exec("bb", ["tasks", ...])`:
      `create_task(type, title, motivation, dod, priority, blocked_by)`, `update_task(key, ...)`,
      `board()`, `handoff(key, outcome, text)` = comment + `--status in_review`
- [ ] preset `imitator`: pi, `kimi-coding/k3` (cheap), permission auto, project-default env,
      instructions = `prompts/imitator.md`
- [ ] `prompts/planner.md`: goal, "no human is available — decide yourself", close with `done` or
      rewrite and reopen with `todo`
- [ ] `prompts/imitator.md`: pretend the task was done; if the task is a test, invent two plausible bugs;
      end with `handoff`
- [ ] planner thread: pi, `openai-codex/gpt-5.4` (bb's pi catalog has no Claude models)

## Loop (`factory/orchestrator.py`, args in code, tick every 10 s)

- [ ] spawn the planner thread with the goal ("Browser calculator on Tailwind")
- [ ] tick: `bb tasks list --project FAB --json`
  - `in_review` and not yet forwarded → last comment from `bb tasks show --json` →
    `bb thread tell <planner> --mode queue "Handoff <key>: ..."`; remember the key in memory
  - `todo`, unblocked (`blocked-by:` line all `done`), free slot (2 for the test) →
    `bb tasks dispatch <key> --preset imitator`
  - quiet for 5 min → heartbeat tell with the board snapshot
- [ ] stop: board non-empty, nothing in `todo/in_progress/in_review`, planner thread idle
- [ ] log one line per action: `HH:MM:SS  dispatch FAB-3 → thr_…`, `HH:MM:SS  handoff FAB-3 → planner`

## Verify

- [ ] a run ends on its own; the log shows create → dispatch → handoff → done for every task
- [ ] one imitator run where a `test` task reports bugs → the planner creates follow-up `code` tasks

Skipped for now: secretary/ask tasks, epics/leads, persistence of "forwarded" across restarts,
priorities beyond bb's four levels.
