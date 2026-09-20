# The factory

A board of tasks, a planner that fills it, agents that take the tasks, and a secretary that talks to the
person whose factory it is. Give it a goal and a git repository; it plans the work, runs a dozen coding
agents in parallel worktrees, merges what they finish, asks you what only you can decide, and reports.

Every agent is a [bb](https://getbb.app) thread. The factory owns the board and the merges; bb owns the
threads and the models.

![the timeline of a run](factory/ui/timeline.png)

## A run

```python
# factory/construct.py
run(goal, power_real, Path.home() / "w/learning/meditate", slots=10, kit=IOS)
```

```
.venv/bin/python -m factory.construct        # the board; it ticks every 10 seconds until the report
.venv/bin/python -m factory.ui.serve         # the timeline of the run, live, on :8877
```

The board writes everything it knows to `state/runs/<started>/` — the tasks, the intents the agents
appended, the messages, the timeline, what each thread cost. `Board.resume()` picks a run back up after
its board is gone.

## How the work is split

| role | takes | threads |
|---|---|---|
| planner | the goal | one per run |
| lead | an `epic`, and splits it | one per epic |
| worker | a `code` task | one per task, in a git worktree of its own |
| tester | a `test` task | one per task, in the project itself |
| secretary | an `ask` task; the only one who writes to you | one per run |

Agents never edit a task. A task is created once and a change is an amendment appended to it, so no agent
can act on a stale view of the board. A worker's handoff merges its worktree into the project and runs the
project's own check before the task counts as done.

You are reached through Telegram: the secretary sends the questions and the screenshots, hears your voice
messages as text, and passes your files on. Everything else the factory decides for itself.

## What it has built

- `ios-kit` — the factory's own ground for iOS work: skills tried and kept, a starter, a measured
  build-test-tap loop on one Mac.
- Meditate — an iPhone app that plays guided meditations, with the titles transcribed from the audio, an
  icon family generated against a reference, and Apple Health. 41 tasks, six hours, 47 threads.

## Getting started

Needs [bb](https://getbb.app) on `PATH`, Python 3.13 and [uv](https://docs.astral.sh/uv/).

```
uv sync
.venv/bin/python -m pytest -q                # the check
```

The Telegram bot is optional and lives outside the repository: put `FACTORY_TELEGRAM_TOKEN=…` in
`state/telegram.env` and write to the bot once — whoever writes first owns the chat. Without it a run
works, and the secretary has nobody to ask.

`do.py` runs one agent on one task with no board, for trying a prompt.

## The documentation

`docs/` is an [OKF](https://github.com/inkeep/open-knowledge-skills) bundle — start at
[docs/index.md](docs/index.md) and follow the index files down.

- [architecture/](docs/architecture/index.md) — the parts and how a run goes through them
- [decisions/](docs/decisions/index.md) — every plan that shaped it, in the order it was made, with the
  boxes it ticked; the run-lesson files are the honest ones

## License

MIT. The skills under `.pi/skills/` and `.agents/skills/` are vendored from their own authors and keep
their own licenses.
