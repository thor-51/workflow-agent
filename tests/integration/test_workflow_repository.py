import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import WorkflowStatus
from app.repositories import WorkflowRepository

S = WorkflowStatus


def test_create_sets_defaults(session: Session) -> None:
    wf = WorkflowRepository(session).create("Payment API is returning 500 errors")
    assert isinstance(wf.id, uuid.UUID)
    assert wf.status == S.CREATED
    assert wf.completed_at is None
    assert wf.issue_id is None
    assert wf.final_report is None


def test_get_missing_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        WorkflowRepository(session).get(uuid.uuid4())
    assert WorkflowRepository(session).find(uuid.uuid4()) is None


def test_legal_transition_path_and_completed_at(session: Session) -> None:
    repo = WorkflowRepository(session)
    wf = repo.create("r")
    repo.set_status(wf.id, S.RUNNING)
    repo.set_status(wf.id, S.AWAITING_APPROVAL)
    repo.set_status(wf.id, S.RUNNING)
    assert repo.get(wf.id).completed_at is None
    repo.set_status(wf.id, S.COMPLETED)
    assert repo.get(wf.id).completed_at is not None


def test_illegal_transition_raises_and_leaves_state(session: Session) -> None:
    repo = WorkflowRepository(session)
    wf = repo.create("r")
    with pytest.raises(ConflictError):
        repo.set_status(wf.id, S.COMPLETED)  # created -> completed is not allowed
    assert repo.get(wf.id).status == S.CREATED


def test_terminal_state_cannot_be_left(session: Session) -> None:
    repo = WorkflowRepository(session)
    wf = repo.create("r")
    repo.set_status(wf.id, S.RUNNING)
    repo.set_status(wf.id, S.FAILED)
    with pytest.raises(ConflictError):
        repo.set_status(wf.id, S.RUNNING)


def test_same_status_is_noop(session: Session) -> None:
    repo = WorkflowRepository(session)
    wf = repo.create("r")
    repo.set_status(wf.id, S.RUNNING)
    repo.set_status(wf.id, S.COMPLETED)
    first_completed_at = repo.get(wf.id).completed_at
    repo.set_status(wf.id, S.COMPLETED)
    assert repo.get(wf.id).completed_at == first_completed_at


def test_issue_id_and_final_report_round_trip(session: Session) -> None:
    repo = WorkflowRepository(session)
    wf = repo.create("r")
    repo.set_issue_id(wf.id, "ISSUE-42")
    repo.set_final_report(wf.id, {"summary": "ok", "actions": [{"name": "restart_service"}]})
    session.commit()
    session.expire_all()
    loaded = repo.get(wf.id)
    assert loaded.issue_id == "ISSUE-42"
    assert loaded.final_report == {"summary": "ok", "actions": [{"name": "restart_service"}]}


def test_list_recent_is_newest_first_and_limited(session: Session) -> None:
    repo = WorkflowRepository(session)
    ids = [repo.create(f"r{i}").id for i in range(3)]
    listed = repo.list_recent(limit=2)
    assert len(listed) == 2
    assert listed[0].id == ids[-1]
