import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import ApprovalStatus
from app.repositories import ApprovalRepository, WorkflowRepository

ACTION = {"action": "restart_service", "params": {"service_name": "payment-api"}}


def test_create_pending(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    approvals = ApprovalRepository(session)
    approval = approvals.create_pending(wf.id, ACTION)
    assert approval.status == ApprovalStatus.PENDING
    assert approval.action == ACTION
    assert approvals.get_pending(wf.id) is not None
    assert approvals.get_pending(wf.id).id == approval.id  # type: ignore[union-attr]


def test_only_one_pending_per_workflow(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    approvals = ApprovalRepository(session)
    approvals.create_pending(wf.id, ACTION)
    with pytest.raises(ConflictError):
        approvals.create_pending(wf.id, ACTION)


def test_pending_allowed_on_different_workflows(session: Session) -> None:
    repo = WorkflowRepository(session)
    approvals = ApprovalRepository(session)
    approvals.create_pending(repo.create("a").id, ACTION)
    approvals.create_pending(repo.create("b").id, ACTION)


def test_approve(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    approvals = ApprovalRepository(session)
    approvals.create_pending(wf.id, ACTION)
    decided = approvals.decide(wf.id, approved=True, decided_by="alice", comment="go ahead")
    assert decided.status == ApprovalStatus.APPROVED
    assert decided.decided_by == "alice"
    assert decided.comment == "go ahead"
    assert decided.decided_at is not None
    assert approvals.get_pending(wf.id) is None


def test_reject(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    approvals = ApprovalRepository(session)
    approvals.create_pending(wf.id, ACTION)
    assert approvals.decide(wf.id, approved=False, decided_by="bob").status == (
        ApprovalStatus.REJECTED
    )


def test_duplicate_decision_is_a_conflict(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    approvals = ApprovalRepository(session)
    approvals.create_pending(wf.id, ACTION)
    approvals.decide(wf.id, approved=True, decided_by="alice")
    with pytest.raises(ConflictError):
        approvals.decide(wf.id, approved=True, decided_by="alice")
    with pytest.raises(ConflictError):
        approvals.decide(wf.id, approved=False, decided_by="mallory")
    # The original decision was not overwritten.
    (only,) = approvals.list_for_workflow(wf.id)
    assert only.status == ApprovalStatus.APPROVED
    assert only.decided_by == "alice"


def test_decide_without_pending_is_a_conflict(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    with pytest.raises(ConflictError):
        ApprovalRepository(session).decide(wf.id, approved=True, decided_by="alice")


def test_new_pending_allowed_after_decision(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    approvals = ApprovalRepository(session)
    approvals.create_pending(wf.id, ACTION)
    approvals.decide(wf.id, approved=True, decided_by="alice")
    approvals.create_pending(wf.id, ACTION)  # e.g. a retry needing fresh approval
    assert len(approvals.list_for_workflow(wf.id)) == 2


def test_unknown_workflow_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        ApprovalRepository(session).create_pending(uuid.uuid4(), ACTION)
