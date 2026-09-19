# Plan: a working directory of its own, worktrees per worker

## Why
Every thread runs in `ENVIRONMENT` — the factory's own checkout — and workers are told to write into
`workspace/`. So the run has no project of its own, two parallel workers edit the same files, and nothing
records what one task changed.

## The constraint that shapes everything
`pi` reads `.pi/` from its cwd and never walks up (`join(cwd, ".pi")`, `dist/migrations.js:234`).
No `.pi/extensions/factory.ts` in the cwd = no `create_task`, no `handoff`, no factory at all.
So every agent directory needs a `.pi` symlink back to this repo, and `factory.ts` must stop reading
`state/run.json` by a relative path.

Two probe threads settled it (both spawned with `--environment <path>`, then archived):

| workdir | tools the thread got |
|---|---|
| `/tmp/factory-probe` | `read, bash, edit, write, update_environment_directory, notify, …` — the extension was skipped |
| `/Users/mikhail/w/learning/factory-probe` | `read, bash, edit, write, grep, find, ls, handoff` — the worker role, as spawned |

The difference is `~/.pi/agent/trust.json` (`{"/Users/mikhail": true}`): outside a trusted path `pi` silently
ignores the project's `.pi`, tools and all. **The workdir must live under a trusted path** — and the symlink
does work, so `.pi` need not be copied.

## Layout
```
<workdir>/                     # given to run(); the project, git repo, work lands on its default branch
  .factory/                    # added to .git/info/exclude — local, the project's .gitignore stays clean
    planner/                   # cwd of the planner, the leads and the imitator: .pi symlink, no code
    work/FAB-32/               # worker worktree, branch FAB-32, removed when the task is merged
```
Tester works in `<workdir>` itself: it checks the integrated state, not one task's branch.

## Steps

- [x] `Config.workdir: Path` and `Threads.spawn(..., path)` → `--environment <path>` (bb takes a bare path
      as an unmanaged workspace). Delete the `ENVIRONMENT` constant.
- [x] `factory/workspace.py` — everything git, ~40 lines:
  - `prepare(workdir)`: refuse a workdir outside every path in `~/.pi/agent/trust.json` — the agents would
    start with no factory tools and nothing would say why; mkdir;
    `git init` + `git commit --allow-empty -m init` when there is no repo
    (a worktree cannot be cut from a repo without HEAD); `.factory/` and `/.pi` into `.git/info/exclude`;
    a `.pi` symlink in `<workdir>` for the tester and in `.factory/planner/`.
  - `worktree(workdir, key)`: `git worktree add .factory/work/<key> -b <key>`, `.pi` symlink, returns the path.
  - `merge(workdir, key, title)`: commit everything in the worktree for the worker
    (`git add -A && git commit -m "<key> <title>"`), `merge --no-ff` into the default branch,
    `worktree remove`. Returns the conflict text or None.
- [x] `Board.dispatch` asks `workspace` for the path per role: worker → a fresh worktree, tester → `workdir`,
      everyone else → `.factory/planner`.
- [x] `Board.forward_handoffs` merges the worker's branch before waking the planner. Conflict → the task goes
      back to `todo` with the conflict text in the description, next dispatch cuts a fresh worktree from the
      updated branch. The worker redoes the task; nobody resolves conflicts by hand.
- [x] `factory.ts`: `state/` paths absolute, resolved through the cwd's own symlink
      (`join(realpathSync(".pi"), "..")` — it points back at this checkout from wherever the agent runs).
- [x] `prompts/worker.md`, `prompts/tester.md`: "the project lives in `workspace/`" → "the current directory
      is the project; the worker's is a git worktree of its task, do not commit — the board does it".

## Verify
- [x] `bb thread spawn --environment <dir>` outside the project — the thread starts in that directory and,
      under a trusted path, gets its role's factory tools.
- [x] `tests/test_workspace.py` — a repo with a commit, an untrusted workdir refused, work merged into the
      project with the agent's `.pi` left out of it, a conflict back as text with the project clean.
- [ ] A real run against a fresh `<workdir>`: `git log` has one commit per code task, `git worktree list` is
      clean at the end. The imitator run does not reach this — a shared imitator gets no worktree.

## Left out
- No integration agent, no rebase, no conflict resolution: a conflict is a redone task.
- The lead gets no directory of its own — leads write no files.
- No cleanup of `.factory/` between runs; `<workdir>` is one run's project.
- `<workdir>` and every worktree get a `.pi` symlink, excluded locally so it never lands in the project.
- Every path spawned into becomes a bb environment of its own, so a run leaves one per worktree behind.
  Clean them up by hand (`bb environment list` / `delete`) until they get in the way.
