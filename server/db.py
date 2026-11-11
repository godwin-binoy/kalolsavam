"""SQLite (WAL) data layer — per-thread connections + explicit transactions."""
from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self._local = threading.local()
        conn = self._new_conn()
        try:
            self._migrate(conn)
        finally:
            conn.close()

    def _new_conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
        return c

    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = self._new_conn()
            self._local.conn = c
        return c

    def _migrate(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)"
        )
        row = conn.execute("SELECT v FROM _meta WHERE k='schema_version'").fetchone()
        current = int(row["v"]) if row else 0
        mig_dir = Path(__file__).resolve().parent / "migrations"
        for mig in sorted(mig_dir.glob("*.sql")):
            ver = int(mig.stem.split("_")[0])
            if ver <= current:
                continue
            conn.executescript(mig.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO _meta(k,v) VALUES('schema_version',?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (str(ver),),
            )
            current = ver

    def q(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn().execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._conn().execute(sql, params).fetchone()

    def ex(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn().execute(sql, params)

    @contextmanager
    def transaction(self):
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
