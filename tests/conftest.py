from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.database import create_db_engine
from app.models import Base


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Fresh in-memory SQLite database per test, schema created from the ORM metadata."""
    engine = create_db_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as session:
        yield session
