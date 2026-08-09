from __future__ import annotations

from datetime import timedelta

from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import ActivationMethod, ClaimStatus, Game, Source
from steam_graveyard.services.verifier import (
    apply_maintainer_verification,
    claim_label,
    verification_is_stale,
)


def test_maintainer_verification_records_source_and_activation(
    repository: GameRepository, now
) -> None:
    repository.upsert_game(Game(appid=12, name="Verified Later", first_seen=now, last_seen=now))
    updated = apply_maintainer_verification(
        repository,
        appid=12,
        claim_status=ClaimStatus.CLAIMABLE,
        source=Source(name="Official", url="https://example.test/official"),
        method="manual_official_source",
        verified_at=now,
        activation_method=ActivationMethod.INSTALL,
        activation_id="12",
    )
    assert updated.is_activation_allowed
    assert repository.all_verifications()[0].claim_status is ClaimStatus.CLAIMABLE
    assert repository.latest_events()[0].event_type.value == "CLAIMABLE_CONFIRMED"


def test_stale_label(repository: GameRepository, now) -> None:
    repository.upsert_game(Game(appid=12, name="Old Evidence", first_seen=now, last_seen=now))
    game = apply_maintainer_verification(
        repository,
        appid=12,
        claim_status=ClaimStatus.UNAVAILABLE,
        source=Source(name="Official", url="https://example.test/old"),
        method="manual_official_source",
        verified_at=now,
    )
    future = now + timedelta(days=31)
    assert verification_is_stale(game, stale_days=30, now=future)
    assert claim_label(game, stale_days=30, now=future) == "UNAVAILABLE (STALE)"
