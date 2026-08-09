from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import (
    ActivationMethod,
    ClaimStatus,
    DelistingStatus,
    Game,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        data_dir=tmp_path,
        page_size=25,
        request_timeout=1,
    )


@pytest.fixture
def repository(settings: Settings) -> GameRepository:
    repo = GameRepository(settings)
    repo.initialize(seed=False)
    return repo


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 9, tzinfo=UTC)


@pytest.fixture
def claimable_game(now: datetime) -> Game:
    return Game(
        appid=123,
        name="Verified Game",
        aliases=["VG"],
        delisting_status=DelistingStatus.DELISTED,
        claim_status=ClaimStatus.CLAIMABLE,
        activation_method=ActivationMethod.INSTALL,
        activation_id="123",
        first_seen=now,
        last_seen=now,
        last_verified=now,
        verification_source_id=1,
    )
