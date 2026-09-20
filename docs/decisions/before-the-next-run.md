# Plan: what the night run asks for before the next one

## Why

The Shipyard run ([shipyard-run-lessons.md](shipyard-run-lessons.md)) ended yellow for reasons that were
the factory's, not the product's: the planner never restated a check its tester could not run, six rounds
were spent on a tester recipe nobody had tried, conflicts came from tasks that shared files and migration
numbers, servers outlived their threads, and the planner answered every review with "nothing" because the
wake carried nothing to judge. Mikhail asked for everything important to be fixed, and for one more thing:
a planner or a lead may change a task that is already running, and the agent doing it is woken with the
change — today the only way is cancel + create, which throws away the work and, for an epic, its lead.

## Steps

Prompts, in effect from the next spawn:

- [x] The planner knows what its tester can and cannot do (the `bsk` commands, no genuine pointer drag,
      no full-page capture), and is told that a check no tester can run is a planning fault: restate the
      gate, give the check to a worker as a code test, or drop it and say so. A residual blocks a gate only
      when it is a defect of the product.
- [x] The tester has a drag recipe that was tried by hand against Shipyard before it was written down:
      `bsk evaluate` dispatching pointer events on the card and the target column, named in the handoff as a
      synthetic drag.
- [x] The lead and the planner cut work so tasks do not share files: one module per area from the
      foundation, a migration named after its task key, never a sequence number.
- [x] The planner and the lead prompts give the exact relative path to the project's `docs/`
      (`../docs/index.md` and `../../docs/index.md`).
- [x] The worker and the tester are told the task text is all there is: no reading of other threads
      through `bb`.

Board, in effect from the next run:

- [x] `amend_task(key, text)` for the planner and the lead: the note is appended to the task; a task not
      started yet carries it in its brief, a running one has its agent woken with it (a lead for an epic,
      a worker or a tester for its task). `Tracker.apply` folds the `amend` intent, the board emits
      `amended` and tells the thread, the timeline shows it, the prompts say when to amend and when to
      cancel. "A task is never edited" goes.
- [x] The review the planner can fail: the wake lists every open epic with its age and its sub-task
      counts, what was returned or canceled since the last review, and asks for a verdict per epic.
- [x] The board kills what a thread started when it archives the thread: every process whose environment
      carries the thread's `BB_THREAD_ID`.
- [x] Docs: `overview.md`, `prompts.md`, the lessons' boxes.
