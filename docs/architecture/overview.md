# Overview

## A run

`factory/construct.py` wires the services and starts a `Board` with a goal and a working directory.
The board makes a run directory under `state/runs/`, spawns the planner and the secretary as bb threads,
then ticks every 10 seconds:

1. **fold** — the intents the agents appended (`intents.jsonl`) become tasks (`Tracker`, the only writer of
   `tasks.json`): a create is noted, a cancel stops the task's agent at once, an amend is appended to the
   task and told to its agent if one is at work, a handoff brings the work home — the worker's worktree is
   merged into the project and whoever planned the task is woken (the lead of its epic, else the planner);
   work that does not merge goes back to its worker with the conflict, the worktree kept, to merge the main
   branch in and hand off again; a dead worker's task is canceled and a copy takes its place among the
   blockers, waiting for the code tasks in flight; a canceled task's work is dropped. One intent at a
   time: one the board cannot act on is a log line and a note for the planner's review, and the intents
   behind it in the same tick — a handoff among them — go on
2. **deliver** — messages between Mikhail's Telegram and the threads (`messages.jsonl` is the queue). Each
   message is counted as delivered before it is handed on, so one that fails half-way is lost once and
   never sent again; the failure is logged and told to the planner at its next review. A repeated message
   is damage to Mikhail no one can take back, a lost one he can be told about
3. **dispatch** — `todo` tasks whose blockers are done go to an agent by type, urgent first, while a slot is
   free; the brief carries the task's amendments, its epic and the handoffs of the tasks it waited on
4. **review** — every 15 minutes the planner gets every open epic with its age and its sub-tasks by status,
   plus what was canceled, came back with a conflict or was handed off red since the last look, and is
   asked for a verdict per epic
5. **watch** — one `bb thread list` gives the status of every thread. A task's thread that is neither
   working nor handed off — its turn failed on the provider, or ended with the task still open — is given
   five minutes, then started again (`bb thread retry` or the `stalled` prompt), three tries in all; then
   the board gives up on it, archives it, drops its worktree and the task is redone by a copy, and the
   planner hears it at its next review. A planner, a lead or the secretary that will not come back ends
   the run instead

A tick that raises is skipped, not fatal: the other side may answer at the next one, and a fault of the
board's own code costs one tick's work rather than the run — it is logged with its traceback, so the log
says where it is. Only a step that keeps failing for the whole `OUTAGE` (5 minutes) ends the run. The
board says so itself through `bb notify` (`factory/tools/notify.py`): `digest` when it recovers from a
failing tick, `telegram` when it gives up, one dedupe key per run. `TRANSIENT` — what may go through next
time — is `URLError`, `OSError`, `subprocess.TimeoutExpired` and `Remote`, the error `bb.py` and
`telegram.py` raise when the other side answers badly; a bare `RuntimeError` from the factory's own code
is a bug, not weather.

A thread the board archives takes what it started with it: every process whose environment carries its
`BB_THREAD_ID` is killed (`factory/tools/processes.py`), so no server outlives its agent on its port.

The goal is reached when the planner has reported and the secretary has passed the report on to Mikhail.
A lingering board (the default in `construct.py`) keeps the planner and the secretary after that, so
Mikhail's messages become more work until Ctrl-C; `Board.resume()` re-attaches to the run `state/current`
points at after its board is gone: the planner, the secretary and every agent that was at work come back
out of the archive the old board put them in, and `costs.json` is read back so its threads stay counted.

Agents never write a task: a task is created once, its text stays as it was, and a change is an amendment
appended to it (`amend_task`) — or a cancel. So no agent can act on a stale view of the board — see
[../decisions/own-tracker.md](../decisions/own-tracker.md).

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

Every `AgentConfig` names its `Model` and its `Thinking` — no defaults, so `construct.py` alone says who runs
on what and how long it reasons. `Model` is bb's pi catalog (`bb provider models pi`), `Thinking` is bb's
`--reasoning-level`: low, medium, high, xhigh, max.

## Tools

Two kinds, do not confuse them:

- **The agents' tools** — `.pi/extensions/factory.ts`, loaded by pi from `.pi/` in the agent's directory
  (a symlink back to the factory). `create_task`, `amend_task`, `cancel_task`, `set_priority`, `board`,
  `show_task`, `handoff`, `contact_human`, `tell_planner`, `tell_secretary`, `report`. They read `tasks.json` and append to `intents.jsonl`
  and `messages.jsonl`; none of them changes a task. `TOOLS_BY_ROLE` in `factory/roles/` says which role
  gets which; the board writes it to `state/roles.json` and the extension reads it when a thread starts.
- **Skills by role** — `.agents/skills/` is the factory's store (`npx skills add … -a universal`,
  `skills-lock.json` beside it); `SKILLS_BY_ROLE` in `factory/roles/` names each role's set; every agent
  directory gets a `.pi/` of its own with the factory's extensions and settings linked in and the role's
  skills linked from the store. A project's own `.agents/skills` and Mikhail's personal skills load on top.
- **Kits** — `factory/kits.py`: a preset a run names (`kit=IOS`): a repository whose `.agents/skills/` are copied
  into the project and committed before any thread exists, whose `docs/index.md` is the way in, and whose
  brief the planner hears before the goal. The factory knows where a kit's parts are, not what iOS is.
- **The board's tools** — `factory/tools/`: `bb.py` (threads through the bb CLI, in the bb project of the
  run's workdir, created when the workdir has none),
  `telegram.py` (the bot chat with Mikhail: his text, his voice as text, his files into the run's `inbox/`,
  the secretary's files to him), `voice.py` (speech to text with `transcribe-cli` and the GigaAM model
  under `~/.local`), `messages.py` (the conversation file), `processes.py` (what a thread left running),
  `notify.py` (`bb notify`: the board's own voice when its run is in trouble), `remote.py` (`Remote`, the
  one error that means the other side).

## State — `factory/state.py`

Every file under `state/` (gitignored), one line each with its schema and writer. A run is a directory
`state/runs/<started>/` — `run.json`, `tasks.json`, `intents.jsonl`, `messages.jsonl`, `events.jsonl`,
`keys/`, `costs.json` (what every finished thread cost: role, model, thinking, its tasks, seconds, turns,
items by type and the tokens bb recorded), and `workdir`, a symlink to the project the run worked on, where
its results are — and `state/current` is a symlink to the newest, the way the agents' tools find it.

## Workspace — `factory/core/workspace.py`

The run's project is a git repo; `.factory/` inside it holds one directory per agent and one worktree per
`code` task. Every agent directory links `.pi` back to the factory, and must be under pi's trusted paths.

## Timeline — `factory/core/events.py`, `factory/ui/`

The board appends an event to the run's `events.jsonl` as things happen: a task created, started, handed
off or canceled, a message sent, an agent started or stopped. `factory/ui/serve.py` serves the page that
replays it, live or after. See [../examples/](../examples/index.md) for the event form.

## One agent alone — `do.py`

`factory/core/solo.py` runs one agent on one task without a board and prints its handoff, its final text and
what it wrote to Mikhail. Never during a run: it points `state/current` at a run directory of its own.
