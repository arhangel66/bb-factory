# Plan: the agreed event model in code

Model: `docs/examples/events-full.jsonl`. Three interactions: task, message, agent.

- [x] Orchestrator → board. `factory/board.py`: class `Board` is the loop; the bb tasks wrapper becomes `Tasks`.
  `construct.py`: `Board(config, tasks=Tasks(), threads=Threads()).run(goal)`.
- [x] No top task. The run is scoped by the project's next task number at start (`state/run.json`),
  which also records the planner thread. The goal reaches the planner as a message.
- [x] Messages live in `state/messages.jsonl` (`from`, `to`, `text`, `status`): the board writes the incoming
  goal (human → planner), the planner's new `report` tool writes the outgoing one (planner → secretary),
  which ends the run.
- [x] Handoff closes the task: `done` right away, `in_review` is gone. `outcome: ok | warning | failed`
  = green / yellow / red. The planner's `update_task` keeps only `todo` (reopen) and `canceled`.
- [x] `factory/timeline.py` emits the agreed form: `at, agent{role, model, imitator, thread}, kind, action,
  key, parent, text, status`. Sources: bb system comments, handoff comments, thread created/archived,
  messages file.
- [x] Prompts: planner ends with `report`, no `{key}`, no "update_task done"; imitator picks the outcome.
- [x] Verify: an imitator run ends on the planner's report; `python -m factory.timeline` matches the example.

Not in this step: the secretary and lead agents, diagrams (still say "orchestrator").

## Lead (done after the plan above)

- [x] `epic` label → `lead` role, `Config.lead`; handoffs wake the task's creator (lead of the epic or the planner).
- [x] pi extension: lead tools, automatic `parent`, board scoped to the lead's epic / the planner's top level.
- [x] `prompts/lead.md`; `type` field in the timeline.
- [x] Run with two leads: `state/run.log`, events via `uv run python -m factory.timeline`.

Still not in code: the secretary. Diagrams still say "orchestrator".
