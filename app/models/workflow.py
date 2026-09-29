"""ORM models for workflows and their audit data."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow
from app.models.enums import ApprovalStatus, EventLevel, ToolExecutionStatus, WorkflowStatus
from app.models.types import UTCDateTime, enum_column


class Workflow(Base):
    """One run of the agent. ``id`` doubles as the LangGraph ``thread_id`` (Phase 4)."""

    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request: Mapped[str] = mapped_column(Text)
    status: Mapped[WorkflowStatus] = mapped_column(
        enum_column(WorkflowStatus), default=WorkflowStatus.CREATED, index=True
    )
    # Reference to the (simulated, effectively external) issue tracker; deliberately not an FK.
    issue_id: Mapped[str | None] = mapped_column(String(64), default=None)
    final_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class WorkflowEvent(Base):
    """Append-only execution history. ``seq`` orders events within a workflow."""

    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint("workflow_id", "seq", name="uq_workflow_events_workflow_id_seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    node: Mapped[str | None] = mapped_column(String(64), default=None)
    level: Mapped[EventLevel] = mapped_column(enum_column(EventLevel), default=EventLevel.INFO)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class ToolExecution(Base):
    """Record of one tool call attempt. ``idempotency_key`` prevents double execution."""

    __tablename__ = "tool_executions"
    __table_args__ = (UniqueConstraint("idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    node: Mapped[str] = mapped_column(String(64))
    tool_name: Mapped[str] = mapped_column(String(64))
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    status: Mapped[ToolExecutionStatus] = mapped_column(
        enum_column(ToolExecutionStatus), default=ToolExecutionStatus.RUNNING
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    duration_ms: Mapped[float | None] = mapped_column(Float, default=None)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class Approval(Base):
    """A human approval request. At most one PENDING approval per workflow (partial index)."""

    __tablename__ = "approvals"
    __table_args__ = (
        Index(
            "uq_approvals_one_pending_per_workflow",
            "workflow_id",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[ApprovalStatus] = mapped_column(
        enum_column(ApprovalStatus), default=ApprovalStatus.PENDING
    )
    requested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    decided_by: Mapped[str | None] = mapped_column(String(128), default=None)
    comment: Mapped[str | None] = mapped_column(Text, default=None)
