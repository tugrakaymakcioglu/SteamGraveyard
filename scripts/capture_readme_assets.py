"""Capture deterministic README screenshots from the real Textual application."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from textual.widgets import Select

from steam_graveyard.app import SteamGraveyardApp
from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.services.credentials import CredentialResult


class _SessionCredentialStore:
    def load(self) -> str | None:
        return None

    def save(self, _api_key: str) -> CredentialResult:
        return CredentialResult(False, "Session-only screenshot credential store.")

    def delete(self) -> CredentialResult:
        return CredentialResult(True, "No screenshot credential was stored.")


async def _offline() -> bool:
    return False


async def capture(output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    with (
        patch("steam_graveyard.ui.main_screen.steam_is_reachable", new=_offline),
        TemporaryDirectory(prefix="steam-graveyard-readme-") as data_directory,
    ):
        settings = Settings(
            _env_file=None,
            data_dir=Path(data_directory),
            page_size=200,
            request_timeout=1,
        )
        repository = GameRepository(settings)
        repository.initialize()
        application = SteamGraveyardApp(
            repository,
            settings,
            credential_store=_SessionCredentialStore(),
            show_setup=True,
        )
        async with application.run_test(size=(120, 42)) as pilot:
            await pilot.pause()
            application.save_screenshot("onboarding.svg", path=str(output_directory))

            await pilot.press("escape")
            await pilot.pause()
            application.save_screenshot("catalog.svg", path=str(output_directory))

            category = application.screen.query_one("#category-select", Select)
            category.value = "demos"
            await pilot.pause()
            application.save_screenshot("demo-category.svg", path=str(output_directory))

            await pilot.press("enter")
            await pilot.pause()
            application.save_screenshot("detail.svg", path=str(output_directory))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/images/source"),
        help="Directory for the generated SVG screenshots.",
    )
    arguments = parser.parse_args()
    asyncio.run(capture(arguments.output.resolve()))


if __name__ == "__main__":
    main()
