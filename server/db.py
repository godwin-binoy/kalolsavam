"""SQLite (WAL) data layer — schema, migrations, helpers.

Reliability notes:
 - WAL mode + busy_timeout: readers never block the single writer; safe for
   one server process on one laptop.
 - Foreign keys ON: bad references are rejected by the database itself.
 - Every helper takes (sql, params) and uses bound '?' placeholders ONLY —
   no string interpolation anywhere → SQL injection is structurally impossible.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('stagemaster','admin')),
  pwd_salt_hex TEXT,                  -- per-user random salt
  pwd_hash_hex TEXT,                  -- PBKDF2-HMAC-SHA256(salt, password)
  totp_secret BLOB,                   -- TOTP shared secret, stored PLAINTEXT
                                      -- (no-DB-encryption policy; NULL until enrolled)
  totp_required INTEGER NOT NULL DEFAULT 0,
  stages TEXT NOT NULL DEFAULT '[]',  -- JSON list of stage ids (stagemaster scope)
  disabled INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  locked_until REAL NOT NULL DEFAULT 0,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  jti TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  family TEXT NOT NULL,
  parent_jti TEXT,
  expires_at REAL NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,
  revoked INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rt_family ON refresh_tokens(family);

CREATE TABLE IF NOT EXISTS sessions (
  sid TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  current_jti TEXT,
  created_at REAL NOT NULL,
  last_seen REAL NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS auth_audit (
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  username TEXT,
  user_id INTEGER,
  ip TEXT,
  event TEXT NOT NULL,           -- login_ok|login_fail|lockout|logout|refresh_reuse|totp_fail|...
  detail TEXT
);

CREATE TABLE IF NOT EXISTS audit_chain (
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  actor_id INTEGER,
  actor TEXT,
  action TEXT NOT NULL,
  target TEXT,
  before_hash TEXT,
  after_hash TEXT,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL             -- SHA-256 chain link
);

-- ===== domain data =====
CREATE TABLE IF NOT EXISTS venues (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT DEFAULT 'stage', active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, grp TEXT DEFAULT 'HSS GENERAL'
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, code TEXT UNIQUE, title TEXT NOT NULL,
  category_id INTEGER REFERENCES categories(id), venue_id INTEGER REFERENCES venues(id),
  day TEXT, scheduled_time TEXT
);
CREATE TABLE IF NOT EXISTS participants (
  id INTEGER PRIMARY KEY, event_id INTEGER REFERENCES events(id),
  school TEXT NOT NULL, student_name TEXT, roll TEXT, order_no INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS queue_items (
  id INTEGER PRIMARY KEY, venue_id INTEGER REFERENCES venues(id),
  event_id INTEGER REFERENCES events(id), participant_id INTEGER REFERENCES participants(id),
  status TEXT NOT NULL DEFAULT 'WAITING'
    CHECK(status IN ('WAITING','ON-STAGE','PAUSED','COMPLETE','SKIPPED')),
  position INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1,       -- optimistic concurrency
  started_at REAL, completed_at REAL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS scores (
  id INTEGER PRIMARY KEY, queue_item_id INTEGER REFERENCES queue_items(id),
  judge_no INTEGER NOT NULL, value REAL NOT NULL,
  entered_by INTEGER REFERENCES users(id), entered_at REAL NOT NULL,
  UNIQUE(queue_item_id, judge_no)
);
CREATE TABLE IF NOT EXISTS live_state (
  venue_id INTEGER PRIMARY KEY REFERENCES venues(id),
  state TEXT NOT NULL DEFAULT 'IDLE',       -- IDLE|RUNNING|PAUSED|BREAK|FINISHED
  announcement TEXT DEFAULT '', updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS feature_flags (
  key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS changelog (
  id INTEGER PRIMARY KEY, ts REAL NOT NULL, entity TEXT NOT NULL, entity_id INTEGER,
  change TEXT NOT NULL                       -- JSON diff for SSE/public snapshot rebuild
);
"""


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        # create tables FIRST — reading meta before the schema exists fails on a
        # brand-new database file.
        self.conn.executescript(SCHEMA)
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(users)")}
        if "totp_secret" not in cols:      # pre-no-encryption-policy database
            self.conn.execute("ALTER TABLE users ADD COLUMN totp_secret BLOB")
        cur_ver = int(self.scalar("SELECT v FROM meta WHERE k='schema_version'") or 0)
        if cur_ver < SCHEMA_VERSION:
            self.conn.execute(
                "INSERT INTO meta(k,v) VALUES('schema_version',?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (str(SCHEMA_VERSION),),
            )
        self.conn.commit()

    # ---- helpers ----
    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def scalar(self, sql: str, params: tuple = ()) -> Any:
        row = self.one(sql, params)
        return row[0] if row else None

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def now(self) -> float:
        return time.time()

    # ---- audit chain (append-only, hash-linked) ----
    def log_auth(self, *, username: str | None, user_id: int | None, ip: str,
                 event: str, detail: str = "") -> None:
        self.execute(
            "INSERT INTO auth_audit(ts,username,user_id,ip,event,detail) "
            "VALUES(?,?,?,?,?,?)",
            (self.now(), username, user_id, ip, event, detail),
        )

    def log_admin(self, actor_id: int | None, actor: str, action: str,
                  target: str, before: Any = None, after: Any = None) -> str:
        import hashlib

        prev = self.scalar("SELECT hash FROM audit_chain ORDER BY id DESC LIMIT 1") \
            or "GENESIS"
        bh = hashlib.sha256(json.dumps(before, sort_keys=True, default=str).encode()).hexdigest() \
            if before is not None else ""
        ah = hashlib.sha256(json.dumps(after, sort_keys=True, default=str).encode()).hexdigest() \
            if after is not None else ""
        ts = self.now()
        payload = f"{prev}|{ts}|{actor_id}|{action}|{target}|{bh}|{ah}"
        h = hashlib.sha256(payload.encode()).hexdigest()
        self.execute(
            "INSERT INTO audit_chain(ts,actor_id,actor,action,target,before_hash,"
            "after_hash,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?,?)",
            (ts, actor_id, actor, action, target, bh, ah, prev, h),
        )
        return h

    def verify_chain(self) -> tuple[bool, int]:
        import hashlib

        prev = "GENESIS"
        rows = self.query("SELECT * FROM audit_chain ORDER BY id")
        for r in rows:
            payload = f"{prev}|{r['ts']}|{r['actor_id']}|{r['action']}|{r['target']}|" \
                      f"{r['before_hash']}|{r['after_hash']}"
            if hashlib.sha256(payload.encode()).hexdigest() != r["hash"] or r["prev_hash"] != prev:
                return False, r["id"]
            prev = r["hash"]
        return True, len(rows)

    # ---- changelog / SSE bus ----
    def emit_change(self, entity: str, entity_id: int | None, change: dict) -> None:
        self.execute(
            "INSERT INTO changelog(ts,entity,entity_id,change) VALUES(?,?,?,?)",
            (self.now(), entity, entity_id, json.dumps(change, default=str)),
        )
        from .events import BUS  # notify after commit

        BUS.publish(entity, change)

    def recent_changes(self, since_id: int = 0, limit: int = 200) -> list[sqlite3.Row]:
        return self.query(
            "SELECT * FROM changelog WHERE id>? ORDER BY id LIMIT ?", (since_id, limit)
        )
