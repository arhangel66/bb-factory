import json
from pathlib import Path

import pytest

from factory.core import tracker as module
from factory.core.tracker import Tracker, write_intent

PLANNER, WORKER = "thr_planner", "thr_worker"


@pytest.fixture
def tracker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Tracker:
    monkeypatch.setattr(module, "INTENTS", tmp_path / "intents.jsonl")
    monkeypatch.setattr(module, "KEYS", tmp_path / "keys")
    (tmp_path / "intents.jsonl").write_text("")
    for n in (1, 2, 3):  # the keys the tests below create by hand are handed out already
        (tmp_path / "keys" / str(n)).mkdir(parents=True)
    return Tracker(tmp_path / "tasks.json", tmp_path / "intents.jsonl")


def create(key: str, priority: str = "high", blocked_by: list[str] = []) -> None:
    write_intent(PLANNER, "create", key=key, type="code", title=f"do {key}", description="## Motivation\nbecause",
                 priority=priority, blocked_by=blocked_by, parent=None)


def handoff(key: str) -> None:
    write_intent(WORKER, "handoff", key=key, outcome="ok", summary="done", text="all done")


def test_a_task_is_created_once(tracker: Tracker) -> None:
    create("FAB-1")
    create("FAB-1")

    applied = tracker.fold()

    assert [i["intent"] for i in applied] == ["create"]
    assert tracker.tasks["FAB-1"]["status"] == "todo"
    assert tracker.tasks["FAB-1"]["created_by"] == PLANNER


def test_a_handoff_closes_a_running_task(tracker: Tracker) -> None:
    create("FAB-1")
    tracker.fold()
    tracker.start("FAB-1", WORKER)

    handoff("FAB-1")
    tracker.fold()

    assert tracker.tasks["FAB-1"]["status"] == "done"
    assert tracker.tasks["FAB-1"]["handoffs"][0]["thread"] == WORKER


def test_a_task_canceled_while_running_stays_canceled_after_its_handoff(tracker: Tracker) -> None:
    create("FAB-1")
    tracker.fold()
    tracker.start("FAB-1", WORKER)
    write_intent(PLANNER, "cancel", key="FAB-1", why="not needed")

    handoff("FAB-1")
    applied = tracker.fold()

    assert tracker.tasks["FAB-1"]["status"] == "canceled"
    assert [i["intent"] for i in applied] == ["cancel", "handoff"]  # the board sees the handoff and drops the work


def test_a_second_handoff_is_ignored(tracker: Tracker) -> None:
    create("FAB-1")
    tracker.fold()
    tracker.start("FAB-1", WORKER)
    handoff("FAB-1")
    tracker.fold()

    handoff("FAB-1")

    assert tracker.fold() == []
    assert len(tracker.tasks["FAB-1"]["handoffs"]) == 1


def test_a_task_handed_back_takes_its_next_handoff(tracker: Tracker) -> None:
    create("FAB-1")
    tracker.fold()
    tracker.start("FAB-1", WORKER)
    handoff("FAB-1")
    tracker.fold()

    tracker.hand_back("FAB-1")
    handoff("FAB-1")
    applied = tracker.fold()

    assert [i["intent"] for i in applied] == ["handoff"]
    assert tracker.tasks["FAB-1"]["status"] == "done"
    assert len(tracker.tasks["FAB-1"]["handoffs"]) == 2


def test_priority_changes_only_while_the_task_waits(tracker: Tracker) -> None:
    create("FAB-1")
    create("FAB-2")
    tracker.fold()
    tracker.start("FAB-2", WORKER)

    write_intent(PLANNER, "priority", key="FAB-1", priority="urgent")
    write_intent(PLANNER, "priority", key="FAB-2", priority="urgent")
    tracker.fold()

    assert tracker.tasks["FAB-1"]["priority"] == "urgent"
    assert tracker.tasks["FAB-2"]["priority"] == "high"


def test_ready_waits_for_blockers_and_puts_urgent_first(tracker: Tracker) -> None:
    create("FAB-1", priority="medium")
    create("FAB-2", priority="urgent", blocked_by=["FAB-1"])
    create("FAB-3", priority="urgent")
    tracker.fold()

    assert [t["key"] for t in tracker.ready()] == ["FAB-3", "FAB-1"]

    tracker.start("FAB-1", WORKER)
    handoff("FAB-1")
    tracker.fold()

    assert [t["key"] for t in tracker.ready()] == ["FAB-2", "FAB-3"]


def test_a_line_still_being_written_waits_for_the_next_fold(tracker: Tracker) -> None:
    create("FAB-1")
    with tracker.intents_file.open("a") as file:
        file.write('{"intent": "create", "key": "FAB-2", "ti')

    tracker.fold()

    assert list(tracker.tasks) == ["FAB-1"]
    assert tracker.folded == 1


def test_a_copy_is_the_same_task_again_for_the_same_creator(tracker: Tracker) -> None:
    create("FAB-1", blocked_by=["FAB-0"])
    tracker.fold()
    tracker.start("FAB-1", WORKER)
    handoff("FAB-1")
    tracker.fold()

    copy = tracker.copy("FAB-1", "Redo of FAB-1: merge failed")

    assert copy["key"] == "FAB-4"
    assert copy["status"] == "todo" and copy["blocked_by"] == [] and copy["handoffs"] == []
    assert copy["created_by"] == PLANNER
    assert copy["description"].startswith("Redo of FAB-1")
    assert tracker.tasks["FAB-1"]["status"] == "canceled"  # its work is not in the project


def test_a_copy_takes_the_originals_place_and_waits_for_the_code_in_flight(tracker: Tracker) -> None:
    create("FAB-1")
    create("FAB-2")
    create("FAB-3", blocked_by=["FAB-1", "FAB-2"])
    tracker.fold()
    tracker.start("FAB-1", WORKER)
    tracker.start("FAB-2", "thr_other_worker")
    handoff("FAB-1")
    tracker.fold()

    copy = tracker.copy("FAB-1", "Redo of FAB-1: merge failed")

    assert copy["blocked_by"] == ["FAB-2"]  # not in parallel with what is still changing the project
    assert tracker.tasks["FAB-3"]["blocked_by"] == [copy["key"], "FAB-2"]
    assert tracker.ready() == []


def test_save_writes_the_whole_board(tracker: Tracker) -> None:
    create("FAB-1")
    tracker.fold()

    tracker.save()

    assert json.loads(tracker.tasks_file.read_text())["FAB-1"]["title"] == "do FAB-1"
    assert not tracker.tasks_file.with_suffix(".tmp").exists()


def test_an_intent_of_an_unknown_thread_is_a_stray(tracker: Tracker) -> None:
    create("FAB-1")
    write_intent("thr_of_an_earlier_run", "create", key="FAB-2", type="code", title="stray", description="",
                 priority="low", blocked_by=[], parent=None)

    applied = tracker.fold(known={PLANNER})

    assert [i["key"] for i in applied] == ["FAB-1"]
    assert list(tracker.tasks) == ["FAB-1"]
    assert [s["key"] for s in tracker.strays] == ["FAB-2"]
