"""Allow-listed research and store links opened only on explicit user action."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from dataclasses import dataclass

from steam_graveyard.models import Game, validate_uint32


@dataclass(frozen=True, slots=True)
class BrowserResult:
    success: bool
    url: str
    message: str


def steamdb_app_url(appid: int | str) -> str:
    return f"https://steamdb.info/app/{validate_uint32(appid, label='AppID')}/"


def steam_store_url(appid: int | str) -> str:
    return f"https://store.steampowered.com/app/{validate_uint32(appid, label='AppID')}/"


def _open(
    url: str,
    *,
    label: str,
    opener: Callable[[str], bool],
) -> BrowserResult:
    try:
        opened = opener(url)
    except OSError as exc:
        return BrowserResult(False, url, f"{label} could not be opened: {exc}")
    return BrowserResult(
        opened,
        url,
        f"Opened {label}." if opened else f"Your browser could not open {label}.",
    )


def open_steamdb_page(
    game: Game, *, opener: Callable[[str], bool] = webbrowser.open
) -> BrowserResult:
    """Open a SteamDB research page without fetching or scraping it."""
    return _open(steamdb_app_url(game.appid), label="SteamDB", opener=opener)


def open_store_page(
    game: Game, *, opener: Callable[[str], bool] = webbrowser.open
) -> BrowserResult:
    return _open(steam_store_url(game.appid), label="the Steam Store", opener=opener)
