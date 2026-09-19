import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from factory import board as module
from factory.board import AgentConfig, Board, Config, write_message

SECRETARY, PLANNER = "thr_secretary", "thr_planner"


class FakeTelegram:
    def __init__(self, incoming: list[str] = []):
        self.sent: list[str] = []
        self.incoming = list(incoming)

    def send(self, text: str) -> None:
        self.sent.append(text)

    def replies(self) -> list[str]:
        return [self.incoming.pop(0)] if self.incoming else []


class FakeThreads:
    def __init__(self):
        self.told: list[tuple[str, str]] = []

    def tell(self, thread: str, text: str) -> None:
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
    (tmp_path / "messages.jsonl").write_text("")
    agent = AgentConfig(prompt="secretary")
    config = Config(planner=agent, lead=agent, worker=agent, tester=agent, secretary=agent)
    board = Board(config, tasks=None, threads=FakeThreads(), workspace=None, telegram=FakeTelegram())
    board.planner, board.secretary = PLANNER, SECRETARY
    return board


def test_a_question_goes_to_mikhail_once(board: Board) -> None:
    write_message("secretary", "human", "Tailwind or plain CSS?")

    assert board.deliver([]) is True
    assert board.deliver([]) is False  # a second tick does not send it again

    assert board.telegram.sent == ["Tailwind or plain CSS?"]
    assert board.threads.told == []


def test_his_answer_wakes_the_secretary(board: Board) -> None:
    board.telegram.incoming.append("Tailwind")

    board.deliver([])

    thread, text = board.threads.told[0]
    assert thread == SECRETARY
    assert "Tailwind" in text
    assert board.waiting is None


def test_silence_past_the_deadline_wakes_the_secretary(board: Board) -> None:
    ask("Ship it now?", wait_minutes=15)
    board.deliver([])
    assert board.waiting > datetime.now()  # the secretary is waiting for him

    board.waiting = datetime.now() - timedelta(seconds=1)  # the time it gave him has just run out

    assert board.deliver([]) is True

    assert [thread for thread, _ in board.threads.told] == [SECRETARY]
    assert "not answered" in board.threads.told[0][1]
    assert board.waiting is None


def test_what_mikhail_says_on_his_own_can_reach_the_planner(board: Board) -> None:
    write_message("secretary", "planner", "Mikhail wants it done without Tailwind")

    board.deliver([])

    assert board.threads.told == [(PLANNER, board.threads.told[0][1])]
    assert "without Tailwind" in board.threads.told[0][1]
