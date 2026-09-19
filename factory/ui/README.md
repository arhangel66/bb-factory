# Timeline

A page that replays a run: lanes per agent, tasks as bars, handoffs and messages as marks, live while
the run goes and as a recording after.

![the timeline of a run](timeline.png)

```
uv run python -m factory.ui.serve      # http://localhost:8877/
```

The panel on the left lists the runs in `state/events/` (newest first) with the goal, how each ended and its
task count; the chosen file is re-read every few seconds.
`timeline.html` is the page, `support.js` its runtime (generated, do not edit).
To see it without a run of your own, copy `docs/examples/events.jsonl` into `state/events/`.
