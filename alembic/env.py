"""Alembic environment. The database URL comes from app settings (DATABASE_URL)."""

from alembic import context
from app.core.config import get_settings
from app.core.database import create_db_engine
from app.models import Base
from app.models.types import UTCDateTime

config = context.config

# Programmatic callers (tests) can pass config.attributes["configure_logger"] = False
# so Alembic does not reconfigure the process's logging.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    from logging.config import fileConfig

    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    """Keep migrations independent of app code: render our custom type as its plain SQL type."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def _database_url() -> str:
    override = config.attributes.get("database_url")
    return str(override) if override else get_settings().database_url


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _database_url()
    engine = create_db_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
            compare_type=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
