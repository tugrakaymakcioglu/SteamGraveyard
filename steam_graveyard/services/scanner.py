"""End-to-end catalog scan orchestration."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.errors import SnapshotSafetyError, SteamGraveyardError
from steam_graveyard.models import CatalogEntry, ScanResult
from steam_graveyard.services.differ import diff_catalog
from steam_graveyard.services.exporter import DatasetExporter
from steam_graveyard.steam.catalog import SteamCatalogClient


def _write_snapshot(
    entries: list[CatalogEntry], directory: Path, timestamp: datetime
) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        {
            "schema_version": 1,
            "scanned_at": timestamp.isoformat(),
            "apps": [entry.model_dump(mode="json") for entry in entries],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    destination = directory / f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{digest[:12]}.json.gz"
    descriptor, temp_name = tempfile.mkstemp(prefix=".snapshot-", suffix=".tmp", dir=directory)
    os.close(descriptor)
    try:
        with gzip.open(temp_name, "wb") as handle:
            handle.write(raw)
        os.replace(temp_name, destination)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return destination, digest


async def update_catalog(
    repository: GameRepository,
    settings: Settings,
    *,
    client: SteamCatalogClient | None = None,
    now: datetime | None = None,
) -> ScanResult:
    started_at = now or datetime.now(UTC)
    scan_id = repository.begin_scan(started_at)
    catalog_client = client or SteamCatalogClient(
        settings.steam_api_key.get_secret_value() if settings.steam_api_key else None,
        timeout=settings.request_timeout,
    )
    try:
        entries = await catalog_client.fetch_all_games()
        previous_count = repository.last_successful_scan_count() or repository.stats().game_count
        if previous_count and len(entries) < previous_count * settings.minimum_snapshot_ratio:
            raise SnapshotSafetyError(
                f"Snapshot rejected: {len(entries)} apps is below "
                f"{settings.minimum_snapshot_ratio:.0%} of the previous {previous_count}."
            )
        finished_at = datetime.now(UTC) if now is None else now
        snapshot_path, digest = _write_snapshot(entries, settings.snapshot_dir, finished_at)
        diff = diff_catalog(
            repository.all_games(),
            entries,
            scanned_at=finished_at,
            threshold=settings.delisting_threshold,
        )
        repository.apply_scan(
            scan_id,
            diff,
            finished_at=finished_at,
            app_count=len(entries),
            snapshot_path=snapshot_path,
            snapshot_sha256=digest,
        )
        DatasetExporter(repository, settings.export_dir).export_all(generated_at=finished_at)
        return ScanResult(
            scan_id=scan_id,
            started_at=started_at,
            finished_at=finished_at,
            app_count=len(entries),
            added=diff.added,
            suspected=diff.suspected,
            delisted=diff.delisted,
            relisted=diff.relisted,
            metadata_changed=diff.metadata_changed,
            snapshot_path=str(snapshot_path),
            snapshot_sha256=digest,
        )
    except Exception as exc:
        repository.fail_scan(scan_id, finished_at=datetime.now(UTC), error=str(exc))
        if isinstance(exc, SteamGraveyardError):
            raise
        raise
