"""Workflow event (audit trail) persistence."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventLevel, WorkflowEvent
from app.repositories._helpers import insert_or_translate


class EventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        workflow_id: uuid.UUID,
        event_type: str,
        *,
        node: str | None = None,
        level: EventLevel = EventLevel.INFO,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        """Append an event with the next per-workflow ``seq``.

        seq = max(seq) + 1 inside the caller's transaction. Two concurrent writers to the
        same workflow could collide; the unique (workflow_id, seq) constraint turns that
        into a ConflictError instead of silent corruption. In practice one graph run
        writes a workflow's events sequentially.
        """
        max_seq = self._session.scalar(
            select(func.max(WorkflowEvent.seq)).where(WorkflowEvent.workflow_id == workflow_id)
        )
        event = WorkflowEvent(
            workflow_id=workflow_id,
            seq=(max_seq or 0) + 1,
            event_type=event_type,
            node=node,
            level=level,
            payload=payload or {},
        )
        insert_or_translate(
            self._session,
            event,
            workflow_id=workflow_id,
            conflict_message=f"event sequence conflict for workflow {workflow_id}",
        )
        return event

    def list_for_workflow(
        self, workflow_id: uuid.UUID, *, after_seq: int = 0, limit: int = 100
    ) -> list[WorkflowEvent]:
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_id == workflow_id, WorkflowEvent.seq > after_seq)
            .order_by(WorkflowEvent.seq)
            .limit(limit)
        )
        return list(self._session.scalars(stmt))
