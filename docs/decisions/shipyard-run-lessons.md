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
- [ ] Time budget on the goal: the run had 8 hours and spent 1.5 on the foundation; the planner's review
      should see the clock against the plan ("four epics still open at 23:50, five stages unstarted") and
      be allowed to cut stages
