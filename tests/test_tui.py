from __future__ import annotations

from datetime import UTC, datetime

import pytest
from textual.widgets import DataTable, Input, Select, Static

from steam_graveyard.app import SteamGraveyardApp
from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import Game
from steam_graveyard.services.credentials import CredentialResult
from steam_graveyard.steam.catalog import ApiKeyValidationResult
from steam_graveyard.ui.api_key_setup import ApiKeySetupScreen
from steam_graveyard.ui.game_detail import GameDetailScreen
from steam_graveyard.ui.main_screen import MainScreen

VALID_KEY = "0123456789abcdef0123456789abcdef"


class FakeCredentialStore:
    def __init__(self) -> None:
        self.saved: str | None = None

    def load(self) -> str | None:
        return None

    def save(self, api_key: str) -> CredentialResult:
        self.saved = api_key
        return CredentialResult(True, "saved securely")

    def delete(self) -> CredentialResult:
        return CredentialResult(True, "deleted")


@pytest.mark.asyncio
async def test_tui_navigation_search_detail_and_offline(monkeypatch, settings: Settings) -> None:
    async def offline() -> bool:
        return False

    monkeypatch.setattr("steam_graveyard.ui.main_screen.steam_is_reachable", offline)
    repository = GameRepository(settings)
    repository.initialize()
    application = SteamGraveyardApp(repository, settings, show_setup=False)
    async with application.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = application.screen
        assert isinstance(screen, MainScreen)
        assert screen.query_one(DataTable).row_count == 4
        category = screen.query_one(Select)
        assert category.value == "all"
        category.value = "verified_free"
        await pilot.pause()
        assert screen.query_one(DataTable).row_count == 3
        category.value = "all"
        await pilot.pause()
        assert "OFFLINE MODE" in str(screen.query_one("#network-status", Static).render())

        await pilot.press("ctrl+s")
        search = screen.query_one(Input)
        assert search.display
        await pilot.press("l", "a", "w")
        await pilot.pause(0.2)
        assert screen.query_one(DataTable).row_count == 1

        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(application.screen, GameDetailScreen)
        await pilot.press("c")
        await pilot.press("escape")
        assert isinstance(application.screen, MainScreen)


@pytest.mark.asyncio
async def test_tui_loads_next_page(
    monkeypatch, settings: Settings, repository: GameRepository
) -> None:
    async def online() -> bool:
        return True

    monkeypatch.setattr("steam_graveyard.ui.main_screen.steam_is_reachable", online)
    now = datetime(2026, 8, 9, tzinfo=UTC)
    for appid in range(1, 27):
        repository.upsert_game(
            Game(appid=appid, name=f"Game {appid:02d}", first_seen=now, last_seen=now)
        )
    application = SteamGraveyardApp(repository, settings, show_setup=False)
    async with application.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = application.screen
        assert isinstance(screen, MainScreen)
        for _ in range(25):
            await pilot.press("down")
        assert screen.page_offset == 25
        assert len(screen.games) == 1


@pytest.mark.asyncio
async def test_first_run_validates_and_saves_api_key(monkeypatch, settings: Settings) -> None:
    async def valid_key(_client) -> ApiKeyValidationResult:
        return ApiKeyValidationResult(True, "Steam accepted the API key.")

    monkeypatch.setattr(
        "steam_graveyard.ui.api_key_setup.SteamCatalogClient.validate_api_key", valid_key
    )
    monkeypatch.setattr(MainScreen, "action_refresh_data", lambda _screen: None)
    repository = GameRepository(settings)
    repository.initialize()
    store = FakeCredentialStore()
    application = SteamGraveyardApp(
        repository,
        settings,
        credential_store=store,
        show_setup=True,
    )
    async with application.run_test(size=(120, 42)) as pilot:
        await pilot.pause()
        assert isinstance(application.screen, ApiKeySetupScreen)
        application.screen.query_one("#api-key-input", Input).value = VALID_KEY
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(application.screen, MainScreen)
        assert store.saved == VALID_KEY.upper()
        assert settings.steam_api_key is not None


@pytest.mark.asyncio
async def test_first_run_can_browse_offline(settings: Settings) -> None:
    repository = GameRepository(settings)
    repository.initialize()
    application = SteamGraveyardApp(
        repository,
        settings,
        credential_store=FakeCredentialStore(),
        show_setup=True,
    )
    async with application.run_test(size=(120, 42)) as pilot:
        await pilot.pause()
        assert isinstance(application.screen, ApiKeySetupScreen)
        application.screen.query_one("#api-key-input", Input).value = "too-short"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(application.screen, ApiKeySetupScreen)
        assert "32 hexadecimal" in str(
            application.screen.query_one("#setup-status", Static).render()
        )
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(application.screen, MainScreen)
