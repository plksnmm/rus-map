from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str
    postgres_port: int = Field(ge=1, le=65535)
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    media_root: Path = Path("var/media")
    admin_session_ttl_hours: int = Field(default=12, ge=1, le=168)
    admin_session_cookie_name: str = "rus_map_admin_session"
    admin_csrf_cookie_name: str = "rus_map_admin_csrf"
    admin_cookie_path: str = Field(default="/", pattern=r"^/")
    admin_cookie_secure: bool = False
    admin_login_max_failures: int = Field(default=5, ge=2, le=20)
    admin_login_window_minutes: int = Field(default=15, ge=1, le=1440)
    admin_login_block_minutes: int = Field(default=15, ge=1, le=1440)

    @property
    def database_url(self) -> URL:
        """Build a SQLAlchemy URL without manual string concatenation."""
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings."""
    return Settings()
