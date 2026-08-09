"""Main catalog screen with paged rows and live fuzzy search."""

from __future__ import annotations

from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Input, Select, Static

from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.errors import SteamGraveyardError
from steam_graveyard.models import ClaimStatus, ContentType, DelistingStatus, Game
from steam_graveyard.services.connectivity import steam_is_reachable
from steam_graveyard.services.scanner import update_catalog
from steam_graveyard.services.search import SearchService
from steam_graveyard.ui.game_detail import GameDetailScreen
from steam_graveyard.ui.widgets import date_text, status_text


class MainScreen(Screen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "move_up", "Up", show=False, priority=True),
        Binding("down", "move_down", "Down", show=False, priority=True),
        Binding("enter", "open_selected", "Select", priority=True),
        Binding("ctrl+s", "search", "Search", priority=True),
        Binding("escape", "escape", "Back / Clear", priority=True),
        Binding("r", "refresh_data", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self, repository: GameRepository, settings: Settings, *, auto_update: bool = False
    ) -> None:
        super().__init__()
        self.repository = repository
        self.settings = settings
        self.search_service = SearchService(repository)
        self.page_offset = 0
        self.search_text = ""
        self.games: list[Game] = []
        self.category = "all"
        self.auto_update = auto_update
        self._search_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Static("STEAM GRAVEYARD", id="title")
        yield Static("Discover forgotten Steam games.", id="subtitle")
        yield Static(id="dataset-stats")
        yield Select(
            [
                ("All content", "all"),
                ("Games", "games"),
                ("DLC", "dlc"),
                ("Demos (curated)", "demos"),
                ("Verified free", "verified_free"),
                ("Delisted", "delisted"),
            ],
            value="all",
            allow_blank=False,
            id="category-select",
        )
        yield Input(placeholder="Search by game, AppID, or alias", id="search-input")
        yield DataTable(id="games-table", cursor_type="row", zebra_stripes=True)
        yield Static("LOCAL DATA", id="network-status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#games-table", DataTable)
        table.add_columns("Rank", "Title", "Type", "Status", "Popularity", "Last Verified")
        self.query_one("#search-input", Input).display = False
        self._load_page()
        self._check_connectivity()
        if self.auto_update and self.settings.steam_api_key is not None:
            self.action_refresh_data()

    def _load_page(self) -> None:
        if self.search_text:
            games = self.search_service.search(
                self.search_text,
                limit=self.settings.page_size,
                offset=self.page_offset,
            )
        else:
            filters: dict[str, str] = {}
            if self.category == "games":
                filters["content_type"] = ContentType.GAME.value
            elif self.category == "dlc":
                filters["content_type"] = ContentType.DLC.value
            elif self.category == "demos":
                filters["content_type"] = ContentType.DEMO.value
            elif self.category == "verified_free":
                filters["claim_status"] = ClaimStatus.CLAIMABLE.value
            elif self.category == "delisted":
                filters["delisting_status"] = DelistingStatus.DELISTED.value
            games = self.repository.list_games(
                limit=self.settings.page_size,
                offset=self.page_offset,
                **filters,
            )
        if not games and self.page_offset > 0:
            self.page_offset = max(0, self.page_offset - self.settings.page_size)
            return
        self.games = games
        table = self.query_one("#games-table", DataTable)
        table.clear(columns=False)
        for index, game in enumerate(games, start=self.page_offset + 1):
            popularity = "N/A" if game.popularity_score is None else f"{game.popularity_score:.1f}"
            table.add_row(
                str(index),
                game.name,
                game.type.value.upper(),
                status_text(game, stale_days=self.settings.stale_days),
                popularity,
                date_text(game.last_verified),
                key=str(game.appid),
            )
        if games:
            table.move_cursor(row=0, column=0)
        stats = self.repository.stats()
        updated = date_text(stats.last_update)
        mode = (
            f"Search: {self.search_text}" if self.search_text else self.category.replace("_", " ")
        )
        self.query_one("#dataset-stats", Static).update(
            f"{stats.game_count:,} items  •  {stats.claimable_count:,} verified free  •  "
            f"{stats.dlc_count:,} DLC  •  {stats.demo_count:,} demos  •  "
            f"{stats.delisted_count:,} delisted  •  Updated {updated}  •  {mode}"
        )

    @work(exclusive=True)
    async def _check_connectivity(self) -> None:
        reachable = await steam_is_reachable()
        widget = self.query_one("#network-status", Static)
        widget.update("ONLINE • LOCAL DATA" if reachable else "OFFLINE MODE • LOCAL DATA AVAILABLE")
        widget.set_class(not reachable, "offline")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return
        if self._search_timer is not None:
            self._search_timer.stop()
        self._search_timer = self.set_timer(0.12, self._apply_search)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "category-select" or not isinstance(event.value, str):
            return
        self.category = event.value
        self.page_offset = 0
        self._load_page()

    def _apply_search(self) -> None:
        self.search_text = " ".join(self.query_one("#search-input", Input).value.split())
        self.page_offset = 0
        self._load_page()

    def action_search(self) -> None:
        search = self.query_one("#search-input", Input)
        search.display = True
        search.focus()

    def action_escape(self) -> None:
        search = self.query_one("#search-input", Input)
        if search.display:
            search.value = ""
            search.display = False
            self.search_text = ""
            self.page_offset = 0
            self._load_page()

    def action_move_down(self) -> None:
        table = self.query_one("#games-table", DataTable)
        if not self.games:
            return
        if table.cursor_row >= len(self.games) - 1:
            old_offset = self.page_offset
            self.page_offset += self.settings.page_size
            self._load_page()
            if self.page_offset == old_offset:
                table.move_cursor(row=len(self.games) - 1, column=0)
        else:
            table.move_cursor(row=table.cursor_row + 1, column=0)

    def action_move_up(self) -> None:
        table = self.query_one("#games-table", DataTable)
        if not self.games:
            return
        if table.cursor_row == 0 and self.page_offset > 0:
            self.page_offset = max(0, self.page_offset - self.settings.page_size)
            self._load_page()
            table.move_cursor(row=max(0, len(self.games) - 1), column=0)
        else:
            table.move_cursor(row=max(0, table.cursor_row - 1), column=0)

    def action_open_selected(self) -> None:
        table = self.query_one("#games-table", DataTable)
        if not self.games or table.cursor_row >= len(self.games):
            return
        self.app.push_screen(
            GameDetailScreen(self.games[table.cursor_row], stale_days=self.settings.stale_days)
        )

    def action_quit(self) -> None:
        self.app.exit()

    @work(exclusive=True)
    async def action_refresh_data(self) -> None:
        if self.settings.steam_api_key is None:
            from steam_graveyard.services.credentials import KeyringCredentialStore
            from steam_graveyard.ui.api_key_setup import ApiKeySetupScreen

            credential_store = getattr(self.app, "credential_store", KeyringCredentialStore())
            self.app.switch_screen(
                ApiKeySetupScreen(self.repository, self.settings, credential_store)
            )
            return
        self.notify("Catalog update started…", timeout=2)
        try:
            result = await update_catalog(self.repository, self.settings)
        except SteamGraveyardError as exc:
            self.notify(str(exc), severity="warning", timeout=8)
            return
        self.search_service.invalidate()
        self.page_offset = 0
        self._load_page()
        self.notify(f"Catalog updated: {result.app_count:,} games and DLC items.", timeout=5)
