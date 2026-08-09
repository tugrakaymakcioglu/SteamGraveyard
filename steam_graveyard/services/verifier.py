"""Safety checks for maintainer-supplied claim verification records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import (
    ActivationMethod,
    ClaimStatus,
    EventType,
    Game,
    Source,
    VerificationRecord,
)


def verification_is_stale(game: Game, *, stale_days: int, now: datetime | None = None) -> bool:
    if game.claim_status is ClaimStatus.UNKNOWN or game.last_verified is None:
        return False
    current = now or datetime.now(UTC)
    verified = game.last_verified
    if verified.tzinfo is None:
        verified = verified.replace(tzinfo=UTC)
    return current - verified > timedelta(days=stale_days)


def claim_label(game: Game, *, stale_days: int, now: datetime | None = None) -> str:
    label = game.claim_status.value.replace("_", " ")
    return (
        f"{label} (STALE)" if verification_is_stale(game, stale_days=stale_days, now=now) else label
    )


def apply_maintainer_verification(
    repository: GameRepository,
    *,
    appid: int,
    claim_status: ClaimStatus,
    source: Source,
    method: str,
    verified_at: datetime,
    notes: str | None = None,
    activation_method: ActivationMethod = ActivationMethod.NONE,
    activation_id: str | None = None,
) -> Game:
    """Apply a source-backed maintainer decision without contacting a Steam account."""
    current = repository.get_game(appid)
    if current is None:
        raise ValueError(f"AppID {appid} is not in the local catalog.")
    source_id = repository.upsert_source(source)
    updated = Game.model_validate(
        {
            **current.model_dump(),
            "claim_status": claim_status,
            "last_verified": verified_at,
            "verification_source_id": source_id,
            "activation_method": activation_method,
            "activation_id": activation_id,
        }
    )
    event_type: EventType | None = None
    if claim_status is ClaimStatus.CLAIMABLE and current.claim_status is not ClaimStatus.CLAIMABLE:
        event_type = EventType.CLAIMABLE_CONFIRMED
    elif (
        current.claim_status is ClaimStatus.CLAIMABLE and claim_status is not ClaimStatus.CLAIMABLE
    ):
        event_type = EventType.CLAIMABILITY_LOST
    record = VerificationRecord(
        appid=appid,
        verified_at=verified_at,
        claim_status=claim_status,
        method=method,
        source_id=source_id,
        notes=notes,
    )
    return repository.record_verification(updated, source, record, event_type=event_type)
