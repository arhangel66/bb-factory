# Plan: a worker hands off green — committed, master merged in, the check passed

## Why

Today the finish belongs to the board: after the handoff it commits the worktree, merges `--no-ff`, and a
conflict throws the work away — a copy of the task goes to a fresh worker who does it all again
([workspace.md](workspace.md)). The worker itself never runs anything as a gate: "check your work runs" is
a wish in the prompt. A `failed` handoff is merged like an `ok` one. The tester leaves its tests
uncommitted in the project. And a project the factory creates has no `AGENTS.md`, no `docs/`, nothing that
says how to check it.

Mikhail wants the finish to be the worker's, with the fewest steps: work done ⇒ a commit exists, master is
merged in, the project's check is green — and when something breaks, the same worker fixes it instead of
a redo from scratch. Every project the factory makes keeps its knowledge the way this one does (OKF).

## Model

**One tool call is the whole finish.** A worker's `handoff` refuses until the work is green; every refusal
says what to do, and the next call picks up where it stopped:

| step, in the worktree | on failure the tool returns |
|---|---|
| `git add -A && git commit -m "<key> <title>"` — also completes a merge in progress | `git diff --cached --check` finds a leftover conflict marker: the files, "resolve and call handoff again" |
| `git merge <main>` — master into the branch, the conflict stays in the files | the conflicting files: "resolve, then call handoff again" |
| the project's check: the command in the fenced block under `## Check` in the project's `AGENTS.md` | no such section: "add tests and their command to AGENTS.md"; a failing one: the last 40 lines, "fix and call handoff again" |
| the intent is written | — |

`failed` skips the merge and the check: the attempt is committed on the branch, the intent says why, nothing
of it lands in the project. `warning` goes through every gate like `ok`.

The logic lives in Python, `factory/core/finish.py` — `finish(worktree, key, title) -> str | None`, the
refusal text or None — and the tool calls it as a subprocess, so it is tested with pytest and the extension
stays a thin caller. The board's merge remains as it is minus the commit: master is already in the branch,
so the merge is trivial; the race when master moved between the two goes back to the same worker with the
conflict (done 2026-09-20, `Board.bring_home`), the copy only when the worker is dead.

**The tester commits too**: its `handoff` runs `git add -A && git commit -m "<key> <title>"` in the project
itself. Nothing finished is left uncommitted.

**A created project starts with its knowledge**: `Workspace.prepare()` writes `AGENTS.md` and
`docs/index.md` from `factory/roles/templates/` into a project that has no `AGENTS.md`, and commits them.
The template says what this repo's does — knowledge in `docs/` in OKF, commit every finished step — plus
an empty `## Check` section the first worker fills with the first tests. The worker prompt tells it to
update the document its change touches and to give a new part a document and an index line.

## Steps

- [ ] `factory/core/finish.py`: `finish()` as above, `main_branch(worktree)` from `git worktree list`,
  `check_command(project)` from `AGENTS.md`. Tests: green work passes; a conflict refuses with the files and
  leaves the merge for the worker; a leftover marker refuses; a failing check refuses with its output; no
  `## Check` refuses; the second call after a fix passes and the branch has master merged in.
- [ ] `.pi/extensions/factory.ts`: a worker's `handoff` runs `finish` before writing the intent and returns
  its refusal as the tool result; a tester's commits the project. `failed` commits and writes the intent.
- [ ] `factory/core/workspace.py`: `merge()` no longer commits; `prepare()` seeds `AGENTS.md` and
  `docs/index.md` from `factory/roles/templates/` when the project has no `AGENTS.md`. Tests.
- [ ] `factory/core/board.py`: `bring_home` merges `ok` and `warning`, drops the worktree of `failed`. Test.
- [ ] Prompts: `worker.md` — you finish through `handoff`, it commits, merges master in and runs the check;
  resolve what it reports and call it again; keep `docs/` current, keep `## Check` true; `tester.md` — your
  tests are committed by `handoff`. `docs/architecture/overview.md`, `prompts.md`, this file's index line.
- [ ] `AGENTS.md` of this repo: `## Check` with the pytest command, so it is what its own tool would read.
- [ ] A real run of a small goal in a fresh workdir: one commit per task, `## Check` filled, `docs/` kept,
  a conflict induced by two tasks on one file resolved by the worker, not redone.

## Not in this step

A release. No project has one yet; when one does, it is a `## Release` section next to `## Check`, run by the
board after the planner's report — the same shape, one more gate. Killing a worker that never gets green:
the planner cancels it after the heartbeat shows it stuck.
