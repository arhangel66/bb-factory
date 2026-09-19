import json
from datetime import datetime
from pathlib import Path

from factory.bb import EVENTS, PROJECT, Tasks, Threads, run_info
from factory.board import AgentConfig, Board, Config
from factory.roles import Role
from factory.telegram import Telegram
from factory.timeline import events
from factory.workspace import Workspace

# test run: one imitator plays every worker and tester, one thread so its story stays consistent;
# the planner and the leads are real, they only create tasks
IMITATOR = AgentConfig(prompt=Role.imitator, mode="shared")

# real run: a fresh thread per task, each worker in a git worktree of the project
WORKER = AgentConfig(prompt=Role.worker)
TESTER = AgentConfig(prompt=Role.tester)
SECRETARY = AgentConfig(prompt=Role.secretary, mode="shared")  # one thread for the whole run: it is one person


def run(goal: str, config: Config, workdir: Path) -> None:
    tasks, threads, workspace, telegram = Tasks(), Threads(), Workspace(workdir), Telegram()
    started = datetime.now().strftime("%Y-%m-%d-%H%M")
    EVENTS.mkdir(exist_ok=True)

    def save() -> None:
        # every tick, so the dashboard follows the run; the final write closes the history
        history = EVENTS / f"{started}-{PROJECT}-{run_info()['number']}.jsonl"
        history.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events(tasks, threads)))

    Board(config, tasks=tasks, threads=threads, workspace=workspace, telegram=telegram).run(goal, after_tick=save)
    save()


if __name__ == "__main__":
    test_config = Config(
        planner=AgentConfig(prompt=Role.planner),
        lead=AgentConfig(prompt=Role.lead),
        worker=IMITATOR,
        tester=IMITATOR,
        secretary=IMITATOR,  # a test run reaches nobody's Telegram
    )
    real_config = Config(
        planner=AgentConfig(prompt=Role.planner),
        lead=AgentConfig(prompt=Role.lead),
        worker=WORKER,
        tester=TESTER,
        secretary=SECRETARY,
    )

    task = "напиши калькулятор в html странице с tailwindcss миленький, отдельным тестированием убедись что миленький"
    run(task, real_config, Path.home() / "w/learning/factory-runs/calculator")
