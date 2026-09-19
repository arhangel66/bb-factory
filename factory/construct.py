import json
from pathlib import Path

from factory.core.board import Board
from factory.core.tracker import Tracker
from factory.core.workspace import Workspace
from factory.roles import AgentConfig, Config, Model, Role, Thinking
from factory.state import RUN_FILE
from factory.tools.bb import Threads
from factory.tools.telegram import Telegram

# who runs on what: every agent names its model and how long it thinks, nothing is left to a default
PLANNER = AgentConfig(prompt=Role.planner)
LEAD = AgentConfig(prompt=Role.lead)

# test run: one imitator plays every worker and tester, one thread so its story stays consistent;
# the planner and the leads are real, they only create tasks
IMITATOR = AgentConfig(prompt=Role.imitator, model=Model.gpt_5_6_terra, thinking=Thinking.low, mode="shared")

# real run: a fresh thread per task, each worker in a git worktree of the project
WORKER = AgentConfig(prompt=Role.worker, model=Model.gpt_5_6_luna, thinking=Thinking.high)
TESTER = AgentConfig(prompt=Role.tester)
# one thread for the whole run: it is one person
SECRETARY = AgentConfig(prompt=Role.secretary, mode="shared")


def run(goal: str, config: Config, workdir: Path, slots: int) -> None:
    # linger: after the report the planner and the secretary stay, Mikhail talks to the run in Telegram until Ctrl-C
    Board(config, tracker=Tracker(), threads=Threads(), workspace=Workspace(workdir), telegram=Telegram(),
          slots=slots, linger=True).run(goal)


def resume(config: Config, slots: int) -> None:
    # the run state/current points at, after its board has ended: Mikhail goes on talking to it in Telegram
    workdir = Path(json.loads(RUN_FILE.read_text())["workdir"])
    Board(config, tracker=Tracker(), threads=Threads(), workspace=Workspace(workdir), telegram=Telegram(),
          slots=slots).resume()


if __name__ == "__main__":
    test_config: Config = {
        Role.planner: PLANNER,
        Role.lead: LEAD,
        Role.worker: IMITATOR,
        Role.tester: IMITATOR,
        Role.secretary: IMITATOR,  # a test run reaches nobody's Telegram
    }
    real_config: Config = {
        Role.planner: PLANNER,
        Role.lead: LEAD,
        Role.worker: WORKER,
        Role.tester: TESTER,
        Role.secretary: SECRETARY,
    }

    task = """\
Build "Shipyard": a local issue tracker in the class of Linear (linear.app), then harden it through five gated
stages. Nobody is available tonight: no `ask` tasks, decide everything yourself. Report only when stage 5 is
green or its retry budget is spent, and in any case by 07:00 — an honest partial report beats a late one.

Stack, hard: Python 3.12, FastAPI, SQLite, Jinja templates, Tailwind CSS from the CDN, vanilla JS. No Node, no
build step, no JS frameworks, no external APIs, fonts or images; icons and avatars are inline SVG. `uv run serve`
starts it from a clean checkout with no manual step. A README with the start command, the URL and the demo logins.

Design target: Linear. Dark by default, muted neutral palette with one accent, 6px radius, 13-14px text, 1px
subtle borders, no gradients. The first code task writes DESIGN.md (colors, spacing scale, type, component
rules); every UI task follows it. Drag uses pointer events, not the HTML5 drag API. Every JS error shows a
toast: the tester sees the screen, not the console.

Product, exactly this and nothing more:
1. Email/password auth with sessions and logout; 8 seeded users with SVG initial avatars.
2. One workspace, 3 projects; sidebar: projects, My Issues, search, theme toggle.
3. Issue: identifier (SHP-123), title, markdown-lite description, status (Backlog / Todo / In Progress / In Review /
   Done / Canceled), priority (Urgent / High / Medium / Low, with icons), assignee, labels, estimate, due date.
4. Board view: a column per status, cards dragged between and within columns; the order persists.
5. List view grouped by status; status, priority and assignee edited inline through dropdowns, no page change.
6. Issue page: title and description edited inline, comments, an activity log of every change (who, what, when).
7. Command palette on Cmd/Ctrl-K: fuzzy-find any issue and jump, create an issue, change its status.
8. Shortcuts: c create, j/k move the selection, Enter open, ? a help overlay. None fire while typing in a field.
9. Real-time: every change is broadcast over websockets with auto-reconnect; every open tab converges within a
   second without reload and shows a toast ("Maya moved SHP-41 to Done").
10. Filters (assignee, label, priority, text) live in the URL; a reload restores the exact view.
11. Dark theme by default, a light theme toggle persisted per user; both themes pass stage 2.
12. Seed: 8 users, 3 projects, ~140 issues with believable titles from one fictional SaaS backlog, 300+ comments,
    activity spread over 8 weeks. No lorem ipsum, no "test", no placeholders anywhere. Idempotent, under 30 s.
13. "Reset demo data" in the sidebar footer, with confirmation, reseeds without a restart.
14. Empty states, hover states, visible focus rings, inline validation, a styled 404. No control that does nothing.

How to run it: first the build — epics per area (foundation and design system; issues, board and list; issue
page and activity; palette, shortcuts and real-time; seed and demo), parallel where they do not share files,
each tested by its lead against the running app. Then the five stages, one after another, each an epic whose
lead has a tester run the checklist against the running app, files one fix task per failure, and re-runs the
whole checklist after the fixes. Three rounds per stage at most; what still fails goes into KNOWN_ISSUES.md,
never marked as passed. No new features after the build; no task titled "polish" or "improve" without a
binary check the tester runs. The tester writes screenshots and results under reports/stage-N/.

Stage 1, adversarial function: every form submitted empty, with 10k characters, with emoji, with
<script>alert(1)</script> (rendered escaped); 20 random URLs give the styled 404, never a 500; the same issue
edited from two tabs; every mutation survives a reload; the server restarted mid-session (session survives,
websocket reconnects); zero tracebacks in the server log for the whole stage.
Stage 2, look against Linear: screenshots of login, board, list, issue page, palette open, empty project, 404 at
1440×900 and 390×844, dark and light; no default-browser element, no horizontal scroll or overlap at 390,
readable contrast in both themes, a hover state on everything interactive; each visible difference from Linear
is a fix task, spacing and type included.
Stage 3, interaction and real-time: drag succeeds 10 of 10 at slow and fast speeds and the order persists;
two windows side by side — a card moved in one moves in the other within a second, with a toast; the palette
finds "SHP-" plus a number and fuzzy-matches titles; every shortcut works and is inert inside fields; a change
made while the server is down rolls back with an error toast; the browser console is clean for the whole pass.
Stage 4, data and demo: reseed from scratch under 30 s; every page rich under seed data; the board page under 25
queries (an X-Query-Count header) and every page under 200 ms locally; DEMO.md — the 3-minute click path: two
windows, drag a card, Cmd-K, c to create, theme toggle, phone width, reset demo — run end to end.
Stage 5, cold start: delete the database, fresh checkout, `uv run serve` starts unaided; the test suite green;
stages 1-4 re-run green; README exact; the final report lists every check with its evidence path and copies
KNOWN_ISSUES.md verbatim. Only then report: the start command, the URL, the demo logins, what is known to be
open."""
    run(task, real_config, Path.home() / "w/learning/factory-runs/shipyard", slots=10)
    # resume(real_config, slots=10)  # re-attach to the run state/current points at, after its board is gone
