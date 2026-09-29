"""Shared repository helpers."""

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Workflow


def insert_or_translate(
    session: Session, obj: Any, *, workflow_id: uuid.UUID, conflict_message: str
) -> None:
    """Insert ``obj`` inside a SAVEPOINT, translating integrity errors to domain errors.

    The SAVEPOINT means a failed insert does not invalidate the caller's transaction.
    An IntegrityError here is either a missing parent workflow or a uniqueness clash.
    """
    try:
        with session.begin_nested():
            session.add(obj)
            session.flush()
    except IntegrityError as exc:
        if session.get(Workflow, workflow_id) is None:
            raise NotFoundError(f"workflow {workflow_id} not found") from exc
        raise ConflictError(conflict_message) from exc
