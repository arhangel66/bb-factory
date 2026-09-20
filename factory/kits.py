"""Kits: what a run names in one word. A kit is a repository the factory hands to a project at the start of a
run — its proven skills, its docs as the way in, and a brief the goal is prefixed with."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Kit:
    name: str  # what the run says: kit=IOS
    root: Path  # its .agents/skills and docs/index.md are read from here
    brief: str  # before every goal run on it: what to read first, how to build, what is fixed where

    def agents_section(self) -> str:
        # what the project's AGENTS.md says about the kit, once, to every agent and to Mikhail's Claude Code
        return (f"## Kit\n\nThis project is built with the {self.name} kit at `{self.root}`: its `docs/index.md` is the\n"
                f"way in, its skills are copied into this project's `.agents/skills/` (`.claude/skills` links there).\n"
                f"What the kit lacks is fixed in the kit, never worked around here.\n")


IOS_ROOT = Path.home() / "w/learning/ios-kit"
IOS = Kit("ios", IOS_ROOT, brief=f"""\
This project is built with the ios kit at {IOS_ROOT}: read its `docs/index.md` first (a quickstart in three
commands), make the app with its starter, build, run, test and drive it the way its docs say; its skills
are in this project's `.agents/skills/`. What the kit lacks is fixed in the kit — a task that works in
{IOS_ROOT} and commits there — never worked around here; the report says what the kit gained. Agents run
in parallel on one Mac: every agent boots a simulator device of its own (`xcrun simctl create`, deleted
when done), never a shared one, and keeps derived data in its own tree.
""")
