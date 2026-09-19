# Lessons of the Shipyard night run

The overnight run of 2026-09-19 (started 22:13, 10 slots, a Linear-class issue tracker in five gated
stages) is watched while it runs; what it shows goes here as it happens, ideas unticked until they land.

## Seen

- Six merge conflicts in the first 90 minutes, all on `app/main.py`, `app/models/*`, `app/migrations/*`:
  every feature registers its routes and its tables in the same files. One conflict (FAB-23) turned four
  parallel tasks into a chain of four copies (FAB-40 ← FAB-41 ← FAB-42 ← FAB-43): the copy waits on every
  code task in flight, and each of those conflicts in its turn. The redo costs the whole task again
  (10-15 minutes of a worker) for a conflict that a person resolves in a minute.
- A canceled original reads as a broken dependency to the leads: twice a lead canceled and recreated its
  downstream tasks (FAB-34/36/38/39 → FAB-44/47/48) although the board had already pointed them at the
  copy. Eight of the fourteen cancellations so far are the leads' reaction to the six of the board.
- The handoffs of canceled tasks carried real findings (FAB-36 red: board filters lose the session;
  FAB-38 yellow) and nobody read them.
- The quarter-hour review is a rubber stamp: six wakes, six answers in three seconds ("no intervention is
  warranted"). The wake shows the planner only the top-level board — fifteen lines, four epics
  `in_progress` — not how long each epic has run, how many of its tasks are open, the conflicts and the
  cancellations since the last look, the time left. Nothing in it can look wrong.
- A false red at 23:54: the goal says "Tailwind CSS from the CDN", the foundation worker wrote into
  DESIGN.md "never fetch CSS from a third party at runtime", the tester of the board epic saw only
  DESIGN.md and failed the epic on the CDN request. The lead filed "Remove runtime Tailwind dependency"
  and a re-test that proves no third-party CSS; a worker is now rewriting every Tailwind class by hand.
  Nobody could stop it: the planner has no channel to a lead, and a cancel by someone else does not wake
  the task's owner — the lead would wait for a handoff that never comes.
- The same worker spent its first minute reading twelve other threads' output through `bb thread output`
  (the bb CLI is on its path); the tester could not drag a card (`bsk` has no drag, a synthetic
  PointerEvent did not reach the card) and full-page screenshots failed — stage 3's "drag 10 of 10" has no
  tester today.
- Master briefly did not start (the seed referenced a table a canceled task had created); a lead caught it
  from a red handoff and made FAB-50 "restore clean database startup". Nothing in the board checks that
  master runs after a merge.

## Ideas

- [ ] Resolve a conflict instead of redoing the task: keep the task's branch, spawn a worker on it with the
      conflict text and one job — merge master in, resolve, run the check, hand off. The redo copy stays
      as the fallback when the resolution fails. Cheaper still: the worker merges master before its handoff
      ([green-handoff.md](green-handoff.md)), so the board's merge is a fast-forward most of the time
- [ ] Cut the project so tasks do not share files: the foundation epic must leave one router module and one
      models module per area, registered by a loop, and the lead names in every task the files it owns.
      Where the goal is written by us, say it in the goal; where it is not, the lead prompt says it
- [ ] The board says `canceled → redone as FAB-42` in the line, the wake and the timeline; the original
      carries `redone_as`, so a lead sees a dependency moved, not lost
- [ ] A canceled task's handoff reaches its lead as a note ("FAB-36 was canceled by a conflict; its tester
      found: …") instead of being dropped
- [ ] After every merge the board runs the project's check on master and, when it is red, creates a
      `code` task "master is broken after FAB-x" for the lead of that epic before anything else merges
- [ ] The goal's hard constraints live in the project before the first worker starts (`AGENTS.md`, from
      [green-handoff.md](green-handoff.md)): a worker's DESIGN.md cannot contradict them, a tester reads
      them with its task. The planner's `ask`-free night goal should also say which external assets are
      allowed by name
- [ ] The planner can write to a lead (`tell_lead(epic, text)`, delivered as a wake with the epic's
      floor), and a cancel by someone other than the owner wakes the owner with the reason
- [ ] The worker's and the tester's `bb` is limited to what their tools need: no `bb thread output` of
      other threads; the prompt says the task text is all there is
- [ ] Drag for the tester: a recipe that works (`bsk evaluate` dispatching pointerdown/move/up on the card
      and the target column, or a Python script over the app's own API as the fallback that is named as
      such); without it every drag check is "not seen"
- [ ] A review the planner can fail: the wake carries, per open epic, its age and its open/done/canceled
      task counts, the conflicts and cancellations since the last review, and the time left against the
      goal's deadline; the prompt asks for a verdict per epic, not a sentence for the whole, and lets the
      planner cut stages when the clock says so
