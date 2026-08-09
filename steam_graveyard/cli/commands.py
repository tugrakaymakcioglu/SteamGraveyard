"""Typer CLI commands."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from steam_graveyard import __version__
from steam_graveyard.app import run_tui
from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.errors import SteamGraveyardError
from steam_graveyard.logging_config import configure_logging
from steam_graveyard.models import (
    ClaimStatus,
    ContentType,
    DelistingStatus,
    Game,
    validate_uint32,
)
from steam_graveyard.services.credentials import KeyringCredentialStore, hydrate_api_key
from steam_graveyard.services.exporter import DatasetExporter
from steam_graveyard.services.scanner import update_catalog
from steam_graveyard.services.search import SearchService
from steam_graveyard.services.verifier import claim_label
from steam_graveyard.steam.uri import build_steam_uri

app = typer.Typer(
    name="steam-graveyard",
    help="Discover and inspect forgotten Steam games from a local-first dataset.",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)
console = Console()


@dataclass(slots=True)
class AppContext:
    settings: Settings
    repository: GameRepository


def _context(data_dir: Path | None) -> AppContext:
    settings = Settings(data_dir=data_dir) if data_dir else Settings()
    configure_logging(settings)
    repository = GameRepository(settings)
    repository.initialize()
    return AppContext(settings, repository)


def _fail(exc: Exception, *, code: int = 1) -> None:
    console.print(f"[bold red]Error:[/] {exc}")
    raise typer.Exit(code) from None


def _games_table(games: list[Game]) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("AppID", justify="right")
    table.add_column("Game")
    table.add_column("Type")
    table.add_column("Catalog")
    table.add_column("Claim")
    table.add_column("Popularity", justify="right")
    for game in games:
        table.add_row(
            str(game.appid),
            game.name,
            game.type.value.upper(),
            game.delisting_status.value.replace("_", " "),
            game.claim_status.value.replace("_", " "),
            "N/A" if game.popularity_score is None else f"{game.popularity_score:.1f}",
        )
    return table


@app.callback()
def main(
    ctx: typer.Context,
    data_dir: Annotated[
        Path | None,
        typer.Option("--data-dir", help="Override the local data directory."),
    ] = None,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed version and exit."),
    ] = False,
) -> None:
    if version:
        console.print(f"SteamGraveyard {__version__}")
        raise typer.Exit()
    try:
        current = _context(data_dir)
    except SteamGraveyardError as exc:
        _fail(exc)
        return
    ctx.obj = current
    if ctx.invoked_subcommand is None:
        run_tui(settings=current.settings, repository=current.repository)


@app.command("search")
def search_command(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Game name, AppID, or alias.")],
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 50,
) -> None:
    current: AppContext = ctx.obj
    games = SearchService(current.repository).search(query, limit=limit)
    if not games:
        console.print("[yellow]No matching games found.[/]")
        return
    console.print(_games_table(games))


@app.command("game")
def game_command(ctx: typer.Context, appid: str) -> None:
    current: AppContext = ctx.obj
    try:
        parsed = validate_uint32(appid, label="AppID")
    except ValueError as exc:
        _fail(exc, code=2)
        return
    game = current.repository.get_game(parsed)
    if game is None:
        _fail(ValueError(f"AppID {parsed} is not in the local dataset."), code=2)
        return
    uri = build_steam_uri(game.activation_method, game.activation_id)
    console.print(f"[bold cyan]{game.name}[/]")
    console.print(f"AppID: {game.appid}")
    console.print(f"Content Type: {game.type.value.upper()}")
    console.print(f"Catalog Status: {game.delisting_status.value}")
    console.print(f"Claim Status: {claim_label(game, stale_days=current.settings.stale_days)}")
    console.print(
        f"Popularity: {game.popularity_score if game.popularity_score is not None else 'N/A'}"
    )
    console.print(f"Activation: {uri or 'Not available'}")


@app.command("latest")
def latest_command(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 20,
) -> None:
    current: AppContext = ctx.obj
    events = current.repository.latest_events(limit=limit)
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Time")
    table.add_column("Event")
    table.add_column("AppID", justify="right")
    table.add_column("Game")
    for event in events:
        table.add_row(
            event.timestamp.isoformat(), event.event_type.value, str(event.appid), event.game_name
        )
    console.print(table)


@app.command("claimable")
def claimable_command(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 200,
) -> None:
    current: AppContext = ctx.obj
    console.print(
        _games_table(
            current.repository.list_games(limit=limit, claim_status=ClaimStatus.CLAIMABLE.value)
        )
    )


@app.command("category")
def category_command(
    ctx: typer.Context,
    category: Annotated[
        str,
        typer.Argument(help="One of: games, dlc, demos, free, delisted."),
    ],
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 200,
) -> None:
    current: AppContext = ctx.obj
    normalized = category.strip().casefold()
    filters: dict[str, str] = {}
    if normalized == "games":
        filters["content_type"] = ContentType.GAME.value
    elif normalized == "dlc":
        filters["content_type"] = ContentType.DLC.value
    elif normalized == "demos":
        filters["content_type"] = ContentType.DEMO.value
    elif normalized == "free":
        filters["claim_status"] = ClaimStatus.CLAIMABLE.value
    elif normalized == "delisted":
        filters["delisting_status"] = DelistingStatus.DELISTED.value
    else:
        _fail(ValueError("category must be games, dlc, demos, free, or delisted"), code=2)
        return
    console.print(
        _games_table(
            current.repository.list_games(
                limit=limit,
                claim_status=filters.get("claim_status"),
                delisting_status=filters.get("delisting_status"),
                content_type=filters.get("content_type"),
            )
        )
    )


@app.command("delisted")
def delisted_command(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 200,
) -> None:
    current: AppContext = ctx.obj
    console.print(
        _games_table(
            current.repository.list_games(
                limit=limit, delisting_status=DelistingStatus.DELISTED.value
            )
        )
    )


@app.command("update")
def update_command(ctx: typer.Context) -> None:
    current: AppContext = ctx.obj
    hydrate_api_key(current.settings)
    try:
        result = asyncio.run(update_catalog(current.repository, current.settings))
    except SteamGraveyardError as exc:
        _fail(exc, code=4)
        return
    console.print(
        f"[green]Updated {result.app_count:,} games and DLC items.[/] "
        f"Added {result.added}, suspected {result.suspected}, "
        f"delisted {result.delisted}, relisted {result.relisted}."
    )


@app.command("setup")
def setup_command(ctx: typer.Context) -> None:
    """Open the guided API key setup again."""
    current: AppContext = ctx.obj
    run_tui(
        settings=current.settings,
        repository=current.repository,
        force_setup=True,
    )


@app.command("forget-key")
def forget_key_command() -> None:
    """Remove the API key from the operating system credential vault."""
    result = KeyringCredentialStore().delete()
    style = "green" if result.persisted else "yellow"
    console.print(f"[{style}]{result.message}[/]")
    console.print(
        "[dim]Keys supplied through STEAM_API_KEY or .env are not changed by this command.[/]"
    )


@app.command("export")
def export_command(ctx: typer.Context) -> None:
    current: AppContext = ctx.obj
    try:
        paths = DatasetExporter(current.repository, current.settings.export_dir).export_all()
    except (OSError, ValueError) as exc:
        _fail(exc, code=3)
        return
    for path in paths:
        console.print(f"[green]Wrote[/] {path}")
