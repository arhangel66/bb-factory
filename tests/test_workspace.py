import json
import subprocess
from pathlib import Path

import pytest

from factory.core import workspace as module
from factory.core.workspace import Workspace, git
from factory.kits import Kit
from factory.roles import SKILLS_BY_ROLE, Role


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
    assert (prepared.factory / "planner/.pi/extensions").resolve() == module.ROOT / ".pi/extensions"


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


def test_files_the_tests_left_in_the_project_are_committed_before_the_merge(prepared: Workspace) -> None:
    work(prepared, "FAB-1", "app.py", "print('one')\n")
    (prepared.workdir / "reports/stage-1").mkdir(parents=True)  # testers run in the project itself
    (prepared.workdir / "reports/stage-1/round-1.md").write_text("checked\n")

    assert prepared.merge("FAB-1", "first task") is None

    assert (prepared.workdir / "app.py").read_text() == "print('one')\n"
    assert "reports/stage-1/round-1.md" in git(prepared.workdir, "ls-files").stdout.split()
    assert git(prepared.workdir, "status", "--porcelain").stdout == ""


def test_conflicting_work_comes_back_as_text(prepared: Workspace) -> None:
    work(prepared, "FAB-1", "app.py", "print('one')\n")
    work(prepared, "FAB-2", "app.py", "print('two')\n")
    prepared.merge("FAB-1", "first task")

    conflict = prepared.merge("FAB-2", "second task")

    assert "app.py" in conflict
    assert (prepared.workdir / "app.py").read_text() == "print('one')\n"  # the project keeps the merged work
    assert subprocess.run(["git", "-C", str(prepared.workdir), "status", "--porcelain"],
                          capture_output=True, text=True).stdout == ""
    assert (prepared.factory / "work/FAB-2").exists()  # the worker resolves it there


def test_a_conflict_the_worker_resolved_merges_the_second_time(prepared: Workspace) -> None:
    work(prepared, "FAB-1", "app.py", "print('one')\n")
    work(prepared, "FAB-2", "app.py", "print('two')\n")
    prepared.merge("FAB-1", "first task")
    prepared.merge("FAB-2", "second task")
    worktree = prepared.factory / "work/FAB-2"
    git(worktree, "merge", prepared.main_branch(), check=False)  # what the worker is told to run
    (worktree / "app.py").write_text("print('one')\nprint('two')\n")

    assert prepared.merge("FAB-2", "second task") is None

    assert (prepared.workdir / "app.py").read_text() == "print('one')\nprint('two')\n"
    assert not worktree.exists()


def test_prepare_forgets_the_worktrees_of_a_run_before(prepared: Workspace) -> None:
    work(prepared, "FAB-1", "app.py", "print('one')\n")

    Workspace(prepared.workdir).prepare()

    assert not (prepared.factory / "work/FAB-1").exists()
    assert git(prepared.workdir, "worktree", "list").stdout.count("\n") == 1
    work(prepared, "FAB-1", "app.py", "print('again')\n")  # the key is free for the new run


def test_drop_throws_the_work_away(prepared: Workspace) -> None:
    work(prepared, "FAB-1", "app.py", "print('one')\n")

    prepared.drop("FAB-1")

    assert not (prepared.factory / "work/FAB-1").exists()
    assert not (prepared.workdir / "app.py").exists()


def test_a_directory_left_where_a_worktree_goes_does_not_block_it(prepared: Workspace) -> None:
    stale = prepared.factory / "work/FAB-7"
    stale.mkdir(parents=True)
    (stale / "check.sh").write_text("left by an agent whose board is gone")

    path = prepared.worktree("FAB-7")

    assert path == stale and (path / ".git").exists() and not (path / "check.sh").exists()


def test_a_kit_seeds_the_project_once_and_keeps_its_own_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trust = tmp_path / "trust.json"
    trust.write_text(json.dumps({str(tmp_path): True}))
    monkeypatch.setattr(module, "TRUST", trust)
    for name in ("a", "b"):
        (tmp_path / f"kit/.agents/skills/{name}").mkdir(parents=True)
        (tmp_path / f"kit/.agents/skills/{name}/SKILL.md").write_text(f"kit {name}")
    project = tmp_path / "project"
    (project / ".agents/skills/a").mkdir(parents=True)
    (project / ".agents/skills/a/SKILL.md").write_text("mine")  # the project rewrote it: its copy wins
    kit = Kit("k", tmp_path / "kit", brief="the brief")
    space = Workspace(project)

    space.prepare(kit)
    space.prepare(kit)  # a second run on the same project seeds nothing more

    assert (project / ".agents/skills/a/SKILL.md").read_text() == "mine"
    assert (project / ".agents/skills/b/SKILL.md").read_text() == "kit b"
    assert (project / ".claude/skills").resolve() == (project / ".agents/skills").resolve()
    assert "## Kit" in (project / "AGENTS.md").read_text()
    assert git(project, "log", "--format=%s").stdout.split() == ["seeded", "with", "the", "k", "kit", "init"]
    assert git(project, "status", "--porcelain").stdout == ""


def test_every_skill_of_every_role_is_in_the_store() -> None:
    for role, names in SKILLS_BY_ROLE.items():
        for name in names:
            assert (module.ROOT / ".agents/skills" / name / "SKILL.md").exists(), f"{role}: {name}"


def test_an_agent_directory_carries_its_roles_skills(prepared: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(module.SKILLS_BY_ROLE, Role.lead, ("okf-knowledge-base",))
    monkeypatch.setitem(module.SKILLS_BY_ROLE, Role.secretary, ())

    lead = prepared.agent_dir("lead/FAB-1", Role.lead)
    secretary = prepared.agent_dir("secretary", Role.secretary)

    assert (lead / ".pi/skills/okf-knowledge-base/SKILL.md").exists()
    assert (lead / ".pi/settings.json").resolve() == module.ROOT / ".pi/settings.json"
    assert list((secretary / ".pi/skills").iterdir()) == []


def test_a_skill_dropped_from_the_set_is_gone_at_the_next_run(prepared: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(module.SKILLS_BY_ROLE, Role.lead, ("okf-knowledge-base",))
    lead = prepared.agent_dir("lead/FAB-1", Role.lead)
    monkeypatch.setitem(module.SKILLS_BY_ROLE, Role.lead, ())

    prepared.agent_dir("lead/FAB-1", Role.lead)

    assert not (lead / ".pi/skills/okf-knowledge-base").exists()
