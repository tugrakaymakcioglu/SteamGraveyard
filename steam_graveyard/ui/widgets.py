"""Reusable TUI presentation helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rich.text import Text

from steam_graveyard.models import ClaimStatus, Game

STATUS_SYMBOLS = {
    ClaimStatus.CLAIMABLE: ("✓ CLAIMABLE", "bold green"),
    ClaimStatus.OWNERS_ONLY: ("◆ OWNERS ONLY", "yellow"),
    ClaimStatus.UNKNOWN: ("? UNKNOWN", "dim"),
    ClaimStatus.UNAVAILABLE: ("✕ UNAVAILABLE", "red"),
}


def status_text(game: Game, *, stale_days: int) -> Text:
    label, style = STATUS_SYMBOLS[game.claim_status]
    if game.last_verified is not None:
        verified = game.last_verified
        if verified.tzinfo is None:
            verified = verified.replace(tzinfo=UTC)
        if datetime.now(UTC) - verified > timedelta(days=stale_days):
            label += " (STALE)"
            style = "bold yellow"
    return Text(label, style=style)


def date_text(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
