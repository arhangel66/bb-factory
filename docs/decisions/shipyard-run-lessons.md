# Lessons of the Shipyard night run

The overnight run of 2026-09-19 (started 22:13, 10 slots, a Linear-class issue tracker in five gated
stages) is watched while it runs; what it shows goes here as it happens, ideas unticked until they land.

## Seen

- Six merge conflicts in the first 90 minutes, all on `app/main.py`, `app/models/*`, `app/migrations/*`:
  every feature registers its routes and its tables in the same files. One conflict (FAB-23) turned four
  parallel tasks into a chain of four copies (FAB-40 ← FAB-41 ← FAB-42 ← FAB-43): the copy waits on every
  code task in flight, and each of those conflicts in its turn. The redo costs the whole task again
  (10-15 minutes of a worker) for a conflict that a person resolves in a minute.
- A canceled original reads as a broken dependency to the leads: three times a lead canceled and recreated
  its downstream tasks (FAB-34/36/38/39 → FAB-44/47/48, then FAB-49 at 00:28 with its tester already
  started) although the board had already pointed them at the copy. Nine of the cancellations so far are
  the leads' reaction to the seven of the board.
- The first worker under the new prompt (FAB-57, 00:08) ran `git merge master` twice before it handed
  off and merged clean in 12 minutes; the same task had cost 45 minutes and a conflict before.
- The handoffs of canceled tasks carried real findings (FAB-36 red: board filters lose the session;
  FAB-38 yellow) and nobody read them.
