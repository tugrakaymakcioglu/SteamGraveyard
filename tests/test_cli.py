from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from steam_graveyard.cli.commands import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "SteamGraveyard 1.1.0" in result.stdout


def test_cli_search_and_game_bootstrap_seed(tmp_path: Path) -> None:
    search = runner.invoke(app, ["--data-dir", str(tmp_path), "search", "lawbrekers"])
    assert search.exit_code == 0
    assert "LawBreakers" in search.stdout
    detail = runner.invoke(app, ["--data-dir", str(tmp_path), "game", "350280"])
    assert detail.exit_code == 0
    assert "Claim Status: UNKNOWN" in detail.stdout


def test_cli_invalid_appid_is_friendly(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "game", "not-an-id"])
    assert result.exit_code == 2
    assert "Error:" in result.stdout
    assert "Traceback" not in result.stdout


def test_cli_update_without_key_is_friendly(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("steam_graveyard.cli.commands.hydrate_api_key", lambda _settings: False)
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "update"])
    assert result.exit_code == 4
    assert "STEAM_API_KEY is required" in result.stdout


def test_cli_category_is_validated(tmp_path: Path) -> None:
    valid = runner.invoke(app, ["--data-dir", str(tmp_path), "category", "games"])
    assert valid.exit_code == 0
    assert "LawBreakers" in valid.stdout
    invalid = runner.invoke(app, ["--data-dir", str(tmp_path), "category", "unknown"])
    assert invalid.exit_code == 2
    assert "category must be" in invalid.stdout


def test_cli_export(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "export"])
    assert result.exit_code == 0
    assert tmp_path.joinpath("export", "games.json").exists()
