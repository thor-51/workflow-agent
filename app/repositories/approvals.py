"""Human approval records."""

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models import Approval, ApprovalStatus
from app.models.base import utcnow
from app.repositories._helpers import insert_or_translate


class ApprovalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_pending(self, workflow_id: uuid.UUID, action: dict[str, Any]) -> Approval:
        """Open an approval request. A second pending one for the workflow is a conflict."""
        approval = Approval(workflow_id=workflow_id, action=action)
        insert_or_translate(
            self._session,
            approval,
            workflow_id=workflow_id,
            conflict_message=f"workflow {workflow_id} already has a pending approval",
        )
        return approval

    def get_pending(self, workflow_id: uuid.UUID) -> Approval | None:
        stmt = select(Approval).where(
            Approval.workflow_id == workflow_id, Approval.status == ApprovalStatus.PENDING
        )
        return self._session.scalars(stmt).one_or_none()

    def decide(
        self,
        workflow_id: uuid.UUID,
        *,
        approved: bool,
        decided_by: str,
        comment: str | None = None,
    ) -> Approval:
        """Resolve the pending approval exactly once.

        Implemented as a conditional UPDATE (... WHERE status = 'pending') so a duplicate
        or concurrent decision affects zero rows and raises ConflictError, rather than a
        read-then-write that two callers could both pass.
        """
        stmt = (
            update(Approval)
            .where(Approval.workflow_id == workflow_id, Approval.status == ApprovalStatus.PENDING)
            .values(
                status=ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED,
                decided_at=utcnow(),
                decided_by=decided_by,
                comment=comment,
            )
            .returning(Approval.id)
            .execution_options(synchronize_session=False)
        )
        approval_id = self._session.execute(stmt).scalar_one_or_none()
        if approval_id is None:
            raise ConflictError(f"workflow {workflow_id} has no pending approval")
        return self._session.get_one(Approval, approval_id, populate_existing=True)

    def list_for_workflow(self, workflow_id: uuid.UUID) -> list[Approval]:
        stmt = (
            select(Approval)
            .where(Approval.workflow_id == workflow_id)
            .order_by(Approval.requested_at, Approval.id)
        )
        return list(self._session.scalars(stmt))
