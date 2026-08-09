"""Event, source, and verification models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from steam_graveyard.models.game import ClaimStatus, utc_now, validate_uint32


class EventType(StrEnum):
    DISCOVERED = "DISCOVERED"
    DELISTED = "DELISTED"
    RELISTED = "RELISTED"
    CLAIMABLE_CONFIRMED = "CLAIMABLE_CONFIRMED"
    CLAIMABILITY_LOST = "CLAIMABILITY_LOST"
    METADATA_CHANGED = "METADATA_CHANGED"


class Source(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2000)
    kind: str = Field(default="official", min_length=1, max_length=50)
    retrieved_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Event(BaseModel):
    id: int | None = None
    appid: int
    event_type: EventType
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        self.appid = validate_uint32(self.appid, label="AppID")


class VerificationRecord(BaseModel):
    id: int | None = None
    appid: int
    verified_at: datetime = Field(default_factory=utc_now)
    claim_status: ClaimStatus
    method: str = Field(min_length=1, max_length=100)
    source_id: int
    notes: str | None = None

    def model_post_init(self, __context: Any) -> None:
        self.appid = validate_uint32(self.appid, label="AppID")
