CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('stagemaster','admin')),
  pwd_salt TEXT NOT NULL,
  pwd_hash TEXT NOT NULL,
  totp_secret BLOB,
  pending_totp_secret BLOB,
  totp_required INTEGER NOT NULL DEFAULT 0,
  stages TEXT NOT NULL DEFAULT '[]',
  disabled INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  locked_until REAL NOT NULL DEFAULT 0,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE sessions (
  sid TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ip_hash TEXT,
  created_at REAL NOT NULL,
  last_seen REAL NOT NULL,
  expires_at REAL NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_sessions_user ON sessions(user_id);

CREATE TABLE auth_audit (
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  username TEXT,
  user_id INTEGER,
  ip_hash TEXT,
  event TEXT NOT NULL,
  detail TEXT
);
CREATE INDEX idx_audit_ts ON auth_audit(ts);

CREATE TABLE venues (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT DEFAULT 'stage',
  active INTEGER DEFAULT 1
);

CREATE TABLE categories (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  grp TEXT DEFAULT 'HSS GENERAL'
);

CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category_id INTEGER REFERENCES categories(id),
  venue_id INTEGER REFERENCES venues(id),
  day TEXT,
  scheduled_time TEXT
);
CREATE INDEX idx_events_venue ON events(venue_id);

CREATE TABLE participants (
  id INTEGER PRIMARY KEY,
  event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
  school TEXT NOT NULL,
  student_name TEXT,
  roll TEXT,
  order_no INTEGER DEFAULT 0
);

CREATE TABLE queue_items (
  id INTEGER PRIMARY KEY,
  venue_id INTEGER NOT NULL REFERENCES venues(id),
  event_id INTEGER NOT NULL REFERENCES events(id),
  participant_id INTEGER REFERENCES participants(id),
  status TEXT NOT NULL DEFAULT 'WAITING'
    CHECK(status IN ('WAITING','ON-STAGE','PAUSED','COMPLETE','SKIPPED')),
  position INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1,
  started_at REAL,
  completed_at REAL,
  updated_at REAL NOT NULL
);
CREATE INDEX idx_queue_board ON queue_items(venue_id, status, position);

CREATE TABLE scores (
  id INTEGER PRIMARY KEY,
  queue_item_id INTEGER REFERENCES queue_items(id) ON DELETE CASCADE,
  judge_no INTEGER NOT NULL,
  value REAL NOT NULL,
  entered_by INTEGER REFERENCES users(id),
  entered_at REAL NOT NULL,
  UNIQUE(queue_item_id, judge_no)
);

CREATE TABLE live_state (
  venue_id INTEGER PRIMARY KEY REFERENCES venues(id),
  state TEXT NOT NULL DEFAULT 'IDLE',
  announcement TEXT DEFAULT '',
  updated_at REAL NOT NULL
);

CREATE TABLE settings (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE idempotency (
  key TEXT PRIMARY KEY,
  response TEXT,
  created_at REAL NOT NULL
);
