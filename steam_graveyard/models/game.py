"""Core game and activation models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

UINT32_MAX = 4_294_967_295


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_uint32(value: int | str, *, label: str = "identifier") -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive uint32")
    if isinstance(value, str):
        if not value.isascii() or not value.isdigit():
            raise ValueError(f"{label} must contain ASCII digits only")
        value = int(value)
    if not 1 <= value <= UINT32_MAX:
        raise ValueError(f"{label} must be between 1 and {UINT32_MAX}")
    return value


class ClaimStatus(StrEnum):
    CLAIMABLE = "CLAIMABLE"
    OWNERS_ONLY = "OWNERS_ONLY"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


class DelistingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPECTED_DELISTING = "SUSPECTED_DELISTING"
    DELISTED = "DELISTED"
    RELISTED = "RELISTED"
    UNKNOWN = "UNKNOWN"


class ActivationMethod(StrEnum):
    INSTALL = "install"
    SUBSCRIPTION_INSTALL = "subscriptioninstall"
    NONE = "none"


class Game(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    appid: int
    name: str = Field(min_length=1, max_length=500)
    aliases: list[str] = Field(default_factory=list)
    type: str = Field(default="game", min_length=1, max_length=64)
    delisting_status: DelistingStatus = DelistingStatus.UNKNOWN
    claim_status: ClaimStatus = ClaimStatus.UNKNOWN
    activation_method: ActivationMethod = ActivationMethod.NONE
    activation_id: str | None = None
    first_seen: datetime = Field(default_factory=utc_now)
    last_seen: datetime = Field(default_factory=utc_now)
    delisted_at: datetime | None = None
    relisted_at: datetime | None = None
    last_verified: datetime | None = None
    verification_source_id: int | None = None
    popularity_score: float | None = Field(default=None, ge=0, le=100)
    historical_peak_players: int | None = Field(default=None, ge=0)
    review_count: int | None = Field(default=None, ge=0)
    review_score: float | None = Field(default=None, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    consecutive_missing_scans: int = Field(default=0, ge=0)

    @field_validator("appid", mode="before")
    @classmethod
    def validate_appid(cls, value: int | str) -> int:
        return validate_uint32(value, label="AppID")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("name cannot be blank")
        return normalized

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            alias = " ".join(raw.split())
            key = alias.casefold()
            if alias and key not in seen:
                seen.add(key)
                result.append(alias)
        return result

    @model_validator(mode="after")
    def validate_verification_and_activation(self) -> Game:
        if self.claim_status is not ClaimStatus.UNKNOWN and (
            self.last_verified is None or self.verification_source_id is None
        ):
            raise ValueError("non-UNKNOWN claim status requires verification time and source")
        if self.activation_method is ActivationMethod.NONE:
            if self.activation_id is not None:
                raise ValueError("activation_id must be null when activation_method is none")
            return self
        if self.claim_status not in {ClaimStatus.CLAIMABLE, ClaimStatus.OWNERS_ONLY}:
            raise ValueError("activation is allowed only for CLAIMABLE or OWNERS_ONLY games")
        if self.activation_id is None:
            raise ValueError("activation_id is required for an activation method")
        validate_uint32(self.activation_id, label="activation ID")
        return self

    @property
    def is_activation_allowed(self) -> bool:
        return (
            self.claim_status in {ClaimStatus.CLAIMABLE, ClaimStatus.OWNERS_ONLY}
            and self.activation_method is not ActivationMethod.NONE
            and self.activation_id is not None
        )
