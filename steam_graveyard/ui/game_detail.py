"""Textual game detail screen."""

from __future__ import annotations

from typing import ClassVar

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Static

from steam_graveyard.models import Game
from steam_graveyard.services.verifier import claim_label
from steam_graveyard.steam.launcher import copy_steam_uri, open_in_steam
from steam_graveyard.steam.uri import build_steam_uri
from steam_graveyard.ui.widgets import date_text


class GameDetailScreen(Screen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "open_steam", "Add / Open in Steam"),
        Binding("c", "copy_uri", "Copy URI"),
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
            f"[bold]Catalog Status:[/] {self.game.delisting_status.value.replace('_', ' ')}\n"
            f"[bold]Claim Status:[/] {claim_label(self.game, stale_days=self.stale_days)}\n"
            f"[bold]Popularity:[/] "
            f"{self.game.popularity_score if self.game.popularity_score is not None else '—'}\n"
            f"[bold]Last Verified:[/] {date_text(self.game.last_verified)}\n"
            f"[bold]Verification Source:[/] {safe_source}\n"
            f"[bold]Delisted Date:[/] {date_text(self.game.delisted_at)}\n"
            f"[bold]Relisted Date:[/] {date_text(self.game.relisted_at)}\n\n"
            f"[bold]Activation Method[/]\n{activation}\n\n"
            "[dim]Steam always decides whether a license or installation is available.[/]"
        )
        yield Container(Static(body, id="detail-body"), id="detail-container")
        yield Footer()

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
