import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import EventLevel, WorkflowEvent
from app.repositories import EventRepository, WorkflowRepository
from app.repositories._helpers import insert_or_translate


def test_seq_increments_per_workflow(session: Session) -> None:
    wf_a = WorkflowRepository(session).create("a")
    wf_b = WorkflowRepository(session).create("b")
    events = EventRepository(session)

    assert [events.append(wf_a.id, "e").seq for _ in range(3)] == [1, 2, 3]
    assert events.append(wf_b.id, "e").seq == 1  # independent counter
    assert events.append(wf_a.id, "e").seq == 4


def test_fields_and_payload_round_trip(session: Session) -> None:
    wf = WorkflowRepository(session).create("a")
    events = EventRepository(session)
    events.append(
        wf.id,
        "node_failed",
        node="execute_actions",
        level=EventLevel.ERROR,
        payload={"error": "timeout", "attempt": 2},
    )
    session.commit()
    session.expire_all()

    (loaded,) = events.list_for_workflow(wf.id)
    assert loaded.event_type == "node_failed"
    assert loaded.node == "execute_actions"
    assert loaded.level == EventLevel.ERROR
    assert loaded.payload == {"error": "timeout", "attempt": 2}


def test_list_supports_after_seq_and_limit(session: Session) -> None:
    wf = WorkflowRepository(session).create("a")
    events = EventRepository(session)
    for i in range(5):
        events.append(wf.id, f"e{i}")

    assert [e.seq for e in events.list_for_workflow(wf.id)] == [1, 2, 3, 4, 5]
    assert [e.seq for e in events.list_for_workflow(wf.id, after_seq=2, limit=2)] == [3, 4]
    assert events.list_for_workflow(wf.id, after_seq=5) == []


def test_unknown_workflow_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        EventRepository(session).append(uuid.uuid4(), "e")


def test_duplicate_seq_is_a_conflict_and_session_stays_usable(session: Session) -> None:
    wf = WorkflowRepository(session).create("a")
    events = EventRepository(session)
    events.append(wf.id, "first")

    duplicate = WorkflowEvent(workflow_id=wf.id, seq=1, event_type="dup")
    with pytest.raises(ConflictError):
        insert_or_translate(session, duplicate, workflow_id=wf.id, conflict_message="dup seq")

    # The SAVEPOINT rolled back only the failed insert; earlier work is intact.
    assert events.append(wf.id, "second").seq == 2
    assert len(events.list_for_workflow(wf.id)) == 2
