CREATE TABLE IF NOT EXISTS venues (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT DEFAULT 'stage',
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  grp TEXT DEFAULT 'HSS GENERAL'
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category_id INTEGER REFERENCES categories(id),
  venue_id INTEGER REFERENCES venues(id),
  day TEXT,
  scheduled_time TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_id);

CREATE TABLE IF NOT EXISTS participants (
  id INTEGER PRIMARY KEY,
  event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
  school TEXT NOT NULL,
  student_name TEXT,
  roll TEXT
);

CREATE TABLE IF NOT EXISTS queue_items (
  id INTEGER PRIMARY KEY,
  venue_id INTEGER NOT NULL REFERENCES venues(id),
  event_id INTEGER NOT NULL REFERENCES events(id),
  participant_id INTEGER REFERENCES participants(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'WAITING'
    CHECK(status IN ('WAITING','ON-STAGE','PAUSED','COMPLETE','SKIPPED')),
  position INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1,
  started_at REAL,
  completed_at REAL,
  updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_queue_board ON queue_items(venue_id, status, position);

CREATE TABLE IF NOT EXISTS scores (
  id INTEGER PRIMARY KEY,
  queue_item_id INTEGER REFERENCES queue_items(id) ON DELETE CASCADE,
  judge_no INTEGER NOT NULL,
  value REAL NOT NULL,
  entered_by TEXT NOT NULL,
  entered_at REAL NOT NULL,
  UNIQUE(queue_item_id, judge_no)
);

CREATE TABLE IF NOT EXISTS live_state (
  venue_id INTEGER PRIMARY KEY REFERENCES venues(id),
  state TEXT NOT NULL DEFAULT 'IDLE',
  announcement TEXT DEFAULT '',
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency (
  key TEXT PRIMARY KEY,
  response TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_audit (
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  username TEXT,
  ip_hash TEXT,
  event TEXT NOT NULL,
  detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON auth_audit(ts);
