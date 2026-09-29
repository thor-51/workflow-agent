"""Enumerations and the workflow status state machine."""

from enum import StrEnum


class WorkflowStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


TERMINAL_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {WorkflowStatus.COMPLETED, WorkflowStatus.REJECTED, WorkflowStatus.FAILED}
)

_ALLOWED_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.CREATED: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.FAILED}),
    WorkflowStatus.RUNNING: frozenset(
        {
            WorkflowStatus.AWAITING_APPROVAL,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.REJECTED,
            WorkflowStatus.FAILED,
        }
    ),
    WorkflowStatus.AWAITING_APPROVAL: frozenset(
        {WorkflowStatus.RUNNING, WorkflowStatus.REJECTED, WorkflowStatus.FAILED}
    ),
    WorkflowStatus.COMPLETED: frozenset(),
    WorkflowStatus.REJECTED: frozenset(),
    WorkflowStatus.FAILED: frozenset(),
}


def can_transition(current: WorkflowStatus, target: WorkflowStatus) -> bool:
    """True if moving ``current`` -> ``target`` is legal. Same-status is a no-op."""
    return current == target or target in _ALLOWED_TRANSITIONS[current]


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ToolExecutionStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EventLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
