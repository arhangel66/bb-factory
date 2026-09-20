import json
from pathlib import Path

import pytest

from factory.core import board as board_module
from factory.core import events as events_module
from factory.core import tracker as tracker_module
from factory.core.board import Board
from factory.core.events import agent
from factory.core.tracker import Tracker, write_intent
from factory.kits import Kit
from factory.roles import AgentConfig, Config, Model, Role, Thinking
from factory.tools import messages as messages_module
from factory.tools.messages import write_message

PLANNER = "thr_planner"


class FakeThreads:
    def __init__(self):
        self.spawned: list[str] = []
        self.prompts: list[str] = []
        self.told: list[tuple[str, str]] = []
        self.archived: list[str] = []
        self.unarchived: list[str] = []
        self.dead: set[str] = set()
        self.modes: list[str] = []

    def project_for(self, workdir: Path) -> str:
        return "proj_fake"

    def spawn(self, title: str, prompt: str, model: Model, thinking: Thinking, path: Path, project: str) -> str:
        self.spawned.append(title)
        self.prompts.append(prompt)
        return f"thr_{len(self.spawned)}"

    def tell(self, thread: str, text: str, mode: str = "queue") -> None:
        self.told.append((thread, text))
        self.modes.append(mode)

    def archive(self, thread: str) -> None:
        self.archived.append(thread)

    def unarchive(self, thread: str) -> None:
        self.unarchived.append(thread)

    def status(self, thread: str) -> str:
        return "idle"

    def alive(self, thread: str) -> bool:
        return thread not in self.dead

    def usage(self, thread: str) -> dict:
        return {"turns": 1, "items": {"toolCall": 2}, "tokens": {"total": 10}}


class FakeTelegram:
    def replies(self) -> list[str]:
        return []

    def send(self, text: str, files: list[str] = ()) -> None:
        pass


class FakeWorkspace:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.kit = None
        self.merged: list[str] = []
        self.dropped: list[str] = []
        self.conflict: str | None = None

    def prepare(self, kit=None) -> None:
        self.kit = kit

    def agent_dir(self, name: str, role: Role) -> Path:
        return self.workdir / name

    def worktree(self, key: str) -> Path:
        return self.workdir / key

    def merge(self, key: str, title: str) -> str | None:
        self.merged.append(key)
        return self.conflict

    def drop(self, key: str) -> None:
        self.dropped.append(key)

    def main_branch(self) -> str:
        return "master"


@pytest.fixture
def board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Board:
    monkeypatch.setattr(events_module, "EVENTS", tmp_path / "events.jsonl")
    monkeypatch.setattr(board_module, "COSTS", tmp_path / "costs.json")
    monkeypatch.setattr(board_module, "RUN_FILE", tmp_path / "run.json")
    monkeypatch.setattr(messages_module, "MESSAGES", tmp_path / "messages.jsonl")
    monkeypatch.setattr(tracker_module, "INTENTS", tmp_path / "intents.jsonl")
    monkeypatch.setattr(tracker_module, "KEYS", tmp_path / "keys")
    (tmp_path / "events.jsonl").write_text("")
    (tmp_path / "intents.jsonl").write_text("")
    (tmp_path / "messages.jsonl").write_text("")
    (tmp_path / "keys").mkdir()
    (tmp_path / "keys/1").mkdir()  # FAB-1 below is handed out already
    config: Config = {role: AgentConfig(prompt=role, model=Model.gpt_5_6_terra, thinking=Thinking.medium)
                      for role in Role}
    board = Board(config, tracker=Tracker(tmp_path / "tasks.json", tmp_path / "intents.jsonl"),
                  threads=FakeThreads(), workspace=FakeWorkspace(tmp_path), telegram=FakeTelegram())
    board.planner = PLANNER
    board.agents[PLANNER] = agent("planner", Model.gpt_5_6_terra, PLANNER)
    board.costs[PLANNER] = {"role": "planner", "model": Model.gpt_5_6_terra, "thinking": Thinking.medium,
                            "started": "2026-09-19T20:00:00+04:00"}
    return board


def events(board: Board) -> list[dict]:
    return [json.loads(line) for line in events_module.EVENTS.read_text().splitlines()]


def create_and_dispatch(board: Board) -> None:
    write_intent(PLANNER, "create", key="FAB-1", type="code", title="do it", description="## Motivation\nbecause",
                 priority="high", blocked_by=[], parent=None)
    board.fold()
    board.dispatch_ready()


