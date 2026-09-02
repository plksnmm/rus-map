from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from rus_map.config import Settings


def test_settings_build_database_url_safely() -> None:
    settings = Settings(
        postgres_host="127.0.0.1",
        postgres_port=15432,
        postgres_db="rus_map",
        postgres_user="rus_map",
        postgres_password=SecretStr("p@ss:/word"),
    )

    database_url = settings.database_url

    assert database_url.drivername == "postgresql+asyncpg"
    assert database_url.host == "127.0.0.1"
    assert database_url.port == 15432
    assert database_url.database == "rus_map"
    assert database_url.username == "rus_map"
    assert database_url.password == "p@ss:/word"
    assert "p@ss:/word" not in database_url.render_as_string(
        hide_password=True,
    )


def test_settings_load_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("POSTGRES_HOST", "database.example")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "test_database")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")

    settings = Settings()

    assert settings.postgres_host == "database.example"
    assert settings.postgres_port == 5432
    assert settings.postgres_db == "test_database"
    assert settings.postgres_user == "test_user"
    assert settings.postgres_password.get_secret_value() == "test_password"


def test_settings_require_database_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    for variable in (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ):
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ValidationError):
        Settings()
