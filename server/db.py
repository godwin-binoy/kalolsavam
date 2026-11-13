"""SQLite (WAL) data layer — per-thread connections + explicit transactions.

Schema is owned exclusively by Alembic (see server/schema.py). This class never
creates, alters, or migrates tables.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self._local = threading.local()
        self._conns_lock = threading.Lock()
        self._conns: set[sqlite3.Connection] = set()

    def _new_conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
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
            except Exception as exc:
                logging.getLogger("kalolsavam").debug("DB connection close failed: %s", exc)

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
