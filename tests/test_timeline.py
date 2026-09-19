import pytest

from factory import timeline as module
from factory.timeline import events

LEAD, WORKER = "thr_lead", "thr_worker"


class FakeTasks:
    def __init__(self, shown: dict):
        self.shown = shown

    def all(self) -> list[dict]:
        return [s["task"] for s in self.shown.values()]

    def show(self, key: str) -> dict:
        return self.shown[key]


class FakeThreads:
    def show(self, thread: str) -> dict:
        return {"title": "worker gpt", "createdAt": 1789820700000, "archivedAt": None}


def comment(at: str, body: str, thread: str | None = None) -> dict:
    return {"createdAt": at, "body": body, "threadId": thread}


@pytest.fixture
def one_task(monkeypatch: pytest.MonkeyPatch) -> FakeTasks:
    monkeypatch.setattr(module, "messages", lambda: [])
    monkeypatch.setattr(module, "run_info", lambda: {"number": 1, "planner": LEAD})
    shown = {"FAB-1": {
        "task": {"id": "t1", "key": "FAB-1", "title": "Build it", "parentTaskId": None},
        "labels": [{"name": "code"}],
        "taskThreads": [{"threadId": WORKER, "attachedAt": "2026-09-19T12:00:10.500Z", "title": "worker gpt"}],
        "comments": [
            comment("2026-09-19T12:00:00.000Z", f"Status changed to Todo by agent ({LEAD})"),
            comment("2026-09-19T12:00:10.000Z", "Status changed to In Progress by cli"),  # the board, not an agent
            comment("2026-09-19T12:00:20.000Z", "handoff (ok): Built", WORKER),
            comment("2026-09-19T12:00:20.300Z", f"Status changed to Done by agent ({WORKER})"),
        ],
    }}
    return FakeTasks(shown)


def test_a_task_the_board_dispatched_is_started_by_its_worker(one_task: FakeTasks) -> None:
    out = [e for e in events(one_task, FakeThreads()) if e["kind"] == "task"]

    assert [e["action"] for e in out] == ["created", "started", "handed_off"]
    assert out[1]["agent"]["thread"] == WORKER
    assert out[1]["agent"]["role"] == "worker"


def test_a_task_created_by_an_unattached_thread_takes_its_title_from_bb(one_task: FakeTasks) -> None:
    stranger = "thr_stranger"
    one_task.shown["FAB-1"]["comments"][0] = comment("2026-09-19T12:00:00.000Z", f"Status changed to Todo by agent ({stranger})")

    out = [e for e in events(one_task, FakeThreads()) if e["kind"] == "task"]

    assert out[0]["action"] == "created"
    assert out[0]["agent"] == {"role": "worker", "model": "gpt", "imitator": False, "thread": stranger}


def test_a_task_started_without_an_attached_thread_is_started_by_the_agent_in_the_comment(one_task: FakeTasks) -> None:
    shown = one_task.shown["FAB-1"]
    shown["taskThreads"] = []
    shown["comments"][1] = comment("2026-09-19T12:00:10.000Z", f"Status changed to In Progress by agent ({WORKER})")

    out = [e for e in events(one_task, FakeThreads()) if e["action"] == "started" and e["kind"] == "task"]

    assert [e["agent"]["thread"] for e in out] == [WORKER]
