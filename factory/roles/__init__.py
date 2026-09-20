"""Who the agents are: the roles, the task labels that call for them, their prompts, and how a run staffs them."""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

from factory.state import ROLES

PROMPTS = Path(__file__).parent / "prompts"


class Role(StrEnum):
    """A role is its prompt file, the tools the pi extension gives it, and its first word in a thread title."""

    planner = "planner"
    lead = "lead"  # plans an `epic` task as sub-tasks, one thread per epic
    worker = "worker"  # does `code` tasks
    tester = "tester"  # does `test` tasks
    secretary = "secretary"  # does `ask` tasks: the only agent that talks to Mikhail
    imitator = "imitator"  # plays whatever role its task needs, for test runs


class Model(StrEnum):
    """What bb's pi provider can run; the full catalog is `bb provider models pi`."""

    gpt_5_6_terra = "openai-codex/gpt-5.6-terra"
    gpt_5_6_sol = "openai-codex/gpt-5.6-sol"
    gpt_5_6_luna = "openai-codex/gpt-5.6-luna"
    gpt_6_astra = "openai-codex/gpt-6-astra"
    gpt_5_5 = "openai-codex/gpt-5.5"
    gpt_5_4_mini = "openai-codex/gpt-5.4-mini"
    kimi_k3 = "kimi-coding/k3-256k"


class Thinking(StrEnum):
    """How long an agent reasons before it acts: bb's `--reasoning-level`, the same five steps for every model."""

    low = "low"
    medium = "medium"
    high = "high"
    xhigh = "xhigh"
    max = "max"


ROLE_BY_LABEL = {"code": Role.worker, "test": Role.tester, "epic": Role.lead, "ask": Role.secretary}
LABEL_BY_ROLE = {role: label for label, role in ROLE_BY_LABEL.items()}

# the tools of .pi/extensions/factory.ts each role may call; anything else pi has is switched off for it
CODING_TOOLS = ("read", "bash", "edit", "write", "grep", "find", "ls")
TOOLS_BY_ROLE: dict[Role, tuple[str, ...]] = {
    # the planner and the leads read the project's docs/, never its code: `read` and `ls`, the prompt says where
    Role.planner: ("read", "ls", "create_task", "amend_task", "cancel_task", "set_priority", "board", "show_task", "report"),
    Role.lead: ("read", "ls", "create_task", "amend_task", "cancel_task", "set_priority", "board", "show_task", "handoff"),
    Role.worker: (*CODING_TOOLS, "handoff"),
    Role.tester: (*CODING_TOOLS, "handoff"),
    Role.secretary: ("contact_human", "tell_planner", "handoff"),
    Role.imitator: ("handoff",),
}


# the skills of .agents/skills/ each role sees, on top of the project's own and Mikhail's personal ones;
# a role's prompt lists only its set, so a worker's skills do not lengthen the planner's
SKILLS_BY_ROLE: dict[Role, tuple[str, ...]] = {
    Role.planner: ("okf-knowledge-base",),
    Role.lead: ("okf-knowledge-base",),
    Role.worker: ("okf-knowledge-base",),
    Role.tester: ("okf-knowledge-base",),
    Role.secretary: (),
    Role.imitator: (),
}


@dataclass(frozen=True)
class AgentConfig:
    prompt: Role  # prompts/<prompt>.md; the role the pi extension gates tools by
    model: Model = Model.gpt_5_6_terra  # no default: a run says out loud who it spends its money on
    thinking: Thinking = Thinking.medium
    mode: Literal["per_task", "shared"] = "per_task"  # shared = one thread for every task (the imitator)


# who serves each role in a run: planner, lead, worker, tester and secretary; the imitator may serve several
Config = dict[Role, AgentConfig]


def prompt(name: str, **fields: str) -> str:
    return (PROMPTS / f"{name}.md").read_text().format(**fields)


def save_tools_by_role() -> None:
    # the extension reads it at every thread's start by the first word of the thread's title
    ROLES.write_text(json.dumps({role: list(tools) for role, tools in TOOLS_BY_ROLE.items()}, indent=2))
