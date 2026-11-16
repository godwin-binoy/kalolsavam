"""Single SQLite (WAL) data layer and idempotent schema bootstrap."""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    stages TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    token_version INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens(user_id);

CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'stage',
    slug TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_venues_slug ON venues(slug) WHERE slug IS NOT NULL;

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT,
    venue_id INTEGER REFERENCES venues(id) ON DELETE SET NULL,
    day TEXT,
    scheduled_time TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_id);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    register_no TEXT NOT NULL,
    name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    school_code TEXT NOT NULL,
    student_class INTEGER NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    deleted_at REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_participants_register_no
    ON participants(register_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_participants_school_code ON participants(school_code);

CREATE TABLE IF NOT EXISTS participant_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    item_code TEXT NOT NULL,
    venue_id INTEGER NOT NULL,
    venue_name TEXT NOT NULL,
    perf_date TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    deleted_at REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_participant_entries_item
    ON participant_entries(participant_id, item_code) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_entries_item ON participant_entries(item_code);

CREATE TABLE IF NOT EXISTS live_state (
    venue_id INTEGER PRIMARY KEY REFERENCES venues(id) ON DELETE CASCADE,
    state TEXT NOT NULL DEFAULT 'IDLE',
    current_item TEXT,
    current_chest TEXT,
    upcoming_chests TEXT,
    announcement TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS photo_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER NOT NULL,
    workflow TEXT NOT NULL,
    perf_date TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS photo_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES photo_batches(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    filename TEXT NOT NULL,
    uploaded_at REAL NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0,
    processed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_photo_assets_processed ON photo_assets(processed, kind);

CREATE TABLE IF NOT EXISTS photo_asset_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_asset_id INTEGER NOT NULL REFERENCES photo_assets(id) ON DELETE CASCADE,
    participant_entry_id INTEGER NOT NULL REFERENCES participant_entries(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    UNIQUE(photo_asset_id, participant_entry_id)
);

CREATE TABLE IF NOT EXISTS auth_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    username TEXT,
    ip_hash TEXT,
    event TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON auth_audit(ts);
"""

_EXTRA_COLS = (
    ("events", "category", "TEXT"),
    ("live_state", "current_item", "TEXT"),
    ("live_state", "current_chest", "TEXT"),
    ("live_state", "upcoming_chests", "TEXT"),
    ("photo_batches", "perf_date", "TEXT"),
    ("photo_assets", "processed", "INTEGER NOT NULL DEFAULT 0"),
    ("photo_assets", "processed_at", "REAL"),
)


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self._local = threading.local()
        self._conns_lock = threading.Lock()
        self._conns: set[sqlite3.Connection] = set()

    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA busy_timeout=5000")
            with self._conns_lock:
                self._conns.add(c)
            self._local.conn = c
        return c

    def init_schema(self) -> None:
        c = self._conn()
        c.executescript(_SCHEMA_SQL)
        for table, col, ddl in _EXTRA_COLS:
            cols = {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}  # noqa: S608
            if col not in cols:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")  # noqa: S608

    def close_all(self) -> None:
        with self._conns_lock:
            conns = list(self._conns)
            self._conns.clear()
        for c in conns:
            try:
                c.close()
            except Exception as exc:
                logging.getLogger("kalolsavam").debug("DB close failed: %s", exc)

    def q(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self._conn().execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return self._conn().execute(sql, params).fetchone()

    def ex(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        return self._conn().execute(sql, params)

    @contextmanager
    def transaction(self) -> Iterator[Database]:
        if getattr(self._local, "tx_depth", 0) > 0:
            raise RuntimeError("nested db.transaction() is not supported")
        c = self._conn()
        c.execute("BEGIN IMMEDIATE")
        self._local.tx_depth = 1
        try:
            yield self
        except BaseException:
            c.execute("ROLLBACK")
            raise
        else:
            c.execute("COMMIT")
        finally:
            self._local.tx_depth = 0

    def now(self) -> float:
        return time.time()
