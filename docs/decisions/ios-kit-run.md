# The ios-kit run

Mikhail wants the factory to prepare its own ground for iOS work: find and try the skills, set the Mac up
to build, test and tap an app from the shell, measure the loop, and leave a kit behind that starts a new
iOS app fast — for the factory's agents and for him with Claude Code. Run on 2026-09-20, from about 06:30,
report by 12:00.

## What is different from a product run

- The deliverable is the repository itself: `docs/`, `.agents/skills/`, a starter script, plus one small
  proof app built with the kit. Not a product.
- The tester has no browser: `xcrun simctl`, `axe` (simulator taps, typing, screen reading, screenshots)
  and the shell. The goal says so; the tester prompt's `bsk` recipes go unused.
- Agents install things on the Mac (brew, npm) but have no `sudo`, Apple ID or device; what needs one is
  a line in the report.
- Agents share one Mac: each boots its own simulator device and keeps derived data in its own tree.

## Before the run

- [x] The lingering Shipyard board stopped (SIGINT: it archives its agents), its stray-commit loop stopped.
- [x] `~/w/learning/ios-kit` seeded by hand — `AGENTS.md` (OKF docs, skills in `.agents/skills`,
  `.claude/skills` a symlink to it, `./check.sh` as the check), `docs/index.md` — and committed; the
  [green-handoff](green-handoff.md) template that would do this is still not built.
- [x] The goal in `factory/construct.py`, workdir `~/w/learning/ios-kit`, 4 slots (Xcode builds are heavy).
  Mikhail's global gitignore hides `AGENTS.md` and `.claude/`: both force-added, tracked from now on.
- [x] Launched: the board in the background with its log in `untracked/run-ios-kit.log`, the timeline on
  port 8877. A false start first: the edit of the goal left the Shipyard text after the new one; killed
  within a minute, its two threads archived, its run directory removed. A board started in the background
  ignores SIGINT (the shell starts background jobs that way): it is stopped with SIGTERM and its planner
  and secretary are archived by hand, `bb thread archive <id>` from `run.json`.

## After the run

- [ ] Lessons into `shipyard-run-lessons.md` or a file of their own: what the planner did with a tester it
  had never been told about, whether the skills reached the agents (pi reads `.agents/skills` from the
  cwd up to the git root — a worktree is its own root, so a skill reaches a worker only once merged into
  its branch).
