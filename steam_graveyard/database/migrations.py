"""Small, explicit SQLite migration runner."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable


def _migration_1(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE games (
            appid INTEGER PRIMARY KEY CHECK (appid BETWEEN 1 AND 4294967295),
            name TEXT NOT NULL,
            aliases TEXT NOT NULL DEFAULT '[]',
            type TEXT NOT NULL DEFAULT 'game',
            delisting_status TEXT NOT NULL DEFAULT 'UNKNOWN',
            claim_status TEXT NOT NULL DEFAULT 'UNKNOWN',
            activation_method TEXT NOT NULL DEFAULT 'none',
            activation_id TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            delisted_at TEXT,
            relisted_at TEXT,
            last_verified TEXT,
            verification_source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
            popularity_score REAL
                CHECK (popularity_score IS NULL OR popularity_score BETWEEN 0 AND 100),
            historical_peak_players INTEGER
                CHECK (historical_peak_players IS NULL OR historical_peak_players >= 0),
            review_count INTEGER CHECK (review_count IS NULL OR review_count >= 0),
            review_score REAL CHECK (review_score IS NULL OR review_score BETWEEN 0 AND 100),
            metadata_json TEXT NOT NULL DEFAULT '{}',
            consecutive_missing_scans INTEGER NOT NULL DEFAULT 0
                CHECK (consecutive_missing_scans >= 0)
        );

        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appid INTEGER NOT NULL REFERENCES games(appid) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE verification_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appid INTEGER NOT NULL REFERENCES games(appid) ON DELETE CASCADE,
            verified_at TEXT NOT NULL,
            claim_status TEXT NOT NULL,
            method TEXT NOT NULL,
            source_id INTEGER NOT NULL REFERENCES sources(id),
            notes TEXT
        );

        CREATE TABLE scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            app_count INTEGER,
            snapshot_path TEXT,
            snapshot_sha256 TEXT,
            error TEXT
        );

        CREATE INDEX idx_games_popularity ON games(popularity_score DESC, appid ASC);
        CREATE INDEX idx_games_claim_status ON games(claim_status, popularity_score DESC);
        CREATE INDEX idx_games_delisting_status ON games(delisting_status, popularity_score DESC);
        CREATE INDEX idx_games_last_verified ON games(last_verified DESC);
        CREATE INDEX idx_games_last_seen ON games(last_seen DESC);
        CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
        CREATE INDEX idx_verification_appid_time
            ON verification_history(appid, verified_at DESC);

        CREATE VIRTUAL TABLE games_fts USING fts5(
            name,
            aliases,
            content='games',
            content_rowid='appid',
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE TRIGGER games_after_insert AFTER INSERT ON games BEGIN
            INSERT INTO games_fts(rowid, name, aliases)
            VALUES (new.appid, new.name, new.aliases);
        END;
        CREATE TRIGGER games_after_delete AFTER DELETE ON games BEGIN
            INSERT INTO games_fts(games_fts, rowid, name, aliases)
            VALUES ('delete', old.appid, old.name, old.aliases);
        END;
        CREATE TRIGGER games_after_update AFTER UPDATE ON games BEGIN
            INSERT INTO games_fts(games_fts, rowid, name, aliases)
            VALUES ('delete', old.appid, old.name, old.aliases);
            INSERT INTO games_fts(rowid, name, aliases)
            VALUES (new.appid, new.name, new.aliases);
        END;
        """
    )


MIGRATIONS: tuple[Callable[[sqlite3.Connection], None], ...] = (_migration_1,)


def migrate(connection: sqlite3.Connection) -> None:
    current = int(connection.execute("PRAGMA user_version").fetchone()[0])
    for version, migration in enumerate(MIGRATIONS, start=1):
        if version <= current:
            continue
        with connection:
            migration(connection)
            connection.execute(f"PRAGMA user_version = {version}")
