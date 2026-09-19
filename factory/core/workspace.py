"""The run's project: a git repo the workers branch off, one worktree per task, under .factory/."""

import json
import subprocess
from pathlib import Path

from factory.roles import Role
from factory.state import ROOT

TRUST = Path.home() / ".pi/agent/trust.json"  # {path: trusted}; outside these pi ignores .pi/ and the agent loses its tools


def git(workdir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", "-C", str(workdir), *args], capture_output=True, text=True, timeout=60)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {workdir}: {done.stderr.strip() or done.stdout.strip()}")
    return done


class Workspace:
    """Where the agents work: <workdir> is the project, .factory/ holds the directories they run in."""

    def __init__(self, workdir: Path):
        self.workdir = workdir.expanduser().resolve()
        self.factory = self.workdir / ".factory"

    def prepare(self) -> None:
        # the directory a run starts from: trusted by pi, a git repo with a commit, .factory/ ignored locally
        trusted = json.loads(TRUST.read_text()) if TRUST.exists() else {}
        if not any(ok and self.workdir.is_relative_to(path) for path, ok in trusted.items()):
            raise RuntimeError(f"{self.workdir} is outside pi's trusted paths in {TRUST}: "
                               "the agents would start without the factory tools")
        self.workdir.mkdir(parents=True, exist_ok=True)
        if git(self.workdir, "rev-parse", "--git-dir", check=False).returncode != 0:
            git(self.workdir, "init")
            git(self.workdir, "commit", "--allow-empty", "-m", "init")  # a worktree needs a HEAD to branch from
        exclude = self.workdir / ".git/info/exclude"
        # /.pi anchors at the root of every worktree as well: the symlink belongs to the agent, not the project
        missing = [line for line in (".factory/", "/.pi") if line not in exclude.read_text()]
        exclude.write_text(exclude.read_text() + "".join(f"{line}\n" for line in missing))
        self.forget_worktrees()
        self.with_tools(self.workdir)  # the tester works in the project itself
        self.agent_dir(Role.planner)

    def forget_worktrees(self) -> None:
        # what a run before this one left under .factory/work: keys repeat per run, a leftover would block the branch
        for line in git(self.workdir, "worktree", "list", "--porcelain").stdout.splitlines():
            if line.startswith("worktree ") and line.removeprefix("worktree ").startswith(str(self.factory / "work")):
                git(self.workdir, "worktree", "remove", "--force", line.removeprefix("worktree "), check=False)
        git(self.workdir, "worktree", "prune")

    def agent_dir(self, name: str) -> Path:
        path = self.factory / name
        path.mkdir(parents=True, exist_ok=True)
        return self.with_tools(path)

    def worktree(self, key: str) -> Path:
        # a branch of its own per task, reset when the task comes back after a conflict
        path = self.factory / "work" / key
        git(self.workdir, "worktree", "add", "-B", key, str(path))
        return self.with_tools(path)

    def with_tools(self, path: Path) -> Path:
        # pi reads extensions from its cwd only, so every agent directory links back to the factory's .pi
        link = path / ".pi"
        if not link.exists():
            link.symlink_to(ROOT / ".pi")
        return path

    def drop(self, key: str) -> None:
        # a canceled task: its worktree goes, nothing of it reaches the project
        path = self.factory / "work" / key
        if path.exists():
            git(self.workdir, "worktree", "remove", "--force", str(path))

    def merge(self, key: str, title: str) -> str | None:
        # the board commits and merges for the worker; the conflict comes back as text, the worktree always goes
        path = self.factory / "work" / key
        if not path.exists():
            return None
        git(path, "add", "-A")
        git(path, "commit", "-m", f"{key} {title}", check=False)  # nothing to commit is not a failure
        merged = git(self.workdir, "merge", "--no-ff", "--no-edit", key, check=False)
        if merged.returncode != 0:
            git(self.workdir, "merge", "--abort", check=False)
        git(self.workdir, "worktree", "remove", "--force", str(path))
        return f"{merged.stdout}\n{merged.stderr}".strip() if merged.returncode != 0 else None
