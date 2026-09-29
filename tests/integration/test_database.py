from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from app.core.database import create_db_engine, create_session_factory, session_scope
from app.models import Base, Workflow, WorkflowEvent
from app.models.workflow import Approval


def test_foreign_keys_are_enforced(session: Session) -> None:
    import uuid

    from sqlalchemy.exc import IntegrityError

    session.add(WorkflowEvent(workflow_id=uuid.uuid4(), seq=1, event_type="x"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_workflow_cascades(session: Session) -> None:
    from app.repositories import ApprovalRepository, EventRepository, WorkflowRepository

    wf = WorkflowRepository(session).create("req")
    EventRepository(session).append(wf.id, "started")
    ApprovalRepository(session).create_pending(wf.id, {"action": "restart_service"})
    session.flush()

    session.execute(delete(Workflow).where(Workflow.id == wf.id))

    assert session.scalar(select(func.count()).select_from(WorkflowEvent)) == 0
    assert session.scalar(select(func.count()).select_from(Approval)) == 0


def test_datetimes_round_trip_as_aware_utc(session: Session) -> None:
    from app.repositories import WorkflowRepository

    wf = WorkflowRepository(session).create("req")
    session.commit()
    session.expire_all()

    loaded = session.get_one(Workflow, wf.id)
    assert loaded.created_at.tzinfo is not None
    assert loaded.created_at.utcoffset() == timedelta(0)
    assert abs(datetime.now(UTC) - loaded.created_at) < timedelta(seconds=5)


def test_naive_datetime_is_rejected(session: Session) -> None:
    session.add(Workflow(request="r", created_at=datetime(2026, 1, 1)))
    with pytest.raises(Exception, match="naive datetime"):
        session.flush()


def test_session_scope_commits_on_success(engine: Engine) -> None:
    from app.repositories import WorkflowRepository

    factory = create_session_factory(engine)
    with session_scope(factory) as s:
        wf_id = WorkflowRepository(s).create("kept").id

    with session_scope(factory) as s:
        assert WorkflowRepository(s).get(wf_id).request == "kept"


def test_session_scope_rolls_back_on_error(engine: Engine) -> None:
    from app.repositories import WorkflowRepository

    factory = create_session_factory(engine)
    with pytest.raises(RuntimeError), session_scope(factory) as s:
        WorkflowRepository(s).create("discarded")
        raise RuntimeError("boom")

    with session_scope(factory) as s:
        assert s.scalar(select(func.count()).select_from(Workflow)) == 0


def test_file_backed_sqlite_persists_across_engines(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.repositories import WorkflowRepository

    url = f"sqlite:///{tmp_path / 'test.db'}"
    first = create_db_engine(url)
    Base.metadata.create_all(first)
    with session_scope(create_session_factory(first)) as s:
        wf_id = WorkflowRepository(s).create("durable").id
    first.dispose()

    second = create_db_engine(url)
    with session_scope(create_session_factory(second)) as s:
        assert WorkflowRepository(s).get(wf_id).request == "durable"
    second.dispose()
