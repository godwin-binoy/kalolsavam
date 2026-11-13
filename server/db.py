"""SQLite (WAL) data layer — per-thread connections + explicit transactions."""
from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self._local = threading.local()
        self._conns_lock = threading.Lock()
        self._conns: set[sqlite3.Connection] = set()
        conn = self._new_conn(track=False)
        try:
            self._migrate(conn)
        finally:
            conn.close()

    def _new_conn(self, track: bool = True) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
        if track:
            with self._conns_lock:
                self._conns.add(c)
        return c

    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = self._new_conn()
            self._local.conn = c
        return c

    def close_all(self) -> None:
        with self._conns_lock:
            conns = list(self._conns)
            self._conns.clear()
        for c in conns:
            try:
                c.close()
            except Exception:
                pass

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
            try:
                conn.executescript(mig.read_text(encoding="utf-8"))
            except sqlite3.Error as e:
                raise RuntimeError(f"Migration {mig.name} failed: {e}") from e
            conn.execute(
                "INSERT INTO _meta(k,v) VALUES('schema_version',?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (str(ver),),
            )
            current = ver

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
