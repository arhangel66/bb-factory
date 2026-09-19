import json
import subprocess
from pathlib import Path

import pytest

from factory import workspace as module
from factory.workspace import Workspace, git


@pytest.fixture
def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Workspace:
    trust = tmp_path / "trust.json"
    trust.write_text(json.dumps({str(tmp_path): True}))
    monkeypatch.setattr(module, "TRUST", trust)
    space = Workspace(tmp_path / "project")
    space.prepare()
    return space


def work(space: Workspace, key: str, name: str, text: str) -> None:
    (space.worktree(key) / name).write_text(text)


def test_prepare_makes_a_repo_with_a_commit(prepared: Workspace) -> None:
    assert git(prepared.workdir, "rev-parse", "HEAD").returncode == 0
    assert ".factory/" in (prepared.workdir / ".git/info/exclude").read_text()
    assert (prepared.factory / "planner/.pi").resolve() == module.ROOT / ".pi"


def test_untrusted_workdir_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trust = tmp_path / "trust.json"
    trust.write_text(json.dumps({str(tmp_path / "trusted"): True}))
    monkeypatch.setattr(module, "TRUST", trust)
    with pytest.raises(RuntimeError, match="trusted paths"):
        Workspace(tmp_path / "elsewhere").prepare()


def test_merge_brings_the_work_into_the_project(prepared: Workspace) -> None:
    work(prepared, "FAB-1", "app.py", "print('one')\n")

    assert prepared.merge("FAB-1", "first task") is None

    assert (prepared.workdir / "app.py").read_text() == "print('one')\n"
    assert git(prepared.workdir, "ls-files").stdout.split() == ["app.py"]  # the agent's .pi stays out of the project
    assert not (prepared.factory / "work/FAB-1").exists()


def test_conflicting_work_comes_back_as_text(prepared: Workspace) -> None:
    work(prepared, "FAB-1", "app.py", "print('one')\n")
    work(prepared, "FAB-2", "app.py", "print('two')\n")
    prepared.merge("FAB-1", "first task")

    conflict = prepared.merge("FAB-2", "second task")

    assert "app.py" in conflict
    assert (prepared.workdir / "app.py").read_text() == "print('one')\n"  # the project keeps the merged work
    assert subprocess.run(["git", "-C", str(prepared.workdir), "status", "--porcelain"],
                          capture_output=True, text=True).stdout == ""
