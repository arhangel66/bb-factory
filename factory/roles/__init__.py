"""Who the agents are: the roles, the task labels that call for them, their prompts, and how a run staffs them."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

PROMPTS = Path(__file__).parent / "prompts"


class Role(StrEnum):
    """A role is its prompt file, the tools the pi extension gives it, and its first word in a thread title."""

    planner = "planner"
    lead = "lead"  # plans an `epic` task as sub-tasks, one thread per epic
    worker = "worker"  # does `code` tasks
    tester = "tester"  # does `test` tasks
    secretary = "secretary"  # does `ask` tasks: the only agent that talks to Mikhail
    imitator = "imitator"  # plays whatever role its task needs, for test runs


ROLE_BY_LABEL = {"code": Role.worker, "test": Role.tester, "epic": Role.lead, "ask": Role.secretary}
LABEL_BY_ROLE = {role: label for label, role in ROLE_BY_LABEL.items()}


@dataclass(frozen=True)
class AgentConfig:
    prompt: Role  # prompts/<prompt>.md; the role the pi extension gates tools by
    model: str = "openai-codex/gpt-5.6-terra"
    mode: Literal["per_task", "shared"] = "per_task"  # shared = one thread for every task (the imitator)


# who serves each role in a run: planner, lead, worker, tester and secretary; the imitator may serve several
Config = dict[Role, AgentConfig]


def prompt(name: str, **fields: str) -> str:
    return (PROMPTS / f"{name}.md").read_text().format(**fields)
