"""Workflow persistence."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import TERMINAL_STATUSES, Workflow, WorkflowStatus, can_transition
from app.models.base import utcnow


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, request: str) -> Workflow:
        workflow = Workflow(request=request)
        self._session.add(workflow)
        self._session.flush()
        return workflow

    def find(self, workflow_id: uuid.UUID) -> Workflow | None:
        return self._session.get(Workflow, workflow_id)

    def get(self, workflow_id: uuid.UUID) -> Workflow:
        workflow = self.find(workflow_id)
        if workflow is None:
            raise NotFoundError(f"workflow {workflow_id} not found")
        return workflow

    def set_status(self, workflow_id: uuid.UUID, status: WorkflowStatus) -> Workflow:
        """Move a workflow to ``status`` if the transition is legal (same status is a no-op)."""
        workflow = self.get(workflow_id)
        if not can_transition(workflow.status, status):
            raise ConflictError(
                f"illegal workflow transition {workflow.status.value} -> {status.value}"
            )
        if workflow.status == status:
            return workflow
        workflow.status = status
        if status in TERMINAL_STATUSES:
            workflow.completed_at = utcnow()
        self._session.flush()
        return workflow

    def set_issue_id(self, workflow_id: uuid.UUID, issue_id: str) -> Workflow:
        workflow = self.get(workflow_id)
        workflow.issue_id = issue_id
        self._session.flush()
        return workflow

    def set_final_report(self, workflow_id: uuid.UUID, report: dict[str, Any]) -> Workflow:
        workflow = self.get(workflow_id)
        workflow.final_report = report
        self._session.flush()
        return workflow

    def list_recent(self, limit: int = 50) -> list[Workflow]:
        stmt = select(Workflow).order_by(Workflow.created_at.desc(), Workflow.id).limit(limit)
        return list(self._session.scalars(stmt))
