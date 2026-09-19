"""Who the agents are: the roles of the factory and the task labels that call for them."""

from enum import StrEnum


class Role(StrEnum):
    """A role is its prompt file, the tools the pi extension gives it, and its first word in a thread title."""

    planner = "planner"
    lead = "lead"
    worker = "worker"
    tester = "tester"
    secretary = "secretary"
    imitator = "imitator"


ROLE_BY_LABEL = {"code": Role.worker, "test": Role.tester, "epic": Role.lead, "ask": Role.secretary}
LABEL_BY_ROLE = {role: label for label, role in ROLE_BY_LABEL.items()}
