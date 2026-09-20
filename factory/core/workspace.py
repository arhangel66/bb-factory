"""The run's project: a git repo the workers branch off, one worktree per task, under .factory/."""

import json
import shutil
import subprocess
from pathlib import Path

from factory.kits import Kit
from factory.roles import SKILLS_BY_ROLE, Role
from factory.state import ROOT

TRUST = Path.home() / ".pi/agent/trust.json"  # {path: trusted}; outside these pi ignores .pi/ and the agent loses its tools
TEMPLATES = ROOT / "factory/roles/templates"  # what a project that has never been through the factory starts with


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

    def prepare(self, kit: Kit | None = None) -> None:
        # the directory a run starts from: trusted by pi, a git repo with a commit, .factory/ ignored locally,
        # seeded with the kit the run names
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
        self.knowledge()
        if kit:
            self.seed(kit)
        self.forget_worktrees()
        self.with_tools(self.workdir, Role.tester)  # the tester works in the project itself
        self.agent_dir(Role.planner, Role.planner)

    def knowledge(self) -> None:
        # a project with no AGENTS.md has never been through the factory: it starts with how it is worked on
        # — docs in OKF, the ponytail ladder, a commit per step, a check to fill — and an empty docs/ to
        # fill. Force-added: Mikhail's global gitignore hides AGENTS.md
        if (self.workdir / "AGENTS.md").exists():
            return
        shutil.copy(TEMPLATES / "AGENTS.md", self.workdir / "AGENTS.md")
        (self.workdir / "docs").mkdir(exist_ok=True)
        shutil.copy(TEMPLATES / "docs/index.md", self.workdir / "docs/index.md")
        git(self.workdir, "add", "-f", "AGENTS.md", "docs")
        git(self.workdir, "commit", "-m", "how this project is worked on, and a docs/ to fill")

    def seed(self, kit: Kit) -> None:
        # what the kit hands the project, once and committed before any thread exists, so every worktree has it:
        # its skills where the project has none of that name, a Kit section in AGENTS.md
        skills = self.workdir / ".agents/skills"
        skills.mkdir(parents=True, exist_ok=True)
        for skill in sorted((kit.root / ".agents/skills").iterdir()):
            if skill.is_dir() and not (skills / skill.name).exists():
                shutil.copytree(skill, skills / skill.name)
        lock = self.workdir / "skills-lock.json"
        if not lock.exists() and (kit.root / "skills-lock.json").exists():
            shutil.copy(kit.root / "skills-lock.json", lock)
        link = self.workdir / ".claude/skills"  # Mikhail's Claude Code reads the same skills
        if not link.is_symlink():
            link.parent.mkdir(exist_ok=True)
            link.symlink_to(Path("../.agents/skills"))
        agents = self.workdir / "AGENTS.md"
        text = agents.read_text() if agents.exists() else "# Agents\n"
        if "## Kit" not in text:
            agents.write_text(text.rstrip("\n") + "\n\n" + kit.agents_section())
        git(self.workdir, "add", "-f", "AGENTS.md", ".agents", ".claude", *(["skills-lock.json"] if lock.exists() else []))
        git(self.workdir, "commit", "-m", f"seeded with the {kit.name} kit", check=False)  # seeded before: nothing to commit

    def forget_worktrees(self) -> None:
        # what a run before this one left under .factory/work: keys repeat per run, a leftover would block the branch
        for line in git(self.workdir, "worktree", "list", "--porcelain").stdout.splitlines():
            if line.startswith("worktree ") and line.removeprefix("worktree ").startswith(str(self.factory / "work")):
                git(self.workdir, "worktree", "remove", "--force", line.removeprefix("worktree "), check=False)
        git(self.workdir, "worktree", "prune")

    def agent_dir(self, name: str, role: Role) -> Path:
        path = self.factory / name
        path.mkdir(parents=True, exist_ok=True)
        return self.with_tools(path, role)

    def worktree(self, key: str) -> Path:
        # a branch of its own per task, reset when the task comes back after a conflict
        path = self.factory / "work" / key
        if path.exists() and not (path / ".git").exists():
            shutil.rmtree(path)  # an agent of a run before, dead board and all, kept writing where its worktree was
        git(self.workdir, "worktree", "add", "-B", key, str(path))
        return self.with_tools(path, Role.worker)

    def with_tools(self, path: Path, role: Role) -> Path:
        # pi reads extensions and skills from <cwd>/.pi, so every agent directory gets one: the factory's
        # extensions and settings linked in, and the role's skills linked from the factory's store; rebuilt every
        # time, so a name dropped from the set is gone at the next run
        pi = path / ".pi"
        if pi.is_symlink():
            pi.unlink()  # before, .pi was a link to the factory's whole .pi
        pi.mkdir(exist_ok=True)
        for name in ("extensions", "settings.json"):
            if not (pi / name).is_symlink():
                (pi / name).symlink_to(ROOT / ".pi" / name)
        skills = pi / "skills"
        if skills.exists():
            shutil.rmtree(skills)
        skills.mkdir()
        for name in SKILLS_BY_ROLE[role]:
            (skills / name).symlink_to(ROOT / ".agents/skills" / name)
        return path

    def drop(self, key: str) -> None:
        # a canceled task: its worktree goes, nothing of it reaches the project
        path = self.factory / "work" / key
        if path.exists():
            git(self.workdir, "worktree", "remove", "--force", str(path))

    def merge(self, key: str, title: str) -> str | None:
        # the board commits and merges for the worker; a conflict comes back as text and the worktree stays
        # for the worker to resolve it in — the commit also completes a merge the worker left resolved
        path = self.factory / "work" / key
        if not path.exists():
            return None
        git(path, "add", "-A")
        git(path, "commit", "-m", f"{key} {title}", check=False)  # nothing to commit is not a failure
        # what the testers left in the project (reports, known issues) is committed first: uncommitted or
        # untracked files would block the merge, and they belong to the project anyway
        git(self.workdir, "add", "-A")
        git(self.workdir, "commit", "-m", "left in the project by the tests", check=False)
        merged = git(self.workdir, "merge", "--no-ff", "--no-edit", key, check=False)
        if merged.returncode != 0:
            git(self.workdir, "merge", "--abort", check=False)
            return f"{merged.stdout}\n{merged.stderr}".strip()
        git(self.workdir, "worktree", "remove", "--force", str(path))
        return None

    def main_branch(self) -> str:
        return git(self.workdir, "branch", "--show-current").stdout.strip()
