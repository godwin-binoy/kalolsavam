"""SQLite (WAL) data layer with a simple versioned migration runner."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS _meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)"
        )
        row = self.conn.execute("SELECT v FROM _meta WHERE k='schema_version'").fetchone()
        current = int(row["v"]) if row else 0
        mig_dir = Path(__file__).resolve().parent / "migrations"
        for mig in sorted(mig_dir.glob("*.sql")):
            ver = int(mig.stem.split("_")[0])
            if ver <= current:
                continue
            self.conn.executescript(mig.read_text(encoding="utf-8"))
            self.conn.execute(
                "INSERT INTO _meta(k,v) VALUES('schema_version',?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (str(ver),),
            )
            self.conn.commit()
            current = ver

    def q(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def ex(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def now(self) -> float:
        return time.time()
