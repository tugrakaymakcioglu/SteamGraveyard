from __future__ import annotations

from datetime import timedelta

import httpx
import pytest

from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.errors import CatalogError, ConfigurationError, SnapshotSafetyError
from steam_graveyard.models import CatalogEntry, Game
from steam_graveyard.services.scanner import update_catalog
from steam_graveyard.steam.catalog import SteamCatalogClient


def client_factory(handler):
    transport = httpx.MockTransport(handler)
    return lambda: httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_catalog_client_paginates() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(
                200,
                json={
                    "response": {
                        "apps": [{"appid": 1, "name": "One"}],
                        "have_more_results": True,
                        "last_appid": 1,
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "response": {
                    "apps": [{"appid": 2, "name": "Two"}],
                    "have_more_results": False,
                    "last_appid": 2,
                }
            },
        )

    client = SteamCatalogClient("secret", max_results=1, client_factory=client_factory(handler))
    entries = await client.fetch_all_games()
    assert [entry.appid for entry in entries] == [1, 2]
    assert requests == 2


@pytest.mark.asyncio
async def test_catalog_requires_api_key() -> None:
    with pytest.raises(ConfigurationError):
        await SteamCatalogClient(None).fetch_all_games()


@pytest.mark.asyncio
async def test_catalog_retries_rate_limit(monkeypatch) -> None:
    requests = 0

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("steam_graveyard.steam.catalog.asyncio.sleep", no_sleep)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "response": {
                    "apps": [{"appid": 1, "name": "One"}],
                    "have_more_results": False,
                }
            },
        )

    client = SteamCatalogClient("secret", client_factory=client_factory(handler))
    assert [entry.appid for entry in await client.fetch_all_games()] == [1]
    assert requests == 2


@pytest.mark.asyncio
async def test_catalog_rejects_non_advancing_cursor() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "response": {
                    "apps": [{"appid": 1, "name": "One"}],
                    "have_more_results": True,
                    "last_appid": 0,
                }
            },
        )

    client = SteamCatalogClient("secret", client_factory=client_factory(handler))
    with pytest.raises(CatalogError, match="cursor"):
        await client.fetch_all_games()


@pytest.mark.asyncio
async def test_catalog_error_never_exposes_api_key() -> None:
    secret = "do-not-log-this-key"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    client = SteamCatalogClient(
        secret,
        max_retries=0,
        client_factory=client_factory(handler),
    )
    with pytest.raises(CatalogError) as captured:
        await client.fetch_all_games()
    assert secret not in str(captured.value)


class FakeCatalogClient:
    def __init__(self, entries: list[CatalogEntry] | None = None, error: Exception | None = None):
        self.entries = entries or []
        self.error = error

    async def fetch_all_games(self) -> list[CatalogEntry]:
        if self.error:
            raise self.error
        return self.entries


@pytest.mark.asyncio
async def test_scanner_persists_snapshot_diff_and_exports(
    repository: GameRepository, settings: Settings, now
) -> None:
    repository.upsert_game(Game(appid=1, name="Old", first_seen=now, last_seen=now))
    result = await update_catalog(
        repository,
        settings,
        client=FakeCatalogClient([CatalogEntry(appid=2, name="New")]),  # type: ignore[arg-type]
        now=now + timedelta(days=1),
    )
    assert result.added == 1
    assert result.suspected == 1
    assert settings.export_dir.joinpath("games.json").exists()
    assert (
        settings.snapshot_dir.joinpath(result.snapshot_path).exists()
        or __import__("pathlib").Path(result.snapshot_path).exists()
    )


@pytest.mark.asyncio
async def test_failed_scan_does_not_change_game_state(
    repository: GameRepository, settings: Settings, now
) -> None:
    original = Game(appid=1, name="Safe", first_seen=now, last_seen=now)
    repository.upsert_game(original)
    with pytest.raises(CatalogError):
        await update_catalog(
            repository,
            settings,
            client=FakeCatalogClient(error=CatalogError("offline")),  # type: ignore[arg-type]
            now=now,
        )
    assert repository.get_game(1) == original


@pytest.mark.asyncio
async def test_snapshot_safety_guard(repository: GameRepository, settings: Settings, now) -> None:
    initial = [CatalogEntry(appid=index, name=f"Game {index}") for index in range(1, 11)]
    await update_catalog(
        repository,
        settings,
        client=FakeCatalogClient(initial),  # type: ignore[arg-type]
        now=now,
    )
    with pytest.raises(SnapshotSafetyError):
        await update_catalog(
            repository,
            settings,
            client=FakeCatalogClient(initial[:1]),  # type: ignore[arg-type]
            now=now + timedelta(days=1),
        )
