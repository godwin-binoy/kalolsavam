#!/usr/bin/env python3
"""Seed demo/master data (venues, categories, events, participants, queues).

Idempotent-ish: refuses to run when venues already exist unless --force.
Usage:  python -m server.scripts.seed [--force]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.config import Config          # noqa: E402
from server.db import Database            # noqa: E402

VENUES = [
    ("Main Stage", "stage"),
    ("Audio Visual Room", "room"),
    ("Arabic Hall", "hall"),
]
CATEGORIES = [
    ("HS GENERAL", "HSS GENERAL"),
    ("HSS GENERAL", "HSS GENERAL"),
    ("HS ARABIC", "HSS ARABIC"),
    ("HS SANSKRIT", "HSS SANSKRIT"),
]
EVENTS = [
    ("M-01", "Solo Song — Boys", 0, 0, "Day 1", "09:00"),
    ("M-02", "Group Dance", 1, 0, "Day 1", "10:30"),
    ("A-01", "Arabic Recitation", 2, 2, "Day 1", "09:30"),
    ("S-01", "Sanskrit Shloka", 3, 1, "Day 2", "09:00"),
]
PARTICIPANTS = {
    "M-01": [("St. Antony's HSS Mala", "Arun S", "12"),
             ("GHS Karukutty", "Biju T", "7")],
    "M-02": [("HSS Vazhakkam", "Team Alpha", "-"),
             ("GHSS Malayil", "Team Beta", "-")],
    "A-01": [("Arabian College MHSS", "Nazeer P", "5")],
    "S-01": [("Vidyanikethan EMS HSS", "Lakshmi R", "9")],
}


def main() -> None:
    cfg = Config()
    cfg.ensure_dirs()
    db = Database(cfg.db_path)
    if db.scalar("SELECT COUNT(*) FROM venues") and "--force" not in sys.argv:
        raise SystemExit("venues already exist — nothing to do (use --force)")

    now = db.now()
    v_ids = []
    for name, kind in VENUES:
        cur = db.execute("INSERT OR IGNORE INTO venues(name,kind,active) VALUES(?,?,1)",
                         (name, kind))
        row = db.one("SELECT id FROM venues WHERE name=?", (name,))
        v_ids.append(row["id"])
    c_ids = []
    for name, grp in CATEGORIES:
        db.execute("INSERT OR IGNORE INTO categories(name,grp) VALUES(?,?)",
                   (name, grp))
        c_ids.append(db.scalar("SELECT id FROM categories WHERE name=?", (name,)))
    for code, title, ci, vi, day, t in EVENTS:
        exists = db.one("SELECT id FROM events WHERE code=?", (code,))
        if exists:
            eid = exists["id"]
        else:
            cur = db.execute(
                "INSERT INTO events(code,title,category_id,venue_id,day,scheduled_time)"
                " VALUES(?,?,?,?,?,?)",
                (code, title, c_ids[ci], v_ids[vi], day, t))
            eid = cur.lastrowid
        if db.scalar("SELECT COUNT(*) FROM queue_items WHERE event_id=?", (eid,)):
            continue
        for i, (school, student, roll) in enumerate(PARTICIPANTS.get(code, [])):
            pcur = db.execute(
                "INSERT INTO participants(event_id,school,student_name,roll,order_no)"
                " VALUES(?,?,?,?,?)", (eid, school, student, roll, i))
            db.execute(
                "INSERT INTO queue_items(venue_id,event_id,participant_id,position,updated_at)"
                " VALUES(?,?,?,?,?)", (v_ids[vi], eid, pcur.lastrowid, i, now))
    for key, val in (("results_publishing_open", "0"), ("site_live", "1")):
        db.execute("INSERT OR IGNORE INTO feature_flags(key,value,updated_at) VALUES(?,?,?)",
                   (key, val, now))
    print(f"seeded: {len(v_ids)} venues, {len(c_ids)} categories, {len(EVENTS)} events")


if __name__ == "__main__":
    main()
