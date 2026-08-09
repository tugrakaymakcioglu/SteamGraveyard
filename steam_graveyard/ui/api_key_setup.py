"""First-run setup screen for validating a Steam Web API key."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from typing import ClassVar

from pydantic import SecretStr
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Static

from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.errors import ConfigurationError
from steam_graveyard.services.credentials import (
    API_KEY_PAGE,
    API_TERMS_PAGE,
    CredentialStore,
    normalize_api_key,
)
from steam_graveyard.steam.catalog import SteamCatalogClient
from steam_graveyard.ui.main_screen import MainScreen


class ApiKeySetupScreen(Screen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("o", "open_key_page", "Open key page"),
        Binding("t", "open_terms", "API terms"),
        Binding("escape", "offline", "Browse offline"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        repository: GameRepository,
        settings: Settings,
        credential_store: CredentialStore,
        *,
        browser_opener: Callable[[str], bool] = webbrowser.open,
    ) -> None:
        super().__init__()
        self.repository = repository
        self.settings = settings
        self.credential_store = credential_store
        self.browser_opener = browser_opener

    def compose(self) -> ComposeResult:
        instructions = (
            "[bold #66d9ef]WELCOME TO STEAMGRAVEYARD 1.1[/]\n\n"
            "A Steam Web API key lets the app build a current game and DLC catalog. "
            "It does not give SteamGraveyard access to your password, purchases, or account.\n\n"
            "[bold]1.[/] Sign in to Steam in your browser.\n"
            f"[bold]2.[/] Open {API_KEY_PAGE} (press [bold]O[/]).\n"
            "[bold]3.[/] Register a user Web API key and accept Steam's API terms. For a "
            "local-only setup, use [bold]localhost[/] if the form accepts it; otherwise use a "
            "domain you control.\n"
            "[bold]4.[/] Copy the 32-character key and paste it below.\n\n"
            "[yellow]Never paste your Steam password here. The key is validated with one small, "
            "read-only request and stored in your operating system credential vault when "
            "available.[/]"
        )
        yield VerticalScroll(
            Static(instructions, id="setup-instructions"),
            Static("API KEY", id="api-key-label"),
            Input(
                placeholder="________________________________",
                password=True,
                max_length=32,
                id="api-key-input",
            ),
            Static("Paste your key, then press Enter.", id="setup-status"),
            Horizontal(
                Button("Validate & Build Catalog", id="validate-key", variant="success"),
                Button("Open Key Page", id="open-key-page", variant="primary"),
                Button("Browse Offline", id="browse-offline"),
                id="setup-actions",
            ),
            id="setup-panel",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#api-key-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self.action_validate_key()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "validate-key":
            self.action_validate_key()
        elif event.button.id == "open-key-page":
            self.action_open_key_page()
        elif event.button.id == "browse-offline":
            self.action_offline()

    @work(exclusive=True)
    async def action_validate_key(self) -> None:
        key_input = self.query_one("#api-key-input", Input)
        status = self.query_one("#setup-status", Static)
        button = self.query_one("#validate-key", Button)
        try:
            api_key = normalize_api_key(key_input.value)
        except ConfigurationError as exc:
            status.update(f"[red]{exc}[/]")
            return
        button.disabled = True
        status.update("[cyan]Checking the key with Steam...[/]")
        result = await SteamCatalogClient(
            api_key,
            timeout=self.settings.request_timeout,
        ).validate_api_key()
        if not result.valid:
            button.disabled = False
            status.update(f"[red]{result.message}[/]")
            return
        self.settings.steam_api_key = SecretStr(api_key)
        storage = self.credential_store.save(api_key)
        self.app.switch_screen(MainScreen(self.repository, self.settings, auto_update=True))
        self.app.notify(
            f"{result.message} {storage.message}",
            severity="information" if storage.persisted else "warning",
            timeout=7,
        )

    def _open_url(self, url: str) -> None:
        if not self.browser_opener(url):
            self.notify("Your browser could not be opened.", severity="warning")

    def action_open_key_page(self) -> None:
        self._open_url(API_KEY_PAGE)

    def action_open_terms(self) -> None:
        self._open_url(API_TERMS_PAGE)

    def action_offline(self) -> None:
        self.app.switch_screen(MainScreen(self.repository, self.settings))
        self.app.notify(
            "Offline browsing is available. Press R later to configure a key.", timeout=5
        )

    def action_quit(self) -> None:
        self.app.exit()
