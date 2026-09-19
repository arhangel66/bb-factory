# Decisions

Plans in the order they were made; checkboxes show what was done.

- [split-orchestrator.md](split-orchestrator.md) — one service per class (`Tasks`, `Threads`, the loop), the timeline read from bb instead of tracked
- [workspace.md](workspace.md) — a working directory of its own per run, a git worktree per worker, the board merges
- [secretary.md](secretary.md) — the secretary: the only agent that talks to Mikhail, through Telegram, with a wait for his answer
- [imitator-test.md](imitator-test.md) — test runs with one imitator playing every worker and tester
- [events-model.md](events-model.md) — the event model of the timeline: task, message, agent
- [split-by-kind.md](split-by-kind.md) — the package split into roles, tools, core and ui; git; docs in OKF
