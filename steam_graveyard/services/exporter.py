"""Stable JSON, CSV, and JSONL dataset exports."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from io import TextIOBase
from pathlib import Path

from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import Game

SCHEMA_VERSION = 1


def _game_dict(game: Game) -> dict[str, object]:
    payload = game.model_dump(mode="json")
    payload["metadata_json"] = payload.pop("metadata")
    return payload


def _atomic_write(
    path: Path, writer: Callable[[TextIOBase], None], *, newline: str | None = "\n"
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline=newline) as handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


class DatasetExporter:
    def __init__(self, repository: GameRepository, export_dir: Path) -> None:
        self.repository = repository
        self.export_dir = export_dir

    def export_all(self, *, generated_at: datetime | None = None) -> tuple[Path, Path, Path]:
        timestamp = (generated_at or datetime.now(UTC)).isoformat()
        games = self.repository.all_games()
        events = self.repository.latest_events(limit=1_000_000)
        sources = self.repository.all_sources()
        sources_by_id = {source.id: source for source in sources}
        verifications = self.repository.all_verifications()
        json_path = self.export_dir / "games.json"
        csv_path = self.export_dir / "games.csv"
        events_path = self.export_dir / "events.jsonl"

        def write_json(handle: TextIOBase) -> None:
            json.dump(
                {
                    "schema_version": SCHEMA_VERSION,
                    "generated_at": timestamp,
                    "games": [_game_dict(game) for game in games],
                    "sources": [source.model_dump(mode="json") for source in sources],
                    "verification_history": [
                        record.model_dump(mode="json") for record in verifications
                    ],
                },
                handle,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            handle.write("\n")

        def write_csv(handle: TextIOBase) -> None:
            fieldnames = [
                "schema_version",
                "generated_at",
                "appid",
                "name",
                "aliases",
                "type",
                "delisting_status",
                "claim_status",
                "activation_method",
                "activation_id",
                "first_seen",
                "last_seen",
                "delisted_at",
                "relisted_at",
                "last_verified",
                "verification_source_id",
                "verification_source_name",
                "verification_source_url",
                "popularity_score",
                "historical_peak_players",
                "review_count",
                "review_score",
                "consecutive_missing_scans",
                "metadata_json",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for game in games:
                row = _game_dict(game)
                row["schema_version"] = SCHEMA_VERSION
                row["generated_at"] = timestamp
                source = sources_by_id.get(game.verification_source_id)
                row["verification_source_name"] = source.name if source else None
                row["verification_source_url"] = source.url if source else None
                row["aliases"] = json.dumps(row["aliases"], ensure_ascii=False)
                row["metadata_json"] = json.dumps(
                    row["metadata_json"], ensure_ascii=False, sort_keys=True
                )
                writer.writerow(row)

        def write_events(handle: TextIOBase) -> None:
            for event in reversed(events):
                handle.write(
                    json.dumps(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "id": event.id,
                            "appid": event.appid,
                            "game_name": event.game_name,
                            "event_type": event.event_type.value,
                            "timestamp": event.timestamp.isoformat(),
                            "metadata": event.metadata,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )

        _atomic_write(json_path, write_json)
        _atomic_write(csv_path, write_csv, newline="")
        _atomic_write(events_path, write_events)
        return json_path, csv_path, events_path
