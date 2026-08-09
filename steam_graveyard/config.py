"""Application configuration and cross-platform data paths."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_path
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _checkout_root() -> Path | None:
    package_root = Path(__file__).resolve().parent.parent
    if (package_root / "pyproject.toml").is_file():
        return package_root
    return None


def default_data_dir() -> Path:
    """Use the repository data directory for a checkout and user data for a wheel."""
    checkout = _checkout_root()
    if checkout is not None:
        return checkout / "data"
    return user_data_path("SteamGraveyard", ensure_exists=False)


class Settings(BaseSettings):
    """Validated settings sourced from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    steam_api_key: SecretStr | None = Field(default=None, validation_alias="STEAM_API_KEY")
    data_dir: Path = Field(
        default_factory=default_data_dir, validation_alias="STEAM_GRAVEYARD_DATA_DIR"
    )
    delisting_threshold: int = Field(
        default=3,
        ge=2,
        le=20,
        validation_alias="STEAM_GRAVEYARD_DELISTING_THRESHOLD",
    )
    stale_days: int = Field(
        default=30,
        ge=1,
        le=3650,
        validation_alias="STEAM_GRAVEYARD_STALE_DAYS",
    )
    page_size: int = Field(
        default=200,
        ge=25,
        le=1000,
        validation_alias="STEAM_GRAVEYARD_PAGE_SIZE",
    )
    minimum_snapshot_ratio: float = Field(
        default=0.8,
        gt=0,
        le=1,
        validation_alias="STEAM_GRAVEYARD_MIN_SNAPSHOT_RATIO",
    )
    log_level: str = Field(default="INFO", validation_alias="STEAM_GRAVEYARD_LOG_LEVEL")
    request_timeout: float = Field(
        default=20.0,
        ge=1,
        le=120,
        validation_alias="STEAM_GRAVEYARD_REQUEST_TIMEOUT",
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def expand_data_dir(cls, value: object) -> object:
        if isinstance(value, str):
            return Path(value).expanduser()
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized

    @property
    def database_path(self) -> Path:
        return self.data_dir / "steam_graveyard.db"

    @property
    def export_dir(self) -> Path:
        return self.data_dir / "export"

    @property
    def snapshot_dir(self) -> Path:
        return self.data_dir / "snapshots"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
