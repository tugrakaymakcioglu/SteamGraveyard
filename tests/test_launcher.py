from __future__ import annotations

import subprocess

import pyperclip

from steam_graveyard.models import Game
from steam_graveyard.steam.launcher import (
    AvailabilityResult,
    copy_steam_uri,
    is_steam_available,
    open_in_steam,
)


def _available(**_: object) -> AvailabilityResult:
    return AvailabilityResult(True, "ok")


def test_windows_launcher_uses_registered_uri_handler(claimable_game: Game) -> None:
    opened: list[str] = []
    result = open_in_steam(
        claimable_game,
        system="Windows",
        startfile=opened.append,
        check_availability=_available,
    )
    assert result.success
    assert opened == ["steam://install/123"]


def test_linux_launcher_uses_argument_list(claimable_game: Game) -> None:
    calls: list[list[str]] = []

    def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    result = open_in_steam(
        claimable_game,
        system="Linux",
        runner=runner,
        check_availability=_available,
    )
    assert result.success
    assert calls == [["xdg-open", "steam://install/123"]]


def test_launcher_refuses_unverified_game() -> None:
    result = open_in_steam(Game(appid=7, name="Unknown"))
    assert not result.success
    assert result.uri is None


def test_launcher_reports_missing_handler(claimable_game: Game) -> None:
    result = open_in_steam(
        claimable_game,
        system="Linux",
        check_availability=lambda **_: AvailabilityResult(False, "missing"),
    )
    assert not result.success
    assert result.message == "missing"


def test_copy_uri_uses_injected_clipboard(claimable_game: Game) -> None:
    copied: list[str] = []
    result = copy_steam_uri(claimable_game, copier=copied.append)
    assert result.success
    assert copied == ["steam://install/123"]


def test_copy_uri_handles_clipboard_failure(claimable_game: Game) -> None:
    def fail(_: str) -> None:
        raise pyperclip.PyperclipException("no clipboard")

    result = copy_steam_uri(claimable_game, copier=fail)
    assert not result.success
    assert "unavailable" in result.message


def test_unknown_platform_is_unavailable() -> None:
    result = is_steam_available(system="Plan9")
    assert not result.available
    assert "Unsupported" in result.message
