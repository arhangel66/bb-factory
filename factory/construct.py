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
Build a local MVP of Instagram: a web app Mikhail starts with one command and opens in his browser.

Must work end to end, checked against the running app (HTTP requests or a headless browser), not by reading the code:
- sign up, log in, log out; password reset without e-mail: the reset link is shown on the page or printed to the console
- upload photos (jpeg/png) with a caption; my profile shows them as a grid; open a photo, edit its caption, delete it
- a feed of everyone's posts, newest first; open a post, like it, comment on it; a user's page from the feed
- follow / unfollow; when I follow someone, the feed shows their posts first
- seed data: a few demo users with photos and comments, so the feed is alive at the first start; the demo
  logins are in the README

Look: as close to the real Instagram as possible — layout, spacing, icons, the feed card, the profile grid,
the post page. Tailwind CSS for all styling (the CDN build is fine). Do not skimp on the polish.

Stack: Python, FastAPI, SQLite, server-rendered Jinja templates; `uv run` starts it, no build step, no Node.
Files under one project folder, a README with the start command, the URL and the demo logins.

How to run this: the goal is big — plan it as epics per area (auth, photos and profile, feed and comments,
look and polish), let the leads split them, and a test task that drives the running app after each area and one
for the whole thing at the end. Decide the details yourself. What only Mikhail can decide, gather into a
single `ask` task with a numbered list before the epics start, not one question at a time; he answers once.
The final report says the start command, the URL and the demo logins."""
    # run(task, real_config, Path.home() / "w/learning/factory-runs/instagram", slots=10)
    resume(real_config, slots=10)  # the Instagram run of 2026-09-19 20:26, done: Mikhail talks to it further
