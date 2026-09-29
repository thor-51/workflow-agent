"""Engine and session management.

Repositories never commit. The caller (a service, from Phase 5 on) owns the
transaction boundary and uses ``session_scope`` to commit or roll back.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool

from app.core.config import get_settings

_IN_MEMORY_URLS = {"sqlite://", "sqlite:///:memory:"}


def create_db_engine(url: str, *, echo: bool = False) -> Engine:
    """Create an engine for ``url`` (SQLite for dev/tests, Postgres in production)."""
    if not url.startswith("sqlite"):
        return create_engine(url, echo=echo, pool_pre_ping=True)

    kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
    if url in _IN_MEMORY_URLS:
        # One shared connection, otherwise every checkout would see a new empty DB.
        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, echo=echo, **kwargs)

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: sqlite3.Connection, _record: ConnectionPoolEntry) -> None:
        # Take transaction control away from pysqlite (its legacy behavior breaks
        # SAVEPOINT), and enable FK enforcement, which SQLite leaves off by default.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    @event.listens_for(engine, "begin")
    def _on_begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN")

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False so returned ORM objects stay readable after commit.
    return sessionmaker(engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Transactional scope: commit on success, roll back on any exception."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@lru_cache
def get_engine() -> Engine:
    return create_db_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())