- The quarter-hour review is a rubber stamp: six wakes, six answers in three seconds ("no intervention is
  warranted"). The wake shows the planner only the top-level board — fifteen lines, four epics
  `in_progress` — not how long each epic has run, how many of its tasks are open, the conflicts and the
  cancellations since the last look, the time left. Nothing in it can look wrong.
- A false red at 23:54: the goal says "Tailwind CSS from the CDN", the foundation worker wrote into
  DESIGN.md "never fetch CSS from a third party at runtime", the tester of the board epic saw only
  DESIGN.md and failed the epic on the CDN request. The lead filed "Remove runtime Tailwind dependency"
  and a re-test that proves no third-party CSS. It cost five minutes, not the night: the foundation had
  written its own design system in `app.css` and the templates used a dozen Tailwind utilities, which the
  worker added as local helpers. But nobody could have stopped it: the planner has no channel to a lead,
  and a cancel by someone else does not wake the task's owner — the lead would wait for a handoff that
  never comes.
- The same worker spent its first minute reading twelve other threads' output through `bb thread output`
  (the bb CLI is on its path); the tester could not drag a card (`bsk` has no drag, a synthetic
  PointerEvent did not reach the card) and full-page screenshots failed — stage 3's "drag 10 of 10" has no
  tester today.
- The planner never restated a check its tester could not run. It learned of the missing drag at 03:57,
  from stage 3's epic handoff (it sees no tester handoffs and knows no tool); stages 4 and 5 were already on
  the board since 00:17, each with "a residual in KNOWN_ISSUES.md is a failed gate" copied from the goal,
  and a task is never edited. Two reviews and one new epic (FAB-140 at 05:20) went by with the gate as it
  was: the goal named KNOWN_ISSUES.md as the outlet for what fails, so the planner kept the requirement
  and recorded it as unverified — the literal reading, and the one its prompt asks for.
- The seventh conflict at 00:08 was add/add on `app/migrations/0003_demo_workspace.sql`: two parallel tasks
  numbered their migration 0003. It cost the realtime transport (45 minutes of a worker) and put five
  tasks behind its copy.
- The docs get written (13 files, 403 lines, updated by 9 of the first 12 merged tasks: an index, the
  architecture, file ownership per epic, API contracts, five ADRs). The planner read `docs/index.md` twice
  — at start, when the project did not exist yet, and after the foundation — and never a page behind it;
  a lead read the index three times and DESIGN.md once, after first failing on the path: the prompt says
  "the directory above `.factory/`", the lead's directory is one level deeper (`.factory/lead/FAB-2`).
- A cancel did not stop anyone: FAB-35 was canceled 13 seconds after its worker started (the lead had
  read FAB-28's handoff and wanted the palette written against it — the right move), and the worker went
  on for its whole task, to a handoff the board then dropped. Same for FAB-49's tester.
- Three reds on the phone look were the tool: `bsk emulate` on a big window lays the page out 390 wide in
  a strip at the left and the capture shows the whole desktop window, black beside the strip (FAB-54
  noticed, FAB-49 and FAB-81 failed on it; the app's phone layout was fine). Checked at 01:35: `bsk window
  resize` before `emulate` gives a true 780×1688 capture. The tester prompt now says so. It was not enough:
  the lead of FAB-3 spent rounds four to six (FAB-96/97, 99/100, 101/102, 02:16–02:45) on a drawer footer
  "absent at 390×844" from captures of 1000×1402 — the resize alone leaves the window at 500×701 CSS px
  and the emulation had not applied to the tab — while the same tester saw the footer at 390×600. By hand
  at 02:45, resize → navigate → emulate → capture: 780×1688, footer there. The lead had written the wrong
  procedure into the tasks as authoritative; nobody could tell it. The prompt now checks the capture's
  size and forbids a verdict on a capture of the wrong size.
- At 02:18 a merge failed on "your local changes would be overwritten": the FAB-94 worker had written its
  doc page into the project's own checkout through a relative path instead of its worktree, and the
  uncommitted file blocked the board's merge — the task was redone for it (FAB-98). Testers, who run in
  the project itself, leave the same kind of file: at 03:47 the untracked `KNOWN_ISSUES.md` and `reports/`
  of stage 1 blocked the merge of the estimate fix (FAB-112 → FAB-114). The board now commits what the
  tests left in the project before it merges; both times the stray files were handled by hand so the
  redo could land.
- Workers and testers leave their servers running after the handoff: at 05:35 four `uv run serve` of
  finished tasks (FAB-45, 99, 118, 134) still held ports under deleted worktrees, one of them 8000 — the
  URL the README names. Killed by hand before the morning.
- The result, 05:33: the planner reported after 7 h 19 min, 87 minutes before the deadline. 142 tasks
  (108 done, 34 canceled, 10 of them by conflicts), 20 epics, 127 threads, 26.9 agent-hours, 9.2 M tokens;
  139 commits, ~10 000 lines of app and tests, 73 tests green, five stages each run to its three rounds,
  KNOWN_ISSUES.md honest about what was not verified (pointer drag above all). The secretary's Telegram
  line was accurate.
- Master briefly did not start (the seed referenced a table a canceled task had created); a lead caught it
  from a red handoff and made FAB-50 "restore clean database startup". Nothing in the board checks that
  master runs after a merge.

## Ideas

- [x] Resolve a conflict instead of redoing the task (Mikhail: the worker owns its task up to the merge):
      the worker merges the main branch into its worktree before it hands off; when the board still cannot
      merge, the task goes back to the same worker with the conflict, its worktree kept, and its next
      handoff counts. The redo copy is only for a dead worker. The tool-side gate of
      [green-handoff.md](green-handoff.md) (a `handoff` that refuses until green) is still open
- [x] A task canceled while running stops its agent at once: the thread is archived and the worktree
      dropped in the same tick, not at the handoff that nobody reads
- [x] The board stops what a task started: a worker's or tester's server dies with its thread (kill the
      process group of the thread, or the tester is told to stop its server and the worker never to leave
      one)
- [x] (in the planner's and the lead's prompts, 2026-09-20) Cut the project so tasks do not share files: the foundation epic must leave one router module and one
      models module per area, registered by a loop, migrations named by task key or timestamp instead of a
      running number, and the lead names in every task the files it owns.
      Where the goal is written by us, say it in the goal; where it is not, the lead prompt says it
- [ ] The board says `canceled → redone as FAB-42` in the line, the wake and the timeline; the original
      carries `redone_as`, so a lead sees a dependency moved, not lost
- [x] (moot since a cancel stops the agent at once: no handoff comes) A canceled task's handoff reaches its lead as a note ("FAB-36 was canceled by a conflict; its tester
      found: …") instead of being dropped
- [ ] After every merge the board runs the project's check on master and, when it is red, creates a
      `code` task "master is broken after FAB-x" for the lead of that epic before anything else merges
- [ ] The goal's hard constraints live in the project before the first worker starts (`AGENTS.md`, from
      [green-handoff.md](green-handoff.md)): a worker's DESIGN.md cannot contradict them, a tester reads
      them with its task. The planner's `ask`-free night goal should also say which external assets are
      allowed by name
- [x] (as `amend_task`, for any task at work) The planner can write to a lead (`tell_lead(epic, text)`, delivered as a wake with the epic's
      floor), and a cancel by someone other than the owner wakes the owner with the reason
- [x] (by the prompt only) The worker's and the tester's `bb` is limited to what their tools need: no `bb thread output` of
      other threads; the prompt says the task text is all there is
- [x] Drag for the tester: a recipe that works (`bsk evaluate` dispatching pointerdown/move/up on the card
      and the target column, or a Python script over the app's own API as the fallback that is named as
      such); without it every drag check is "not seen"
- [x] The planner knows what its testers can do (the tester's tools and their limits, in the planner prompt
      or the review wake) and is told that a check no tester can run is a planning fault: restate the gate,
      give the check to a worker as a code test, or drop it and say so — never leave it red
- [x] The lead and the planner prompts give the exact relative path to the project's `docs/` from where
      each of them sits; the review wake names the docs pages changed since the last look, so the planner
      opens what moved instead of the index
- [x] A review the planner can fail: the wake carries, per open epic, its age and its open/done/canceled
      task counts, the conflicts and cancellations since the last review, and the time left against the
      goal's deadline; the prompt asks for a verdict per epic, not a sentence for the whole, and lets the
      planner cut stages when the clock says so
