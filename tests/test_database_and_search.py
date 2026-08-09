from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.errors import DatabaseCorruptionError
from steam_graveyard.models import DelistingStatus, Game, Source
from steam_graveyard.services.search import SearchService


def test_repository_bootstraps_packaged_seed(settings: Settings) -> None:
    repo = GameRepository(settings)
    repo.initialize()
    game = repo.get_game(350280)
    assert game is not None
    assert game.name == "LawBreakers"
    assert game.claim_status.value == "UNKNOWN"


def test_repository_crud_stats_and_indexes(repository: GameRepository, now: datetime) -> None:
    repository.upsert_game(
        Game(
            appid=1,
            name="First",
            popularity_score=10,
            first_seen=now,
            last_seen=now,
        )
    )
    repository.upsert_game(
        Game(
            appid=2,
            name="Second",
            popularity_score=90,
            delisting_status=DelistingStatus.DELISTED,
            first_seen=now,
            last_seen=now,
        )
    )
    assert [game.appid for game in repository.list_games()] == [2, 1]
    assert repository.stats().game_count == 2
    assert repository.list_games(delisting_status="DELISTED")[0].appid == 2


def test_source_round_trip(repository: GameRepository) -> None:
    source = Source(name="Valve", url="https://example.test/source", kind="official")
    source_id = repository.upsert_source(source)
    stored = repository.get_source(source_id)
    assert stored is not None
    assert stored.url == source.url


def test_search_by_name_alias_appid_and_typo(repository: GameRepository, now: datetime) -> None:
    repository.upsert_game(
        Game(
            appid=350280,
            name="LawBreakers",
            aliases=["Project BlueStreak"],
            first_seen=now,
            last_seen=now,
        )
    )
    repository.upsert_game(Game(appid=10, name="Another Game", first_seen=now, last_seen=now))
    search = SearchService(repository)
    assert search.search("law")[0].appid == 350280
    assert search.search("bluestreak")[0].appid == 350280
    assert search.search("350280")[0].appid == 350280
    assert search.search("lawbrekers")[0].appid == 350280
    search.invalidate()
    assert search.search("no-match-at-all") == []


def test_corrupt_database_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "steam_graveyard.db"
    path.write_bytes(b"not a sqlite database")
    repo = GameRepository(Settings(_env_file=None, data_dir=tmp_path))
    with pytest.raises(DatabaseCorruptionError):
        repo.initialize()
    assert path.read_bytes() == b"not a sqlite database"
