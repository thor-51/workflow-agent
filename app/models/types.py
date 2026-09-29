"""Custom column types."""

from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import DateTime, Dialect, Enum
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes on every backend.

    SQLite discards tzinfo; Postgres keeps it. This normalizes both so callers
    always get aware UTC values back, and refuses naive datetimes on write.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime is not allowed; use timezone-aware UTC")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def enum_column(enum_cls: type[PyEnum]) -> Enum:
    """Enum stored as a portable VARCHAR of the enum *values* (no native PG enum type)."""

    def _values(e: type[PyEnum]) -> list[Any]:
        return [member.value for member in e]

    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=_values,
        validate_strings=True,
    )
