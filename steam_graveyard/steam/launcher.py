"""Cross-platform Steam URI and clipboard integration."""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pyperclip

from steam_graveyard.models import Game
from steam_graveyard.steam.uri import build_steam_uri


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    available: bool
    message: str


@dataclass(frozen=True, slots=True)
class LaunchResult:
    success: bool
    uri: str | None
    message: str


@dataclass(frozen=True, slots=True)
class CopyResult:
    success: bool
    uri: str | None
    message: str


def is_steam_available(*, system: str | None = None) -> AvailabilityResult:
    """Best-effort check for an installed Steam URI handler."""
    current = system or platform.system()
    if current == "Windows":
        try:
            # Loading winreg dynamically keeps cross-platform type checking honest:
            # its public attributes only exist in typeshed when targeting Windows.
            winreg = cast(Any, importlib.import_module("winreg"))
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"steam\Shell\Open\Command"):
                return AvailabilityResult(True, "Steam URI handler is registered.")
        except (FileNotFoundError, OSError):
            return AvailabilityResult(False, "Steam URI handler is not registered.")
    if current == "Linux":
        if shutil.which("xdg-open") is None:
            return AvailabilityResult(False, "xdg-open is not installed.")
        try:
            handler = (
                subprocess.run(
                    ["xdg-mime", "query", "default", "x-scheme-handler/steam"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if shutil.which("xdg-mime")
                else None
            )
        except (OSError, subprocess.SubprocessError):
            handler = None
        if handler is not None and handler.returncode == 0 and handler.stdout.strip():
            return AvailabilityResult(True, "Steam URI handler is registered.")
        if shutil.which("steam"):
            return AvailabilityResult(True, "Steam executable is available.")
        return AvailabilityResult(False, "Steam URI handler was not found.")
    if current == "Darwin":
        installed = (
            Path("/Applications/Steam.app").exists()
            or Path.home().joinpath("Applications", "Steam.app").exists()
        )
        return AvailabilityResult(
            installed, "Steam is available." if installed else "Steam.app not found."
        )
    return AvailabilityResult(False, f"Unsupported platform: {current}")


def open_in_steam(
    game: Game,
    *,
    system: str | None = None,
    startfile: Callable[[str], Any] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    check_availability: Callable[..., AvailabilityResult] = is_steam_available,
) -> LaunchResult:
    if not game.is_activation_allowed:
        return LaunchResult(
            False,
            None,
            "Activation is disabled because this game is not verified as claimable or owners-only.",
        )
    uri = build_steam_uri(game.activation_method, game.activation_id)
    assert uri is not None
    current = system or platform.system()
    availability = check_availability(system=current)
    if not availability.available:
        return LaunchResult(False, uri, availability.message)
    try:
        if current == "Windows":
            opener = startfile or getattr(os, "startfile", None)
            if opener is None:
                return LaunchResult(False, uri, "Windows URI opener is unavailable.")
            opener(uri)
        elif current == "Linux":
            runner(["xdg-open", uri], check=True, capture_output=True, text=True)
        elif current == "Darwin":
            runner(["open", uri], check=True, capture_output=True, text=True)
        else:
            return LaunchResult(False, uri, f"Unsupported platform: {current}")
    except (OSError, subprocess.SubprocessError) as exc:
        return LaunchResult(False, uri, f"Steam could not be opened: {exc}")
    return LaunchResult(True, uri, "Steam accepted the URI request.")


def copy_steam_uri(
    game: Game,
    *,
    copier: Callable[[str], None] = pyperclip.copy,
) -> CopyResult:
    if not game.is_activation_allowed:
        return CopyResult(
            False,
            None,
            "No verified Steam activation URI is available for this game.",
        )
    uri = build_steam_uri(game.activation_method, game.activation_id)
    assert uri is not None
    try:
        copier(uri)
    except pyperclip.PyperclipException as exc:
        return CopyResult(False, uri, f"Clipboard is unavailable: {exc}")
    except OSError as exc:
        return CopyResult(False, uri, f"Clipboard operation failed: {exc}")
    return CopyResult(True, uri, "Steam URI copied to the clipboard.")
