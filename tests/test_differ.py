from __future__ import annotations

from datetime import timedelta

from steam_graveyard.models import CatalogEntry, DelistingStatus, EventType, Game
from steam_graveyard.services.differ import diff_catalog


def test_new_game_is_discovered(now) -> None:
    diff = diff_catalog([], [CatalogEntry(appid=10, name="New")], scanned_at=now, threshold=3)
    assert diff.added == 1
    assert diff.transitions[0].game.delisting_status is DelistingStatus.ACTIVE
    assert diff.transitions[0].event_types == (EventType.DISCOVERED,)


def test_delisting_requires_three_successful_absences(now) -> None:
    game = Game(appid=10, name="Gone", first_seen=now, last_seen=now)
    first = diff_catalog([game], [], scanned_at=now + timedelta(days=1), threshold=3)
    game = first.transitions[0].game
    assert game.delisting_status is DelistingStatus.SUSPECTED_DELISTING
    assert game.consecutive_missing_scans == 1
    second = diff_catalog([game], [], scanned_at=now + timedelta(days=2), threshold=3)
    game = second.transitions[0].game
    assert game.consecutive_missing_scans == 2
    third = diff_catalog([game], [], scanned_at=now + timedelta(days=3), threshold=3)
    game = third.transitions[0].game
    assert game.delisting_status is DelistingStatus.DELISTED
    assert third.transitions[0].event_types == (EventType.DELISTED,)


def test_relisted_game_resets_missing_count(now) -> None:
    old = Game(
        appid=10,
        name="Returned",
        delisting_status=DelistingStatus.DELISTED,
        consecutive_missing_scans=3,
        first_seen=now,
        last_seen=now,
    )
    diff = diff_catalog(
        [old], [CatalogEntry(appid=10, name="Returned")], scanned_at=now, threshold=3
    )
    game = diff.transitions[0].game
    assert game.delisting_status is DelistingStatus.RELISTED
    assert game.consecutive_missing_scans == 0
    assert diff.relisted == 1


def test_metadata_change_emits_event(now) -> None:
    old = Game(appid=10, name="Old Name", first_seen=now, last_seen=now)
    diff = diff_catalog(
        [old], [CatalogEntry(appid=10, name="New Name")], scanned_at=now, threshold=3
    )
    assert diff.metadata_changed == 1
    assert EventType.METADATA_CHANGED in diff.transitions[0].event_types
