"""Textual game detail screen."""

from __future__ import annotations

from typing import ClassVar

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from steam_graveyard.models import Game
from steam_graveyard.services.links import (
    open_steamdb_page,
    open_store_page,
    steamdb_app_url,
)
from steam_graveyard.services.verifier import claim_label
from steam_graveyard.steam.launcher import copy_steam_uri, open_in_steam
from steam_graveyard.steam.uri import build_steam_uri
from steam_graveyard.ui.widgets import date_text


class GameDetailScreen(Screen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "open_steam", "Add / Open in Steam"),
        Binding("c", "copy_uri", "Copy URI"),
        Binding("d", "open_steamdb", "SteamDB"),
        Binding("s", "open_store", "Steam Store"),
        Binding("escape", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, game: Game, *, stale_days: int) -> None:
        super().__init__()
        self.game = game
        self.stale_days = stale_days

    def compose(self) -> ComposeResult:
        uri = build_steam_uri(self.game.activation_method, self.game.activation_id)
        activation = uri or "Not available — claimability has not been verified."
        source = self.game.metadata.get("source_url")
        if source is None and self.game.verification_source_id is not None:
            source = f"Local source #{self.game.verification_source_id}"
        safe_source = escape(str(source)) if source is not None else "N/A"
        body = (
            f"[bold #66d9ef]{escape(self.game.name.upper())}[/]\n\n"
            f"[bold]AppID:[/] {self.game.appid}\n"
            f"[bold]Content Type:[/] {self.game.type.value.upper()}\n"
            f"[bold]Catalog Status:[/] {self.game.delisting_status.value.replace('_', ' ')}\n"
            f"[bold]Claim Status:[/] {claim_label(self.game, stale_days=self.stale_days)}\n"
            f"[bold]Popularity:[/] "
            f"{self.game.popularity_score if self.game.popularity_score is not None else '—'}\n"
            f"[bold]Last Verified:[/] {date_text(self.game.last_verified)}\n"
            f"[bold]Verification Source:[/] {safe_source}\n"
            f"[bold]Delisted Date:[/] {date_text(self.game.delisted_at)}\n"
            f"[bold]Relisted Date:[/] {date_text(self.game.relisted_at)}\n\n"
            f"[bold]Activation Method[/]\n{activation}\n\n"
            f"[bold]SteamDB Research:[/] {steamdb_app_url(self.game.appid)}\n\n"
            "[dim]Steam always decides whether a license or installation is available.[/]"
        )
        yield Container(
            Static(body, id="detail-body"),
            Horizontal(
                Button(
                    "Add / Open in Steam",
                    id="open-steam",
                    variant="success",
                    disabled=not self.game.is_activation_allowed,
                ),
                Button("Steam Store", id="open-store", variant="primary"),
                Button("Research on SteamDB", id="open-steamdb"),
                id="detail-actions",
            ),
            id="detail-container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-steam":
            self.action_open_steam()
        elif event.button.id == "open-store":
            self.action_open_store()
        elif event.button.id == "open-steamdb":
            self.action_open_steamdb()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()

    def action_open_steam(self) -> None:
        result = open_in_steam(self.game)
        self.notify(result.message, severity="information" if result.success else "warning")

    def action_copy_uri(self) -> None:
        result = copy_steam_uri(self.game)
        self.notify(result.message, severity="information" if result.success else "warning")

    def action_open_steamdb(self) -> None:
        result = open_steamdb_page(self.game)
        self.notify(result.message, severity="information" if result.success else "warning")

    def action_open_store(self) -> None:
        result = open_store_page(self.game)
        self.notify(result.message, severity="information" if result.success else "warning")
