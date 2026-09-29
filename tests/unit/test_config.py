import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"


def test_invalid_value_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "LOUD")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_database_url_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings(_env_file=None).database_url.startswith("sqlite")  # type: ignore[call-arg]
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./other.db")
    assert Settings(_env_file=None).database_url == "sqlite:///./other.db"  # type: ignore[call-arg]
