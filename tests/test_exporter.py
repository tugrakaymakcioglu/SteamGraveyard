from __future__ import annotations

import csv
import json
from datetime import datetime

from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import DelistingStatus, Game, Source
from steam_graveyard.services.exporter import DatasetExporter


def test_export_writes_programmatic_formats(
    repository: GameRepository, settings, now: datetime
) -> None:
    repository.upsert_game(Game(appid=2, name="B", first_seen=now, last_seen=now))
    repository.upsert_game(Game(appid=1, name="A", first_seen=now, last_seen=now))
    json_path, csv_path, events_path = DatasetExporter(repository, settings.export_dir).export_all(
        generated_at=now
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert [game["appid"] for game in payload["games"]] == [1, 2]
    assert payload["sources"] == []
    assert payload["verification_history"] == []

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["appid"] for row in rows] == ["1", "2"]
    assert {row["schema_version"] for row in rows} == {"1"}
    assert {row["generated_at"] for row in rows} == {now.isoformat()}
    assert events_path.read_text(encoding="utf-8") == ""


def test_export_can_rebuild_persistent_scan_state(settings, now: datetime) -> None:
    first = GameRepository(settings)
    first.initialize(seed=False)
    source_id = first.upsert_source(Source(name="Official", url="https://example.test/source"))
    first.upsert_game(
        Game(
            appid=55,
            name="Persistent",
            delisting_status=DelistingStatus.SUSPECTED_DELISTING,
            consecutive_missing_scans=2,
            first_seen=now,
            last_seen=now,
            metadata={"source_id": source_id},
        )
    )
    DatasetExporter(first, settings.export_dir).export_all(generated_at=now)
    settings.database_path.unlink()

    rebuilt = GameRepository(settings)
    rebuilt.initialize()
    restored = rebuilt.get_game(55)
    assert restored is not None
    assert restored.consecutive_missing_scans == 2
    assert restored.delisting_status is DelistingStatus.SUSPECTED_DELISTING
