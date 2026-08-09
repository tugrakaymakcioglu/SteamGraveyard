from __future__ import annotations

from datetime import UTC, datetime

import pytest
from textual.widgets import DataTable, Input, Static

from steam_graveyard.app import SteamGraveyardApp
from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import Game
from steam_graveyard.ui.game_detail import GameDetailScreen
from steam_graveyard.ui.main_screen import MainScreen


@pytest.mark.asyncio
async def test_tui_navigation_search_detail_and_offline(monkeypatch, settings: Settings) -> None:
    async def offline() -> bool:
        return False

    monkeypatch.setattr("steam_graveyard.ui.main_screen.steam_is_reachable", offline)
    repository = GameRepository(settings)
    repository.initialize()
    application = SteamGraveyardApp(repository, settings)
    async with application.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = application.screen
        assert isinstance(screen, MainScreen)
        assert screen.query_one(DataTable).row_count == 1
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
    application = SteamGraveyardApp(repository, settings)
    async with application.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = application.screen
        assert isinstance(screen, MainScreen)
        for _ in range(25):
            await pilot.press("down")
        assert screen.page_offset == 25
        assert len(screen.games) == 1
