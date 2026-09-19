# Ideas (not yet in the plan)

## Timeline view

See what is happening now and what happened before: lanes per agent (planner, leads, workers,
tester, secretary), tasks as bars, handoffs and messages as marks on the lanes. Built from the
`tasks` + `messages` store, so no extra tracking is needed.

Visual style: Mikhail will show a reference later.

Prior art in bb-loop: `uv run bb-collect timeline` (`docs/capacity-timeline.md`) and the
`bb-plugin-capacity-timeline/` plugin — both reconstruct secretary and worker lanes from timestamps.
