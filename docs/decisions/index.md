# Decisions

Plans in the order they were made; checkboxes show what was done.

- [split-orchestrator.md](split-orchestrator.md) — one service per class (`Tasks`, `Threads`, the loop), the timeline read from bb instead of tracked
- [workspace.md](workspace.md) — a working directory of its own per run, a git worktree per worker, the board merges
- [secretary.md](secretary.md) — the secretary: the only agent that talks to Mikhail, through Telegram, with a wait for his answer
- [imitator-test.md](imitator-test.md) — test runs with one imitator playing every worker and tester
- [events-model.md](events-model.md) — the event model of the timeline: task, message, agent
- [split-by-kind.md](split-by-kind.md) — the package split into roles, tools, core and ui; git; docs in OKF
- [own-tracker.md](own-tracker.md) — the board owns the tasks: agents append intents, the board folds them; bb's tracker goes, its threads stay
- [green-handoff.md](green-handoff.md) — a worker's handoff commits, merges master in and runs the project's check before it counts; created projects start with `AGENTS.md` and `docs/`
- [instagram-run-lessons.md](instagram-run-lessons.md) — what the first big run taught: parallel by default, handoffs that teach, a brief with context, conflicts not marked done, a review every quarter hour, the board lingers after the report
- [shipyard-run-lessons.md](shipyard-run-lessons.md) — what the night run shows while it runs: conflicts resolved instead of redone, files cut per area, canceled tasks that say where they went, master checked after every merge
- [before-the-next-run.md](before-the-next-run.md) — the night's lessons applied: the planner knows its tester, a drag recipe tried by hand, `amend_task` wakes the agent at work, a review the planner can fail, servers die with their threads
- [ios-kit-run.md](ios-kit-run.md) — the factory prepares its own iOS ground: skills tried and kept, a starter, the build-test-tap loop measured on this Mac, the kit is the deliverable
- [secretary-voice-and-files](secretary-voice-and-files.md) — the secretary hears Mikhail's voice messages (Beseda's transcribe-cli) and passes files both ways; plan, not built yet
- [skills-by-role](skills-by-role.md) — skills attached to the agents in sets per role, delivered through each agent's .pi/skills; the first is okf-knowledge-base
- [kits](kits.md) — a preset named in the run (kit=IOS): the project is seeded with the kit's skills and a Kit section in AGENTS.md, the planner gets the kit's brief before the goal; plan
- [stopped-agents](stopped-agents.md) — an agent whose turn failed or ended without a handoff is noticed, started again, and its task redone when it does not come back
- [secretary-planner-link](secretary-planner-link.md) — the secretary asks the planner how the work goes and comes back to Mikhail with the answer: `tell_secretary`, the report told apart by its status
