from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from alembic import command
from app.core.database import create_db_engine
from app.models import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {"workflows", "workflow_events", "tool_executions", "approvals"}


def _alembic_config(db_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["database_url"] = db_url
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'migrations.db'}"


def test_upgrade_creates_expected_tables(db_url: str) -> None:
    command.upgrade(_alembic_config(db_url), "head")
    engine = create_db_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert tables >= EXPECTED_TABLES
    assert "alembic_version" in tables


def test_migrations_match_orm_models(db_url: str) -> None:
    """Fails if someone changes a model without adding a migration."""
    command.upgrade(_alembic_config(db_url), "head")
    engine = create_db_engine(db_url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        diff = compare_metadata(context, Base.metadata)
    engine.dispose()
    assert diff == []


def test_downgrade_to_base_removes_tables(db_url: str) -> None:
    config = _alembic_config(db_url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    engine = create_db_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert not (EXPECTED_TABLES & tables)


def test_migrated_schema_enforces_one_pending_approval(db_url: str) -> None:
    """The partial unique index must exist in the *migrated* schema, not just the ORM."""
    from sqlalchemy.orm import Session

    from app.core.errors import ConflictError
    from app.repositories import ApprovalRepository, WorkflowRepository

    command.upgrade(_alembic_config(db_url), "head")
    engine = create_db_engine(db_url)
    with Session(engine) as session:
        wf = WorkflowRepository(session).create("r")
        approvals = ApprovalRepository(session)
        approvals.create_pending(wf.id, {"action": "restart_service"})
        with pytest.raises(ConflictError):
            approvals.create_pending(wf.id, {"action": "restart_service"})
    engine.dispose()
