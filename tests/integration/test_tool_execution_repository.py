import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import ToolExecutionStatus
from app.repositories import ToolExecutionRepository, WorkflowRepository


def _start(repo: ToolExecutionRepository, wf_id: uuid.UUID, key: str = "wf:restart:1"):  # type: ignore[no-untyped-def]
    return repo.start(
        wf_id,
        node="execute_actions",
        tool_name="restart_service",
        input={"service_name": "payment-api"},
        idempotency_key=key,
    )


def test_start_records_running_execution(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    execution = _start(ToolExecutionRepository(session), wf.id)
    assert execution.status == ToolExecutionStatus.RUNNING
    assert execution.attempt == 1
    assert execution.output is None
    assert execution.finished_at is None


def test_mark_succeeded(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    repo = ToolExecutionRepository(session)
    execution = repo.mark_succeeded(
        _start(repo, wf.id).id, output={"restarted": True}, duration_ms=12.5
    )
    assert execution.status == ToolExecutionStatus.SUCCEEDED
    assert execution.output == {"restarted": True}
    assert execution.duration_ms == 12.5
    assert execution.finished_at is not None


def test_mark_failed(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    repo = ToolExecutionRepository(session)
    execution = repo.mark_failed(_start(repo, wf.id).id, error="timeout", duration_ms=3000.0)
    assert execution.status == ToolExecutionStatus.FAILED
    assert execution.error == "timeout"


def test_cannot_complete_twice(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    repo = ToolExecutionRepository(session)
    execution_id = _start(repo, wf.id).id
    repo.mark_succeeded(execution_id, output={}, duration_ms=1.0)
    with pytest.raises(ConflictError):
        repo.mark_failed(execution_id, error="late", duration_ms=1.0)
    with pytest.raises(ConflictError):
        repo.mark_succeeded(execution_id, output={}, duration_ms=1.0)


def test_idempotency_key_is_unique(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    repo = ToolExecutionRepository(session)
    first = _start(repo, wf.id, key="k1")
    with pytest.raises(ConflictError):
        _start(repo, wf.id, key="k1")
    assert repo.get_by_idempotency_key("k1") is not None
    assert repo.get_by_idempotency_key("k1").id == first.id  # type: ignore[union-attr]
    assert repo.get_by_idempotency_key("missing") is None
    _start(repo, wf.id, key="k2")  # session still usable after the conflict


def test_unknown_workflow_and_unknown_execution(session: Session) -> None:
    repo = ToolExecutionRepository(session)
    with pytest.raises(NotFoundError):
        _start(repo, uuid.uuid4())
    with pytest.raises(NotFoundError):
        repo.mark_succeeded(uuid.uuid4(), output={}, duration_ms=1.0)


def test_list_for_workflow(session: Session) -> None:
    wf = WorkflowRepository(session).create("r")
    other = WorkflowRepository(session).create("other")
    repo = ToolExecutionRepository(session)
    _start(repo, wf.id, key="a")
    _start(repo, wf.id, key="b")
    _start(repo, other.id, key="c")
    assert {e.idempotency_key for e in repo.list_for_workflow(wf.id)} == {"a", "b"}
