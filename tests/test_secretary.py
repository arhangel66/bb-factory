import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from factory.core import events as events_module
from factory.core.board import Board
from factory.core.tracker import Tracker
from factory.roles import AgentConfig, Config, Model, Role, Thinking
from factory.tools import messages as module
from factory.tools.messages import write_message

SECRETARY, PLANNER = "thr_secretary", "thr_planner"


class FakeTelegram:
    def __init__(self, incoming: list[str] = []):
        self.sent: list[str] = []
        self.files: list[str] = []
        self.incoming = list(incoming)
        self.unsendable: list[str] = []  # what the bot refuses, as a screenshot in a dropped worktree is
        self.unreachable = ""  # the text whose send fails outright, as a bot with no chat does

    def send(self, text: str, files: list[str] = ()) -> list[str]:
        if text == self.unreachable:
            raise RuntimeError("nobody has written to the bot yet")
        self.sent.append(text)
        self.files.extend(files)
        return [f"telegram sendPhoto {f}: no such file" for f in files if f in self.unsendable]

    def replies(self) -> list[str]:
        return [self.incoming.pop(0)] if self.incoming else []


class FakeThreads:
    def __init__(self):
        self.told: list[tuple[str, str]] = []
        self.deaf: set[str] = set()  # threads bb will not take a message for

    def tell(self, thread: str, text: str, mode: str = "queue") -> None:
        if thread in self.deaf:
            raise RuntimeError(f"bb thread tell {thread}: no such thread")
        self.told.append((thread, text))


def ask(text: str, wait_minutes: int) -> None:
    # the line the secretary's own `contact_human` appends; the board only reads it
    message = {"at": datetime.now().astimezone().isoformat(), "from": "secretary", "to": "human",
               "text": text, "wait_minutes": wait_minutes, "status": None}
    with module.MESSAGES.open("a") as file:
        file.write(json.dumps(message) + "\n")


@pytest.fixture
def board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Board:
    monkeypatch.setattr(module, "MESSAGES", tmp_path / "messages.jsonl")
    monkeypatch.setattr(events_module, "EVENTS", tmp_path / "events.jsonl")
    for name in ("messages.jsonl", "events.jsonl", "intents.jsonl"):
        (tmp_path / name).write_text("")
    agent = AgentConfig(prompt=Role.secretary, model=Model.gpt_5_6_terra, thinking=Thinking.medium)
    config: Config = {role: agent for role in Role}
    board = Board(config, tracker=Tracker(tmp_path / "tasks.json", tmp_path / "intents.jsonl"),
                  threads=FakeThreads(), workspace=None, telegram=FakeTelegram())
    board.planner, board.secretary = PLANNER, SECRETARY
    return board


def test_a_question_goes_to_mikhail_once(board: Board) -> None:
    write_message("secretary", "human", "Tailwind or plain CSS?")

    assert board.deliver() is True
    assert board.deliver() is False  # a second tick does not send it again

    assert board.telegram.sent == ["Tailwind or plain CSS?"]
    assert board.threads.told == []


def test_files_go_to_mikhail_with_the_text(board: Board) -> None:
    message = {"at": datetime.now().astimezone().isoformat(), "from": "secretary", "to": "human",
               "text": "Three looks, which one?", "wait_minutes": 120, "files": ["/tmp/a.png", "/tmp/b.png"], "status": None}
    with module.MESSAGES.open("a") as file:
        file.write(json.dumps(message) + "\n")

    board.deliver()

    assert board.telegram.sent == ["Three looks, which one?"]
    assert board.telegram.files == ["/tmp/a.png", "/tmp/b.png"]


def test_a_file_that_will_not_send_does_not_stop_the_run_or_resend_the_text(board: Board) -> None:
    # the screenshot lived in a worktree the board had already dropped, and the send of it must not be retried
    board.telegram.unsendable = ["/tmp/gone.png"]
    message = {"at": datetime.now().astimezone().isoformat(), "from": "secretary", "to": "human",
               "text": "Here is how it looks", "files": ["/tmp/gone.png"], "status": None}
    with module.MESSAGES.open("a") as file:
        file.write(json.dumps(message) + "\n")

    board.deliver()
    board.deliver()

    assert board.telegram.sent == ["Here is how it looks"]
    assert board.since_review == ["a file the secretary sent Mikhail did not reach him: "
                                  "telegram sendPhoto /tmp/gone.png: no such file"]


def test_a_message_that_will_not_send_is_not_sent_twice_and_does_not_hold_up_the_next(board: Board) -> None:
    board.telegram.unreachable = "first"
    write_message("secretary", "human", "first")
    write_message("secretary", "human", "second")

    board.deliver()
    board.deliver()

    assert board.telegram.sent == ["second"]
    assert board.since_review == ["a message the secretary sent human did not go: "
                                  "nobody has written to the bot yet"]


def test_a_thread_that_will_not_take_a_message_does_not_hold_up_the_others(board: Board) -> None:
    board.threads.deaf.add(PLANNER)
    write_message("human", "planner", "a word for the planner")
    write_message("human", "secretary", "a word for the secretary")

    board.deliver()

    assert [thread for thread, _ in board.threads.told] == [SECRETARY]
    assert len(board.since_review) == 1


def test_his_answer_wakes_the_secretary(board: Board) -> None:
    board.telegram.incoming.append("Tailwind")

    board.deliver()

    thread, text = board.threads.told[0]
    assert thread == SECRETARY
    assert "Tailwind" in text
    assert board.waiting is None


def test_silence_past_the_deadline_wakes_the_secretary(board: Board) -> None:
    ask("Ship it now?", wait_minutes=15)
    board.deliver()
    assert board.waiting > datetime.now()  # the secretary is waiting for him

    board.waiting = datetime.now() - timedelta(seconds=1)  # the time it gave him has just run out

    assert board.deliver() is True

    assert [thread for thread, _ in board.threads.told] == [SECRETARY]
    assert "not answered" in board.threads.told[0][1]
    assert board.waiting is None


def test_what_mikhail_says_on_his_own_can_reach_the_planner(board: Board) -> None:
    write_message("secretary", "planner", "Mikhail wants it done without Tailwind")

    board.deliver()

    assert board.threads.told == [(PLANNER, board.threads.told[0][1])]
    assert "without Tailwind" in board.threads.told[0][1]


def test_the_planners_answer_wakes_the_secretary_and_the_run_goes_on(board: Board) -> None:
    write_message("planner", "secretary", "the foundation is merged, the app is next")

    board.deliver()

    assert board.threads.told == [(SECRETARY, board.threads.told[0][1])]
    assert "foundation is merged" in board.threads.told[0][1]
    assert board.reported() is False
