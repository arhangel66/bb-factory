import json
from pathlib import Path

from factory.core.board import Board
from factory.core.tracker import Tracker
from factory.core.workspace import Workspace
from factory.kits import Kit
from factory.roles import AgentConfig, Config, Model, Role, Thinking
from factory.state import RUN_FILE
from factory.tools.bb import Threads
from factory.tools.telegram import Telegram
from factory.tools.voice import Voice

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

# power run: the strongest planner, strong leads, a cheap tester that only drives and looks
PLANNER_POWER = AgentConfig(prompt=Role.planner, model=Model.gpt_6_astra, thinking=Thinking.high)
LEAD_POWER = AgentConfig(prompt=Role.lead, model=Model.gpt_5_6_sol, thinking=Thinking.high)
TESTER_POWER = AgentConfig(prompt=Role.tester, model=Model.kimi_k3, thinking=Thinking.medium)


def run(goal: str, config: Config, workdir: Path, slots: int, kit: Kit | None = None) -> None:
    # linger: after the report the planner and the secretary stay, Mikhail talks to the run in Telegram until Ctrl-C;
    # kit: the project is seeded with its skills and the planner hears its brief before the goal
    Board(config, tracker=Tracker(), threads=Threads(), workspace=Workspace(workdir), telegram=Telegram(voice=Voice()),
          slots=slots, linger=True).run(goal, kit)


def resume(config: Config, slots: int) -> None:
    # the run state/current points at, after its board has ended: Mikhail goes on talking to it in Telegram
    workdir = Path(json.loads(RUN_FILE.read_text())["workdir"])
    Board(config, tracker=Tracker(), threads=Threads(), workspace=Workspace(workdir), telegram=Telegram(voice=Voice()),
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
    power_real: Config = {
        Role.planner: PLANNER_POWER,
        Role.lead: LEAD_POWER,
        Role.worker: WORKER,
        Role.tester: TESTER_POWER,
        Role.secretary: SECRETARY,
    }

    # a small goal to try the factory on. The goals of the runs before this one — the ios kit, Meditate —
    # are in the git history, and what they taught is in docs/decisions/
    timer = """\
Build "Timer": one page that counts down, opened straight from the filesystem — a single HTML file with its
script and style inside, no server and no dependencies.

- Minutes and seconds are set, then start, pause and reset. The tab title shows the time left, so it can be
  read from another tab.
- At zero the page says so and makes a sound generated in the browser, never an audio file.
- The last duration is there again at the next visit.
- It looks deliberate on a phone and on a desktop: one accent colour, one typeface, and nothing that jumps
  as the digits change.

The first task writes `./check.sh` into the `## Check` section of AGENTS.md and it stays green from then on.
The tester drives the real page in a browser and says what a person would notice.
"""
    run(timer, real_config, Path.home() / "w/learning/timer", slots=3)
    # resume(power_real, slots=10)  # the run state/current points at, when its board is gone
