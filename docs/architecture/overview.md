# Overview

## A run

`factory/construct.py` wires the services and starts a `Board` with a goal and a working directory.
The board spawns the planner and the secretary as bb threads, then ticks every 10 seconds:

1. **deliver** — messages between Mikhail's Telegram and the threads (`state/messages.jsonl` is the queue)
2. **forward handoffs** — a `done` task's handoff wakes whoever planned it (the lead of its epic, else the planner);
   a worker's worktree is merged into the project first, a conflict sends the task back to `todo`
3. **dispatch** — `todo` tasks whose blockers are done go to an agent by label, urgent first, while a slot is free
4. **heartbeat** — the planner is woken after five quiet minutes
5. **liveness** — a thread in `error` is retried a few times, then the run stops

The run ends when the planner has reported and the secretary has passed the report on to Mikhail.

## Roles — `factory/roles/`

`Role` is the enum every module uses; a role is its prompt file, its tools, and the first word of its thread title.

| role | takes | how many threads |
|---|---|---|
| planner | the goal | one per run |
| lead | `epic` tasks, splits them into `code` and `test` sub-tasks | one per epic |
| worker | `code` tasks | one per task, in a git worktree of the project |
| tester | `test` tasks | one per task, in the project itself |
| secretary | `ask` tasks; the only one that talks to Mikhail | one per run |
| imitator | any task, plays the role the task needs; for test runs | one shared thread |

`Config = dict[Role, AgentConfig]` says who serves each role in a run: `construct.py` has a test config
(the imitator serves worker, tester and secretary) and a real one.

## Tools

Two kinds, do not confuse them:

- **The agents' tools** — `.pi/extensions/factory.ts`, loaded by pi from `.pi/` in the agent's directory
  (a symlink back to the factory). `create_task`, `update_task`, `board`, `show_task`, `handoff`,
  `contact_human`, `tell_planner`, `report`. `TOOLS_BY_ROLE` in `factory/roles/` says which role gets which;
  the board writes it to `state/roles.json` and the extension reads it when a thread starts.
- **The board's tools** — `factory/tools/`: `bb.py` (tasks and threads through the bb CLI),
  `telegram.py` (the bot chat with Mikhail), `messages.py` (the conversation file).

## State — `factory/state.py`

Every file under `state/` (gitignored), one line each with its schema and writer. `messages.jsonl` is written
both by the board and by the agents' tools, in the same form.

## Workspace — `factory/core/workspace.py`

The run's project is a git repo; `.factory/` inside it holds one directory per agent and one worktree per
`code` task. Every agent directory links `.pi` back to the factory, and must be under pi's trusted paths.

## Timeline — `factory/core/timeline.py`, `factory/ui/`

The history of a run is rebuilt from bb (status comments and handoffs), the messages file and the threads —
nothing is tracked separately. `construct.py` writes it to `state/events/` every tick; `factory/ui/serve.py`
serves the page that replays it. See [../examples/](../examples/index.md) for the event form.

## One agent alone — `do.py`

`factory/core/solo.py` runs one agent on one task without a board and prints its handoff, its final text and
what it wrote to Mikhail. Never during a run: the board and the messages file are shared.
