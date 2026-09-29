"""Tool execution records."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import ToolExecution, ToolExecutionStatus
from app.models.base import utcnow
from app.repositories._helpers import insert_or_translate


class ToolExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def start(
        self,
        workflow_id: uuid.UUID,
        *,
        node: str,
        tool_name: str,
        input: dict[str, Any],
        idempotency_key: str,
        attempt: int = 1,
    ) -> ToolExecution:
        """Record a RUNNING execution. A repeated idempotency key raises ConflictError."""
        execution = ToolExecution(
            workflow_id=workflow_id,
            node=node,
            tool_name=tool_name,
            input=input,
            idempotency_key=idempotency_key,
            attempt=attempt,
        )
        insert_or_translate(
            self._session,
            execution,
            workflow_id=workflow_id,
            conflict_message=f"tool execution '{idempotency_key}' already recorded",
        )
        return execution

    def get(self, execution_id: uuid.UUID) -> ToolExecution:
        execution = self._session.get(ToolExecution, execution_id)
        if execution is None:
            raise NotFoundError(f"tool execution {execution_id} not found")
        return execution

    def get_by_idempotency_key(self, key: str) -> ToolExecution | None:
        stmt = select(ToolExecution).where(ToolExecution.idempotency_key == key)
        return self._session.scalars(stmt).one_or_none()

    def mark_succeeded(
        self, execution_id: uuid.UUID, *, output: dict[str, Any], duration_ms: float
    ) -> ToolExecution:
        execution = self._require_running(execution_id)
        execution.status = ToolExecutionStatus.SUCCEEDED
        execution.output = output
        execution.duration_ms = duration_ms
        execution.finished_at = utcnow()
        self._session.flush()
        return execution

    def mark_failed(
        self, execution_id: uuid.UUID, *, error: str, duration_ms: float
    ) -> ToolExecution:
        execution = self._require_running(execution_id)
        execution.status = ToolExecutionStatus.FAILED
        execution.error = error
        execution.duration_ms = duration_ms
        execution.finished_at = utcnow()
        self._session.flush()
        return execution

    def list_for_workflow(self, workflow_id: uuid.UUID) -> list[ToolExecution]:
        stmt = (
            select(ToolExecution)
            .where(ToolExecution.workflow_id == workflow_id)
            .order_by(ToolExecution.started_at, ToolExecution.attempt)
        )
        return list(self._session.scalars(stmt))

    def _require_running(self, execution_id: uuid.UUID) -> ToolExecution:
        execution = self.get(execution_id)
        if execution.status != ToolExecutionStatus.RUNNING:
            raise ConflictError(f"tool execution {execution_id} already {execution.status.value}")
        return execution
