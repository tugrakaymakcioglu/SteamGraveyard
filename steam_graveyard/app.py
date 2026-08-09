"""Textual application entry point."""

from __future__ import annotations

from textual.app import App

from steam_graveyard.config import Settings, get_settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.logging_config import configure_logging
from steam_graveyard.ui.main_screen import MainScreen


class SteamGraveyardApp(App[None]):
    TITLE = "SteamGraveyard"
    SUB_TITLE = "Discover forgotten Steam games."
    CSS = """
    Screen {
        background: #080b10;
        color: #d7dee9;
    }
    #title {
        color: #66d9ef;
        text-style: bold;
        text-align: center;
        padding-top: 1;
        height: 3;
    }
    #subtitle {
        color: #8b949e;
        text-align: center;
        height: 2;
    }
    #dataset-stats {
        background: #101620;
        color: #b5c1d1;
        padding: 0 2;
        height: 3;
        content-align: left middle;
    }
    #search-input {
        margin: 1 2 0 2;
        border: tall #66d9ef;
        background: #0d121a;
    }
    #games-table {
        height: 1fr;
        margin: 1 2 0 2;
        background: #080b10;
    }
    DataTable > .datatable--header {
        background: #151d29;
        color: #66d9ef;
        text-style: bold;
    }
    DataTable > .datatable--cursor {
        background: #253348;
        color: #ffffff;
    }
    #network-status {
        height: 1;
        padding: 0 2;
        color: #5fd7af;
        text-align: right;
    }
    #network-status.offline {
        color: #ffaf5f;
    }
    GameDetailScreen {
        align: center middle;
    }
    #detail-container {
        width: 76;
        max-width: 95%;
        height: auto;
        max-height: 90%;
        margin: 0;
        padding: 2 4;
        border: round #66d9ef;
        background: #0d121a;
    }
    #detail-body {
        height: auto;
    }
    Footer {
        background: #101620;
    }
    """

    def __init__(self, repository: GameRepository, settings: Settings) -> None:
        super().__init__()
        self.repository = repository
        self.settings = settings

    def on_mount(self) -> None:
        self.push_screen(MainScreen(self.repository, self.settings))


def run_tui(
    *,
    settings: Settings | None = None,
    repository: GameRepository | None = None,
) -> None:
    current_settings = settings or get_settings()
    configure_logging(current_settings)
    current_repository = repository or GameRepository(current_settings)
    current_repository.initialize()
    SteamGraveyardApp(current_repository, current_settings).run()
