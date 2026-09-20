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
Prepare "ios-kit": a kit for building iOS apps on this Mac fast, from the idea to a running, tested app, for
the agents of this factory and for Mikhail with Claude Code. The kit is this repository: `docs/` with what is
known, `.agents/skills/` with the skills that proved themselves, and a starter that makes a new app. Report
by 12:00 today; an honest partial report beats a late one.

The Mac: MacBook Pro M2 Max, macOS 26, Xcode 26.6 at /Applications/Xcode.app (Swift 6.3), iOS 26.2 and 26.4
simulator runtimes with iPhone devices, Homebrew, Node and npx, `axe` (simulator UI automation: describe-ui,
tap, type, swipe, button, screenshots through stream-video), `ios-deploy`. Nothing else for iOS. No `sudo`,
no Apple ID, no App Store, no physical device, no paid service: what needs one is a line for Mikhail in the
report. Everything else may be installed with brew or npm; what is installed is written down in `docs/` with
the version and the reason.

What the kit must do, proven not described:
1. Start: one command (`./new-app.sh <Name>` or the like) makes a new SwiftUI app in a directory without the
   Xcode GUI: the project, a unit test target, a UI test target, a `check.sh` that builds and runs both, and a
   `run.sh` that builds, installs and launches it on a simulator. Under 3 minutes from nothing to the app on
   screen, unattended.
2. Loop: change one line, see it on the simulator — the fastest way found on this Mac, measured in seconds and
   written down with what made it fast (a warm simulator, incremental builds, derived data, flags) and what
   was tried and was slower.
3. Test: unit tests and XCUITest run from the shell with readable output (a failure names the test and the
   line); a screenshot of any screen from the shell; `axe` taps, types and reads the screen of the running app
   — the recipes in a skill, each one tried.
4. Skills: search skills.sh (`npx skills find <words>` searches, `npx skills add <owner/repo>` installs; the
   `find-skills` skill in vercel-labs/skills says how) for iOS, SwiftUI, Swift testing, Xcode and simulator
   skills; install the candidates into `.agents/skills/`; keep one only after it was used in this run's work
   and made it better; rewrite what is nearly right; every reject is a line in `docs/` with the reason. Write
   skills of the kit's own for what nobody had: this Mac's loop, the starter, `axe`.
5. Proof: build one small real app with the kit — "Ledger": a list of expenses, add and edit on a second
   screen, a total, persisted across a relaunch; unit tests of the total, a UI test of add; a tester drives it
   on the simulator with `axe` and takes screenshots. Built with the kit and nothing else: what the kit lacked
   is fixed in the kit, not worked around in the app.
6. Knowledge: `docs/` in OKF holds it all — the Mac, the tools and versions, the loop with its numbers, the
   skills kept and rejected with why, how to start the next app in three lines. `./check.sh` in AGENTS.md is
   the kit's check: the first task writes it and it stays green.

How to run it: first a foundation task that maps the Mac and makes the starter work once; then in parallel
the loop, the tests and the skills, each in its own files; then Ledger with the kit; last, a test task that
clones the kit fresh into a new directory, follows `docs/` only, and gets to a running, tested new app. The
tester in this run has no browser and no `bsk`: a shell, `xcrun simctl`, `axe` and what the kit documents.
Write test tasks in those terms, and every check names its evidence: a screenshot path, a command and its
output. Agents run in parallel on one Mac: every agent boots a simulator device of its own (`xcrun simctl
create`, deleted when it is done), never a shared one, and keeps derived data in its own tree. Mikhail is
reachable through the secretary but slow to answer: decide yourself where you can.
"""
    run(task, real_config, Path.home() / "w/learning/ios-kit", slots=4)  # Xcode builds are heavy: four at once
    # resume(real_config, slots=10)  # re-attach to the run state/current points at, after its board is gone
