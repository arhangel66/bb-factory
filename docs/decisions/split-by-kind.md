# Plan: split the factory by kind, drop what is dead, start git, document in OKF

## Why
`factory/board.py` holds the loop plus config, prompts, messages and helpers that `solo.py` and `timeline.py`
import from it; a role is defined in four places; `state/` paths are spread over four modules; `main.py`,
old plans and `save_roles()` (half-done, breaks `Board.start()`) are dead weight. No git, no docs index.

## 0. Git first — a safety net before anything moves
- [ ] `.gitignore`: `state/ .venv/ __pycache__/ .pytest_cache/ .ruff_cache/ .idea/ .DS_Store untracked/`
- [ ] `git init`, first signed commit of the tree as it is (`initial factory`)
- [ ] every step below is its own commit; tests green before each

## 1. Delete the dead
- [ ] `main.py` (a sketch, not valid Python)
- [ ] `save_roles()`, `ROLES` in board.py — replaced by step 3
- [ ] `untracked/scripts/events_v2.py`, `check_ask_task.py` (superseded by timeline.py and do.py)
- [ ] `docs/ideas.md` (the timeline exists), `.idea/` out of git
- Verify: `pytest -q` 11 passed, `python -c "import factory.construct, do"` ok

## 2. Layout — by kind
```
factory/
  roles/
    __init__.py     Role enum, LABEL_BY_ROLE, AgentConfig, Config = dict[Role, AgentConfig], prompt()
    prompts/        planner.md … wake.md, README.md
  tools/            what the board reaches the world with
    bb.py           bb(), Tasks, Threads
    telegram.py     Telegram
    messages.py     MESSAGES, write_message(), messages()
  core/
    board.py        Board: the loop only, plus blocked_by, board_lines, log
    workspace.py    Workspace, git()
    timeline.py     events()
    solo.py         run_agent_on_one_task()
  state.py          every path under state/: RUN_FILE, EVENTS, MESSAGES, ROLES, TOKEN_FILE, SETTINGS, TRUST
  ui/
    serve.py        the http server (was dashboard.py)
    timeline.html   was dashboard/board.dc.html
    support.js
    README.md       what it shows, how to run, a screenshot, demo data = docs/examples/events.jsonl
  construct.py      wiring and run()
.pi/extensions/factory.ts   the agents' tools; stays, pi reads extensions from .pi/ only
do.py               single-agent runs
```
- [ ] move files with `git mv`, fix imports, `PROMPTS` path, `Handler.directory`, the page's `/dashboard/` URL
- [ ] `Config` becomes `dict[Role, AgentConfig]`: `self.config[role]` instead of `getattr`; construct.py builds the dicts
- [ ] tests move with their modules; `pytest -q` 11 passed
- [ ] `uv run python -m factory.ui.serve` shows the old runs

## 3. One definition of a role
- [ ] `AgentConfig.tools: tuple[str, ...]` with the lists now hardcoded in `ROLE_TOOLS` (factory.ts)
- [ ] `Board.start()` writes `state/roles.json` `{role: [tool]}`; `solo.py` writes it too
- [ ] `factory.ts` reads roles.json instead of `ROLE_TOOLS`
- Verify: `do.py` `run_tester()` live — the tester has read/bash/…/handoff and nothing else; `pytest -q`

## 4. Docs in Open Knowledge Format
- [ ] `AGENTS.md` at the root with the "Project knowledge" section (given by Mikhail, verbatim)
- [ ] `docs/index.md` — entry point, one line per directory
- [ ] `docs/architecture/` — `index.md`, `overview.md` (roles, board, tools, state files: what today lives in
      module docstrings and prompts/README.md), `diagrams/factory.html`
- [ ] `docs/decisions/` — `index.md`, the five finished plans renamed by what they decided
      (`events-model.md`, `imitator-test.md`, `secretary.md`, `split-orchestrator.md`, `workspace.md`), this plan joins them when done
- [ ] `docs/examples/` — `index.md`, `events.jsonl`
- [ ] `factory/roles/prompts/README.md` → `docs/architecture/prompts.md`, the table stays

## Out of scope (say if wanted)
- renaming short loop variables in board.py / timeline.py (`t`, `c`, `m`)
- the UI as a separate repo or GitHub Pages
- Board's `forwarded` set surviving a restart (ponytail note stays)
