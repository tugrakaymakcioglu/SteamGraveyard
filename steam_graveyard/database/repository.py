"""SQLite persistence boundary for SteamGraveyard."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from steam_graveyard.config import Settings
from steam_graveyard.database.migrations import migrate
from steam_graveyard.errors import DatabaseCorruptionError, DatabaseError
from steam_graveyard.models import (
    ClaimStatus,
    Event,
    EventType,
    Game,
    Source,
    VerificationRecord,
)
from steam_graveyard.services.differ import DiffSummary

SEED_REVISION = 2


@dataclass(frozen=True, slots=True)
class DatasetStats:
    game_count: int
    claimable_count: int
    dlc_count: int
    demo_count: int
    delisted_count: int
    last_update: datetime | None


@dataclass(frozen=True, slots=True)
class SearchRecord:
    appid: int
    name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EventRow:
    id: int
    appid: int
    game_name: str
    event_type: EventType
    timestamp: datetime
    metadata: dict[str, Any]


def _datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class GameRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = settings.database_path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path, timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
        except sqlite3.DatabaseError as exc:
            if connection is not None:
                connection.close()
            if self.path.exists() and any(
                marker in str(exc).casefold() for marker in ("not a database", "malformed")
            ):
                raise DatabaseCorruptionError(
                    f"Database at {self.path} is unreadable: {exc}. "
                    "It was not deleted or overwritten."
                ) from exc
            raise DatabaseError(f"Could not open database at {self.path}: {exc}") from exc
        try:
            assert connection is not None
            yield connection
        finally:
            connection.close()

    def initialize(self, *, seed: bool = True) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.connection() as connection:
                migrate(connection)
                check = connection.execute("PRAGMA quick_check").fetchone()[0]
                if check != "ok":
                    raise DatabaseCorruptionError(
                        f"Database integrity check failed at {self.path}: {check}. "
                        "Keep the file for recovery and choose a new data directory."
                    )
                count = int(connection.execute("SELECT COUNT(*) FROM games").fetchone()[0])
                if seed:
                    applied = connection.execute(
                        "SELECT 1 FROM seed_revisions WHERE revision = ?", (SEED_REVISION,)
                    ).fetchone()
                    if applied is None:
                        if count == 0:
                            self._load_seed(connection)
                        else:
                            self._merge_packaged_seed(connection)
                        with connection:
                            connection.execute(
                                "INSERT INTO seed_revisions(revision, applied_at) VALUES (?, ?)",
                                (SEED_REVISION, datetime.now(UTC).isoformat()),
                            )
        except DatabaseCorruptionError:
            raise
        except sqlite3.DatabaseError as exc:
            raise DatabaseCorruptionError(
                f"Database at {self.path} is unreadable: {exc}. It was not deleted or overwritten."
            ) from exc

    def _load_seed(self, connection: sqlite3.Connection) -> None:
        exported_seed = self.settings.export_dir / "games.json"
        seed_file = (
            exported_seed
            if exported_seed.is_file()
            else files("steam_graveyard.resources").joinpath("games.json")
        )
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
        with connection:
            source_ids: dict[str, int] = {}
            source_id_map: dict[int, int] = {}
            for raw_source in payload.get("sources", []):
                source = Source.model_validate(raw_source)
                database_id = self._upsert_source(connection, source)
                source_ids[source.url] = database_id
                if source.id is not None:
                    source_id_map[source.id] = database_id
            for original_game in payload.get("games", []):
                game = self._seed_game(original_game, source_ids, source_id_map)
                self._upsert_game(connection, game)
            for raw_verification in payload.get("verification_history", []):
                verification = VerificationRecord.model_validate(raw_verification)
                source_id = source_id_map.get(verification.source_id, verification.source_id)
                connection.execute(
                    """
                    INSERT INTO verification_history(
                        appid, verified_at, claim_status, method, source_id, notes
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        verification.appid,
                        verification.verified_at.isoformat(),
                        verification.claim_status.value,
                        verification.method,
                        source_id,
                        verification.notes,
                    ),
                )
            raw_events = list(payload.get("events", []))
            exported_events = self.settings.export_dir / "events.jsonl"
            if exported_seed.is_file() and exported_events.is_file():
                raw_events = [
                    json.loads(line)
                    for line in exported_events.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            for raw_event in raw_events:
                self._insert_event(connection, Event.model_validate(raw_event))

    @staticmethod
    def _seed_game(
        original_game: object,
        source_ids: dict[str, int],
        source_id_map: dict[int, int],
    ) -> Game:
        if not isinstance(original_game, dict):
            raise DatabaseError("The packaged seed contains an invalid game record.")
        raw_game = dict(original_game)
        source_url = raw_game.pop("verification_source_url", None)
        if source_url and raw_game.get("claim_status") != "UNKNOWN":
            raw_game["verification_source_id"] = source_ids[str(source_url)]
        old_source_id = raw_game.get("verification_source_id")
        if old_source_id is not None:
            raw_game["verification_source_id"] = source_id_map.get(
                int(old_source_id), int(old_source_id)
            )
        if "metadata_json" in raw_game:
            raw_game["metadata"] = raw_game.pop("metadata_json")
        return Game.model_validate(raw_game)

    def _merge_packaged_seed(self, connection: sqlite3.Connection) -> None:
        """Apply a newer curated seed without replacing existing catalog history."""
        seed_file = files("steam_graveyard.resources").joinpath("games.json")
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
        with connection:
            source_ids: dict[str, int] = {}
            source_id_map: dict[int, int] = {}
            for raw_source in payload.get("sources", []):
                source = Source.model_validate(raw_source)
                database_id = self._upsert_source(connection, source)
                source_ids[source.url] = database_id
                if source.id is not None:
                    source_id_map[source.id] = database_id

            for original_game in payload.get("games", []):
                candidate = self._seed_game(original_game, source_ids, source_id_map)
                row = connection.execute(
                    "SELECT * FROM games WHERE appid = ?", (candidate.appid,)
                ).fetchone()
                if row is None:
                    self._upsert_game(connection, candidate)
                    continue

                existing = self._row_to_game(row)
                updates: dict[str, object] = {}
                aliases = list(dict.fromkeys([*existing.aliases, *candidate.aliases]))
                if aliases != existing.aliases:
                    updates["aliases"] = aliases
                metadata = {**candidate.metadata, **existing.metadata}
                if metadata != existing.metadata:
                    updates["metadata"] = metadata
                candidate_is_newer = candidate.last_verified is not None and (
                    existing.last_verified is None
                    or candidate.last_verified > existing.last_verified
                )
                if candidate.claim_status is not ClaimStatus.UNKNOWN and candidate_is_newer:
                    updates.update(
                        {
                            "type": candidate.type,
                            "claim_status": candidate.claim_status,
                            "activation_method": candidate.activation_method,
                            "activation_id": candidate.activation_id,
                            "last_verified": candidate.last_verified,
                            "verification_source_id": candidate.verification_source_id,
                        }
                    )
                if updates:
                    self._upsert_game(connection, existing.model_copy(update=updates))

            for raw_verification in payload.get("verification_history", []):
                verification = VerificationRecord.model_validate(raw_verification)
                source_id = source_id_map.get(verification.source_id, verification.source_id)
                exists = connection.execute(
                    """
                    SELECT 1 FROM verification_history
                    WHERE appid = ? AND verified_at = ? AND claim_status = ?
                      AND method = ? AND source_id = ?
                    """,
                    (
                        verification.appid,
                        verification.verified_at.isoformat(),
                        verification.claim_status.value,
                        verification.method,
                        source_id,
                    ),
                ).fetchone()
                if exists is None:
                    connection.execute(
                        """
                        INSERT INTO verification_history(
                            appid, verified_at, claim_status, method, source_id, notes
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            verification.appid,
                            verification.verified_at.isoformat(),
                            verification.claim_status.value,
                            verification.method,
                            source_id,
                            verification.notes,
                        ),
                    )

            for raw_event in payload.get("events", []):
                event = Event.model_validate(raw_event)
                exists = connection.execute(
                    "SELECT 1 FROM events WHERE appid = ? AND event_type = ? AND timestamp = ?",
                    (event.appid, event.event_type.value, event.timestamp.isoformat()),
                ).fetchone()
                if exists is None:
                    self._insert_event(connection, event)

    @staticmethod
    def _upsert_source(connection: sqlite3.Connection, source: Source) -> int:
        connection.execute(
            """
            INSERT INTO sources(name, url, kind, retrieved_at, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                name=excluded.name,
                kind=excluded.kind,
                retrieved_at=excluded.retrieved_at,
                metadata_json=excluded.metadata_json
            """,
            (
                source.name,
                source.url,
                source.kind,
                source.retrieved_at.isoformat(),
                json.dumps(source.metadata, ensure_ascii=False, sort_keys=True),
            ),
        )
        row = connection.execute("SELECT id FROM sources WHERE url = ?", (source.url,)).fetchone()
        return int(row[0])

    def upsert_source(self, source: Source) -> int:
        with self.connection() as connection, connection:
            return self._upsert_source(connection, source)

    def get_source(self, source_id: int | None) -> Source | None:
        if source_id is None:
            return None
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            return None
        return Source(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            kind=row["kind"],
            retrieved_at=_datetime(row["retrieved_at"]) or datetime.now(UTC),
            metadata=json.loads(row["metadata_json"]),
        )

    def all_sources(self) -> list[Source]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM sources ORDER BY id").fetchall()
        return [
            Source(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                kind=row["kind"],
                retrieved_at=_datetime(row["retrieved_at"]) or datetime.now(UTC),
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]

    def all_verifications(self) -> list[VerificationRecord]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM verification_history ORDER BY verified_at, id"
            ).fetchall()
        return [
            VerificationRecord(
                id=row["id"],
                appid=row["appid"],
                verified_at=_datetime(row["verified_at"]) or datetime.now(UTC),
                claim_status=row["claim_status"],
                method=row["method"],
                source_id=row["source_id"],
                notes=row["notes"],
            )
            for row in rows
        ]

    @staticmethod
    def _game_values(game: Game) -> tuple[object, ...]:
        return (
            game.appid,
            game.name,
            json.dumps(game.aliases, ensure_ascii=False),
            game.type,
            game.delisting_status.value,
            game.claim_status.value,
            game.activation_method.value,
            game.activation_id,
            game.first_seen.isoformat(),
            game.last_seen.isoformat(),
            game.delisted_at.isoformat() if game.delisted_at else None,
            game.relisted_at.isoformat() if game.relisted_at else None,
            game.last_verified.isoformat() if game.last_verified else None,
            game.verification_source_id,
            game.popularity_score,
            game.historical_peak_players,
            game.review_count,
            game.review_score,
            json.dumps(game.metadata, ensure_ascii=False, sort_keys=True),
            game.consecutive_missing_scans,
        )

    @classmethod
    def _upsert_game(cls, connection: sqlite3.Connection, game: Game) -> None:
        connection.execute(
            """
            INSERT INTO games(
                appid, name, aliases, type, delisting_status, claim_status,
                activation_method, activation_id, first_seen, last_seen,
                delisted_at, relisted_at, last_verified, verification_source_id,
                popularity_score, historical_peak_players, review_count,
                review_score, metadata_json, consecutive_missing_scans
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(appid) DO UPDATE SET
                name=excluded.name,
                aliases=excluded.aliases,
                type=excluded.type,
                delisting_status=excluded.delisting_status,
                claim_status=excluded.claim_status,
                activation_method=excluded.activation_method,
                activation_id=excluded.activation_id,
                first_seen=excluded.first_seen,
                last_seen=excluded.last_seen,
                delisted_at=excluded.delisted_at,
                relisted_at=excluded.relisted_at,
                last_verified=excluded.last_verified,
                verification_source_id=excluded.verification_source_id,
                popularity_score=excluded.popularity_score,
                historical_peak_players=excluded.historical_peak_players,
                review_count=excluded.review_count,
                review_score=excluded.review_score,
                metadata_json=excluded.metadata_json,
                consecutive_missing_scans=excluded.consecutive_missing_scans
            """,
            cls._game_values(game),
        )

    def upsert_game(self, game: Game) -> None:
        with self.connection() as connection, connection:
            self._upsert_game(connection, game)

    def record_verification(
        self,
        game: Game,
        source: Source,
        record: VerificationRecord,
        *,
        event_type: EventType | None,
    ) -> Game:
        with self.connection() as connection, connection:
            source_id = self._upsert_source(connection, source)
            if record.source_id != source_id:
                record = record.model_copy(update={"source_id": source_id})
            self._upsert_game(connection, game)
            connection.execute(
                """
                INSERT INTO verification_history(
                    appid, verified_at, claim_status, method, source_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.appid,
                    record.verified_at.isoformat(),
                    record.claim_status.value,
                    record.method,
                    source_id,
                    record.notes,
                ),
            )
            if event_type is not None:
                self._insert_event(
                    connection,
                    Event(
                        appid=game.appid,
                        event_type=event_type,
                        timestamp=record.verified_at,
                        metadata={"source_id": source_id, "method": record.method},
                    ),
                )
        return game

    @staticmethod
    def _insert_event(connection: sqlite3.Connection, event: Event) -> None:
        connection.execute(
            "INSERT INTO events(appid, event_type, timestamp, metadata_json) VALUES (?, ?, ?, ?)",
            (
                event.appid,
                event.event_type.value,
                event.timestamp.isoformat(),
                json.dumps(event.metadata, ensure_ascii=False, sort_keys=True),
            ),
        )

    @staticmethod
    def _row_to_game(row: sqlite3.Row) -> Game:
        return Game(
            appid=row["appid"],
            name=row["name"],
            aliases=json.loads(row["aliases"]),
            type=row["type"],
            delisting_status=row["delisting_status"],
            claim_status=row["claim_status"],
            activation_method=row["activation_method"],
            activation_id=row["activation_id"],
            first_seen=_datetime(row["first_seen"]),
            last_seen=_datetime(row["last_seen"]),
            delisted_at=_datetime(row["delisted_at"]),
            relisted_at=_datetime(row["relisted_at"]),
            last_verified=_datetime(row["last_verified"]),
            verification_source_id=row["verification_source_id"],
            popularity_score=row["popularity_score"],
            historical_peak_players=row["historical_peak_players"],
            review_count=row["review_count"],
            review_score=row["review_score"],
            metadata=json.loads(row["metadata_json"]),
            consecutive_missing_scans=row["consecutive_missing_scans"],
        )

    def get_game(self, appid: int) -> Game | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM games WHERE appid = ?", (appid,)).fetchone()
        return None if row is None else self._row_to_game(row)

    def list_games(
        self,
        *,
        limit: int = 200,
        offset: int = 0,
        claim_status: str | None = None,
        delisting_status: str | None = None,
        content_type: str | None = None,
    ) -> list[Game]:
        clauses: list[str] = []
        values: list[object] = []
        if claim_status:
            clauses.append("claim_status = ?")
            values.append(claim_status)
        if delisting_status:
            clauses.append("delisting_status = ?")
            values.append(delisting_status)
        if content_type:
            clauses.append("type = ?")
            values.append(content_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.extend((limit, offset))
        with self.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM games {where}
                ORDER BY popularity_score IS NULL, popularity_score DESC, name COLLATE NOCASE, appid
                LIMIT ? OFFSET ?
                """,
                values,
            ).fetchall()
        return [self._row_to_game(row) for row in rows]

    def all_games(self) -> list[Game]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM games ORDER BY appid").fetchall()
        return [self._row_to_game(row) for row in rows]

    def stats(self) -> DatasetStats:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS game_count,
                       SUM(CASE WHEN claim_status = 'CLAIMABLE' THEN 1 ELSE 0 END) AS claimable,
                       SUM(CASE WHEN type = 'dlc' THEN 1 ELSE 0 END) AS dlc,
                       SUM(CASE WHEN type = 'demo' THEN 1 ELSE 0 END) AS demo,
                       SUM(CASE WHEN delisting_status = 'DELISTED' THEN 1 ELSE 0 END) AS delisted,
                       MAX(last_seen) AS last_update
                FROM games
                """
            ).fetchone()
        return DatasetStats(
            game_count=int(row["game_count"]),
            claimable_count=int(row["claimable"] or 0),
            dlc_count=int(row["dlc"] or 0),
            demo_count=int(row["demo"] or 0),
            delisted_count=int(row["delisted"] or 0),
            last_update=_datetime(row["last_update"]),
        )

    def search_corpus(self) -> list[SearchRecord]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT appid, name, aliases FROM games ORDER BY appid"
            ).fetchall()
        return [
            SearchRecord(row["appid"], row["name"], tuple(json.loads(row["aliases"])))
            for row in rows
        ]

    def search_fts_appids(self, query: str, *, limit: int = 500) -> list[int]:
        tokens = re.findall(r"\w+", query, flags=re.UNICODE)
        if not tokens:
            return []
        expression = " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT rowid FROM games_fts WHERE games_fts MATCH ? ORDER BY rank LIMIT ?",
                (expression, limit),
            ).fetchall()
        return [int(row[0]) for row in rows]

    def get_games_by_appids(self, appids: Sequence[int]) -> list[Game]:
        if not appids:
            return []
        placeholders = ",".join("?" for _ in appids)
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM games WHERE appid IN ({placeholders})",
                tuple(appids),
            ).fetchall()
        games = {game.appid: game for game in map(self._row_to_game, rows)}
        return [games[appid] for appid in appids if appid in games]

    def latest_events(self, *, limit: int = 20) -> list[EventRow]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT e.id, e.appid, g.name AS game_name, e.event_type,
                       e.timestamp, e.metadata_json
                FROM events AS e
                JOIN games AS g ON g.appid = e.appid
                ORDER BY e.timestamp DESC, e.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            EventRow(
                id=row["id"],
                appid=row["appid"],
                game_name=row["game_name"],
                event_type=EventType(row["event_type"]),
                timestamp=_datetime(row["timestamp"]) or datetime.now(UTC),
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]

    def last_successful_scan_count(self) -> int | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT app_count FROM scan_runs
                WHERE status = 'SUCCESS'
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
        return None if row is None else int(row[0])

    def begin_scan(self, started_at: datetime) -> int:
        with self.connection() as connection, connection:
            cursor = connection.execute(
                "INSERT INTO scan_runs(started_at, status) VALUES (?, 'RUNNING')",
                (started_at.isoformat(),),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("SQLite did not return an ID for the catalog scan.")
            return cursor.lastrowid

    def fail_scan(self, scan_id: int, *, finished_at: datetime, error: str) -> None:
        with self.connection() as connection, connection:
            connection.execute(
                """
                UPDATE scan_runs SET status='FAILED', finished_at=?, error=? WHERE id=?
                """,
                (finished_at.isoformat(), error[:2000], scan_id),
            )

    def apply_scan(
        self,
        scan_id: int,
        diff: DiffSummary,
        *,
        finished_at: datetime,
        app_count: int,
        snapshot_path: Path,
        snapshot_sha256: str,
    ) -> None:
        with self.connection() as connection, connection:
            for transition in diff.transitions:
                self._upsert_game(connection, transition.game)
                for event_type in transition.event_types:
                    self._insert_event(
                        connection,
                        Event(
                            appid=transition.game.appid,
                            event_type=event_type,
                            timestamp=finished_at,
                        ),
                    )
            connection.execute(
                """
                UPDATE scan_runs
                SET status='SUCCESS', finished_at=?, app_count=?, snapshot_path=?,
                    snapshot_sha256=?, error=NULL
                WHERE id=?
                """,
                (
                    finished_at.isoformat(),
                    app_count,
                    str(snapshot_path),
                    snapshot_sha256,
                    scan_id,
                ),
            )
