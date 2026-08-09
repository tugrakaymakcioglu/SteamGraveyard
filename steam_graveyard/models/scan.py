"""Steam catalog and scan result models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from steam_graveyard.models.game import ContentType, validate_uint32


class CatalogEntry(BaseModel):
    appid: int
    name: str = Field(min_length=1, max_length=500)
    last_modified: int | None = None
    price_change_number: int | None = None
    content_type: ContentType = ContentType.GAME

    @field_validator("appid", mode="before")
    @classmethod
    def validate_appid(cls, value: int | str) -> int:
        return validate_uint32(value, label="AppID")


class ScanResult(BaseModel):
    scan_id: int
    started_at: datetime
    finished_at: datetime
    app_count: int = Field(ge=0)
    added: int = Field(ge=0)
    suspected: int = Field(ge=0)
    delisted: int = Field(ge=0)
    relisted: int = Field(ge=0)
    metadata_changed: int = Field(ge=0)
    snapshot_path: str
    snapshot_sha256: str
    metadata: dict[str, Any] = Field(default_factory=dict)
