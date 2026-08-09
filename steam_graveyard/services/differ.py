"""Pure catalog diff and delisting confirmation logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from steam_graveyard.models import CatalogEntry, DelistingStatus, EventType, Game


@dataclass(frozen=True, slots=True)
class GameTransition:
    game: Game
    event_types: tuple[EventType, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DiffSummary:
    transitions: tuple[GameTransition, ...]
    added: int
    suspected: int
    delisted: int
    relisted: int
    metadata_changed: int


def diff_catalog(
    existing_games: list[Game],
    current_entries: list[CatalogEntry],
    *,
    scanned_at: datetime,
    threshold: int,
) -> DiffSummary:
    """Return durable state transitions for one successful, complete catalog scan."""
    if threshold < 2:
        raise ValueError("delisting threshold must be at least 2")

    existing = {game.appid: game for game in existing_games}
    current = {entry.appid: entry for entry in current_entries}
    transitions: list[GameTransition] = []
    added = suspected = delisted = relisted = metadata_changed = 0

    for appid, entry in current.items():
        old = existing.get(appid)
        if old is None:
            game = Game(
                appid=appid,
                name=entry.name,
                delisting_status=DelistingStatus.ACTIVE,
                first_seen=scanned_at,
                last_seen=scanned_at,
                metadata={
                    "last_modified": entry.last_modified,
                    "price_change_number": entry.price_change_number,
                },
            )
            transitions.append(GameTransition(game, (EventType.DISCOVERED,)))
            added += 1
            continue

        events: list[EventType] = []
        updates: dict[str, object] = {
            "last_seen": scanned_at,
            "consecutive_missing_scans": 0,
        }
        if old.delisting_status is DelistingStatus.DELISTED:
            updates["delisting_status"] = DelistingStatus.RELISTED
            updates["relisted_at"] = scanned_at
            events.append(EventType.RELISTED)
            relisted += 1
        elif old.delisting_status in {
            DelistingStatus.UNKNOWN,
            DelistingStatus.SUSPECTED_DELISTING,
        }:
            updates["delisting_status"] = DelistingStatus.ACTIVE

        metadata = dict(old.metadata)
        metadata.update(
            {
                "last_modified": entry.last_modified,
                "price_change_number": entry.price_change_number,
            }
        )
        updates["metadata"] = metadata
        if old.name != entry.name:
            updates["name"] = entry.name
            events.append(EventType.METADATA_CHANGED)
            metadata_changed += 1
        transitions.append(GameTransition(old.model_copy(update=updates), tuple(events)))

    for appid, old in existing.items():
        if appid in current or old.delisting_status is DelistingStatus.DELISTED:
            continue
        missing = old.consecutive_missing_scans + 1
        updates = {"consecutive_missing_scans": missing}
        missing_events: tuple[EventType, ...] = ()
        if missing >= threshold:
            updates["delisting_status"] = DelistingStatus.DELISTED
            updates["delisted_at"] = scanned_at
            missing_events = (EventType.DELISTED,)
            delisted += 1
        else:
            updates["delisting_status"] = DelistingStatus.SUSPECTED_DELISTING
            suspected += 1
        transitions.append(GameTransition(old.model_copy(update=updates), missing_events))

    return DiffSummary(
        transitions=tuple(transitions),
        added=added,
        suspected=suspected,
        delisted=delisted,
        relisted=relisted,
        metadata_changed=metadata_changed,
    )