def handoff(board: Board, thread: str = "thr_1") -> None:
    write_intent(thread, "handoff", key="FAB-1", outcome="ok", summary="did it", text="all done")
    board.fold()


def test_a_task_goes_to_one_worker_once(board: Board) -> None:
    create_and_dispatch(board)

    board.dispatch_ready()

    assert board.threads.spawned == ["worker FAB-1 openai-codex/gpt-5.6-terra"]
    assert board.tracker.tasks["FAB-1"]["status"] == "in_progress"


def test_a_handoff_brings_the_work_home_and_wakes_the_planner(board: Board) -> None:
    create_and_dispatch(board)

    handoff(board)

    assert board.workspace.merged == ["FAB-1"]
    assert board.threads.archived == ["thr_1"]
    thread, text = board.threads.told[0]
    assert thread == PLANNER and "handoff (ok): did it" in text
    assert board.tracker.tasks["FAB-1"]["status"] == "done"


def test_a_task_canceled_while_running_stops_its_worker_at_once(board: Board) -> None:
    create_and_dispatch(board)
    write_intent(PLANNER, "cancel", key="FAB-1", why="not needed")

    board.fold()

    assert board.threads.archived == ["thr_1"] and board.workspace.dropped == ["FAB-1"]
    assert board.tracker.tasks["FAB-1"]["status"] == "canceled"
    handoff(board)  # the worker's last word, if it came through, changes nothing
    assert board.threads.archived == ["thr_1"] and board.workspace.merged == [] and board.threads.told == []


def test_a_conflict_goes_back_to_its_worker_who_hands_off_again(board: Board) -> None:
    board.workspace.conflict = "CONFLICT (content): app.py"
    create_and_dispatch(board)

    handoff(board)

    assert board.tracker.tasks["FAB-1"]["status"] == "in_progress"
    assert "FAB-2" not in board.tracker.tasks and board.threads.archived == []
    assert board.threads.told[-1][0] == "thr_1" and "CONFLICT (content): app.py" in board.threads.told[-1][1]
    assert "git merge master" in board.threads.told[-1][1]
    assert [e["action"] for e in events(board) if e["kind"] == "task"][-2:] == ["handed_off", "returned"]

    board.workspace.conflict = None
    handoff(board)

    assert board.tracker.tasks["FAB-1"]["status"] == "done" and board.threads.archived == ["thr_1"]
    assert board.workspace.merged == ["FAB-1", "FAB-1"]
    assert board.threads.told[-1][0] == PLANNER and "FAB-1" in board.threads.told[-1][1]


def test_a_conflict_of_a_dead_worker_makes_a_copy_for_the_same_creator(board: Board) -> None:
    board.workspace.conflict = "CONFLICT (content): app.py"
    create_and_dispatch(board)
    board.threads.dead.add("thr_1")

    handoff(board)

    copy = board.tracker.tasks["FAB-2"]
    assert copy["status"] == "todo" and copy["created_by"] == PLANNER
    assert copy["description"].startswith("Redo of FAB-1")
    assert board.threads.told == []  # the planner hears of the copy when it is done, not of the conflict
    canceled = [e for e in events(board) if e["kind"] == "task" and e["action"] == "canceled"]
    assert [(e["key"], e["text"]) for e in canceled] == [("FAB-1", "not merged, redone as FAB-2")]


def test_the_timeline_follows_the_task(board: Board) -> None:
    create_and_dispatch(board)
    handoff(board)

    tasks = [e for e in events(board) if e["kind"] == "task"]

    assert [e["action"] for e in tasks] == ["created", "started", "handed_off"]
    assert tasks[0]["agent"]["role"] == "planner"
    assert tasks[1]["agent"] == {"role": "worker", "model": "openai-codex/gpt-5.6-terra", "imitator": False, "thread": "thr_1"}
    assert tasks[2]["status"] == "green" and tasks[2]["text"] == "did it"


