from pathlib import Path

import pytest

from factory import state as module
from factory.state import start_run


def test_a_run_gets_a_directory_of_its_own_and_current_points_at_the_newest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(module, "CURRENT", tmp_path / "current")

    first = start_run("2026-09-19-100000", tmp_path / "project")
    second = start_run("2026-09-19-100100", tmp_path / "project")

    assert (tmp_path / "current").resolve() == second
    assert (first / "keys").is_dir()
    assert (second / "intents.jsonl").read_text() == ""
    assert (second / "workdir").readlink() == tmp_path / "project"
