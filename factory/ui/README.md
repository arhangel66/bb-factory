# Timeline

A page that replays a run: lanes per agent, tasks as bars, handoffs and messages as marks, live while
the run goes and as a recording after.

![the timeline of a run](timeline.png)

```
uv run python -m factory.ui.serve      # http://localhost:8877/
```

The panel on the left lists the runs in `state/runs/` (newest first) with the goal, how each ended and its
task count; the chosen run's `events.jsonl` is re-read every few seconds. Above the lanes, the chosen run's
project: its folder (`открыть папку` opens it in Finder through `/open/<run>`), and every `command` of the
secretary's last report as a button that copies `cd <folder> && <command>` for a terminal.
A click on a task row opens its description and handoff; an epic row folds its sub-tasks;
`◀ прогоны` hides the runs panel to give task titles room.
`timeline.html` is the page, `support.js` its runtime (generated, do not edit).
To see it without a run of your own, copy `docs/examples/events.jsonl` into `state/runs/example/`.