def test_the_planner_hears_the_kits_brief_before_the_goal(board: Board, tmp_path: Path,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(board_module, "start_run", lambda started, workdir: None)
    monkeypatch.setattr(board_module, "save_tools_by_role", lambda: None)
    kit = Kit("k", tmp_path / "kit", brief="the brief\n")

    board.start("the goal", kit)

    planner_prompt = board.threads.prompts[0]
    assert planner_prompt.index("the brief") < planner_prompt.index("the goal")
    assert board.workspace.kit is kit
    assert json.loads(board_module.RUN_FILE.read_text())["kit"] == "k"


def test_a_crashed_board_archives_every_agent_it_spawned(board: Board, monkeypatch: pytest.MonkeyPatch) -> None:
    create_and_dispatch(board)  # a worker thread is spawned
    board.alive.add(PLANNER)  # the fixture set the planner by hand, a real start spawns it
    monkeypatch.setattr(board, "start", lambda goal, kit=None: None)

    def crash() -> bool:
        raise KeyError("a bug, not an outage")
    monkeypatch.setattr(board, "tick", crash)

    with pytest.raises(KeyError):
        board.run("goal")

    assert sorted(board.threads.archived) == ["thr_1", PLANNER]
    assert board.alive == set()


def test_a_network_outage_is_retried_before_the_run_gives_up(board: Board, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(board, "start", lambda goal, kit=None: None)
    monkeypatch.setattr(board_module.time, "sleep", lambda seconds: None)
    ticks = iter([RuntimeError("bb: fetch failed"), OSError("no route to host"), False])

    def flaky() -> bool:
        outcome = next(ticks)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(board, "tick", flaky)

    board.run("goal")  # two failing ticks, then a normal end: no exception

    assert next(ticks, "spent") == "spent"


def test_an_outage_longer_than_the_limit_ends_the_run(board: Board, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(board, "start", lambda goal, kit=None: None)
    monkeypatch.setattr(board_module, "OUTAGE", board_module.timedelta(seconds=0))

    def down() -> bool:
        raise OSError("no route to host")
    monkeypatch.setattr(board, "tick", down)

    with pytest.raises(OSError):
        board.run("goal")


def test_a_stray_planner_of_an_earlier_run_creates_nothing(board: Board) -> None:
    write_intent("thr_of_an_earlier_run", "create", key="FAB-1", type="epic", title="foreign epic",
                 description="", priority="high", blocked_by=[], parent=None)

    board.fold()

    assert board.tracker.tasks == {}
    assert [e for e in events(board) if e["kind"] == "task"] == []


def test_an_archived_thread_leaves_its_cost(board: Board) -> None:
    create_and_dispatch(board)

    handoff(board)

    cost = json.loads(board_module.COSTS.read_text())["thr_1"]
    assert cost["role"] == "worker" and cost["thinking"] == "medium" and cost["tasks"] == ["FAB-1"]
    assert cost["turns"] == 1 and cost["tokens"] == {"total": 10} and cost["seconds"] >= 0
    assert PLANNER not in json.loads(board_module.COSTS.read_text())  # still running: not a cost yet


def test_a_resumed_board_lingers_for_mikhail_after_the_report(board: Board, tmp_path: Path,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    board_module.RUN_FILE.write_text(json.dumps({"goal": "goal", "started": "2026-09-19-202650",
                                                 "workdir": str(tmp_path), "planner": "thr_p", "secretary": "thr_s"}))
    create_and_dispatch(board)
    handoff(board)
    board.tracker.save()
    write_message(Role.planner, Role.secretary, "the report", status="green")
    resumed = Board(board.config, tracker=Tracker(tmp_path / "tasks.json", tmp_path / "intents.jsonl"),
                    threads=FakeThreads(), workspace=FakeWorkspace(tmp_path), telegram=FakeTelegram())
    monkeypatch.setattr(resumed, "serve", lambda: None)

    resumed.resume()

    assert resumed.threads.unarchived == ["thr_p", "thr_s"]
    assert resumed.planner == "thr_p" and resumed.secretary == "thr_s"
    assert resumed.tracker.tasks["FAB-1"]["status"] == "done"
    assert resumed.tick() is True  # the report is in, yet the board goes on
    assert resumed.threads.told == []  # nothing of the old run is delivered or dispatched again


def test_a_resumed_board_takes_back_the_agents_at_work(board: Board, tmp_path: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    board_module.RUN_FILE.write_text(json.dumps({"goal": "goal", "started": "2026-09-20-063122",
                                                 "workdir": str(tmp_path), "planner": "thr_p", "secretary": "thr_s"}))
    create_and_dispatch(board)  # FAB-1 → worker thr_1
    write_intent(PLANNER, "create", key="FAB-2", type="epic", title="the epic", description="## Motivation\nthe why",
                 priority="high", blocked_by=[], parent=None)
    board.fold()
    board.dispatch_ready()  # FAB-2 → lead thr_2
    board.tracker.save()
    resumed = Board(board.config, tracker=Tracker(tmp_path / "tasks.json", tmp_path / "intents.jsonl"),
                    threads=FakeThreads(), workspace=FakeWorkspace(tmp_path), telegram=FakeTelegram())
    monkeypatch.setattr(resumed, "serve", lambda: None)

    resumed.resume()

    assert {"thr_1", "thr_2"} <= resumed.alive
    assert resumed.leads == {"FAB-2": "thr_2"}
    handoff(resumed)  # thr_1 hands FAB-1 off to the new board
    assert resumed.tracker.tasks["FAB-1"]["status"] == "done"
    assert resumed.threads.told[0][0] == "thr_p"  # the planner is woken with the handoff, as before the gap


def test_the_brief_carries_the_epic_and_the_handoffs_before_the_task(board: Board) -> None:
    write_intent(PLANNER, "create", key="FAB-1", type="epic", title="the epic", description="## Motivation\nthe why",
                 priority="high", blocked_by=[], parent=None)
    board.fold()
    board.dispatch_ready()  # the lead, thr_1
    write_intent("thr_1", "create", key="FAB-2", type="code", title="first", description="scaffold",
                 priority="high", blocked_by=[], parent="FAB-1")
    board.fold()
    board.dispatch_ready()  # the worker, thr_2
    write_intent("thr_2", "handoff", key="FAB-2", outcome="ok", summary="scaffolded", text="Done — app.py\nNoticed — nothing")
    write_intent("thr_1", "create", key="FAB-3", type="code", title="second", description="build on it",
                 priority="high", blocked_by=["FAB-2"], parent="FAB-1")
    board.fold()

    board.dispatch_ready()

    brief = board.threads.prompts[-1]
    assert "Task FAB-3 «second»" in brief and "build on it" in brief
    assert "## Epic FAB-1 «the epic»\n## Motivation\nthe why" in brief
    assert "## Before this task: FAB-2 «first» (ok)\nDone — app.py\nNoticed — nothing" in brief


def test_the_planner_is_asked_to_review_every_quarter_hour(board: Board) -> None:
    board.last_review = board.last_review - board_module.REVIEW

    board.tick()

    thread, text = board.threads.told[-1]
    assert thread == PLANNER and text.startswith("Review: 15 minutes")
    assert board.tick() is True and len(board.threads.told) == 1  # not again a tick later


def test_an_amendment_wakes_the_agent_at_work_on_the_task(board: Board) -> None:
    create_and_dispatch(board)
    write_intent(PLANNER, "amend", key="FAB-1", text="drop the drag check")

    board.fold()

    thread, text = board.threads.told[-1]
    assert thread == "thr_1" and "drop the drag check" in text and "the planner adds" in text
    assert board.threads.modes[-1] == "steer"  # read in the middle of the work, not queued behind it
    assert [e["action"] for e in events(board) if e["kind"] == "task"][-1] == "amended"


def test_an_amendment_of_a_waiting_task_is_in_its_brief(board: Board) -> None:
    write_intent(PLANNER, "create", key="FAB-1", type="code", title="do it", description="## Motivation\nbecause",
                 priority="high", blocked_by=[], parent=None)
    write_intent(PLANNER, "amend", key="FAB-1", text="drop the drag check")
    board.fold()

    board.dispatch_ready()

    assert board.threads.told == []
    assert "## Added at" in board.threads.prompts[-1] and "drop the drag check" in board.threads.prompts[-1]


def test_the_review_names_every_open_epic_with_its_sub_tasks_and_what_went_wrong(board: Board) -> None:
    write_intent(PLANNER, "create", key="FAB-1", type="epic", title="build the board", description="## Motivation\nbecause",
                 priority="high", blocked_by=[], parent=None)
    board.fold()
    board.dispatch_ready()  # the lead is thr_1
    write_intent("thr_1", "create", key="FAB-2", type="code", title="cards", description="", priority="high",
                 blocked_by=[], parent="FAB-1")
    write_intent("thr_1", "create", key="FAB-3", type="code", title="columns", description="", priority="high",
                 blocked_by=[], parent="FAB-1")
    write_intent("thr_1", "cancel", key="FAB-3", why="columns are cards")
    board.fold()
    board.last_review = board.last_review - board_module.REVIEW

    board.tick()

    thread, text = board.threads.told[-1]
    assert thread == PLANNER and text.startswith("Review: 15 minutes")
    assert "- FAB-1 «build the board»: 0 minutes in, sub-tasks 1 in_progress, 1 canceled" in text  # the tick dispatched FAB-2
    assert "FAB-3 canceled by the lead: 'columns are cards'" in text
    assert "verdict per epic" in text
