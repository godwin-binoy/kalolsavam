"""Admin API: master data, users, sessions, audit, health, backup, flags."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time as _t
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import check_step_up, get_cfg, get_db, require_admin
from ..models import CategoryIn, EventIn, FlagIn, UserIn, VenueIn
from ..security import hash_password

router = APIRouter()

RESULTS_DOMAINS = ("kalolsavam.kerala.gov.in", "kerala.gov.in")


def _valid_results_url(value: str) -> bool:
    from urllib.parse import urlparse
    try:
        u = urlparse(value)
    except ValueError:
        return False
    return (u.scheme == "https" and u.hostname is not None
            and any(u.hostname == d or u.hostname.endswith("." + d)
                    for d in RESULTS_DOMAINS))


@router.get("/venues")
async def list_venues(request: Request, user: dict = Depends(require_admin)):
    db = get_db(request)
    return {"venues": [dict(r) for r in db.q("SELECT * FROM venues ORDER BY id")]}


@router.post("/venues")
async def create_venue(body: VenueIn, request: Request,
                       user: dict = Depends(require_admin)):
    db = get_db(request)
    cur = db.ex("INSERT INTO venues(name, kind, active) VALUES (?,?,?)",
                (body.name, body.kind, int(body.active)))
    return dict(db.one("SELECT * FROM venues WHERE id = ?", (cur.lastrowid,)))


@router.patch("/venues/{vid}")
async def update_venue(vid: int, body: VenueIn, request: Request,
                       user: dict = Depends(require_admin)):
    db = get_db(request)
    if not db.one("SELECT id FROM venues WHERE id = ?", (vid,)):
        raise HTTPException(404, "not_found")
    db.ex("UPDATE venues SET name = ?, kind = ?, active = ? WHERE id = ?",
          (body.name, body.kind, int(body.active), vid))
    return dict(db.one("SELECT * FROM venues WHERE id = ?", (vid,)))


@router.get("/categories")
async def list_categories(request: Request, user: dict = Depends(require_admin)):
    db = get_db(request)
    return {"categories": [dict(r) for r in db.q("SELECT * FROM categories ORDER BY name")]}


@router.post("/categories")
async def create_category(body: CategoryIn, request: Request,
                          user: dict = Depends(require_admin)):
    db = get_db(request)
    cur = db.ex("INSERT INTO categories(name, grp) VALUES (?,?)",
                (body.name, body.group))
    return {"id": cur.lastrowid}


@router.get("/events")
async def list_events(request: Request, venue_id: int | None = None,
                      user: dict = Depends(require_admin)):
    db = get_db(request)
    q = "SELECT * FROM events"
    params: tuple = ()
    if venue_id is not None:
        q += " WHERE venue_id = ?"
        params = (venue_id,)
    return {"events": [dict(r) for r in db.q(q + " ORDER BY id LIMIT 5000", params)]}


@router.post("/events")
async def create_event(body: EventIn, request: Request,
                       user: dict = Depends(require_admin)):
    db = get_db(request)
    try:
        cur = db.ex(
            "INSERT INTO events(code, title, category_id, venue_id, day, scheduled_time) "
            "VALUES (?,?,?,?,?,?)",
            (body.code, body.title, body.category_id, body.venue_id,
             body.day, body.scheduled_time),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "duplicate_or_fk")
    return {"id": cur.lastrowid}


@router.get("/users")
async def list_users(request: Request, user: dict = Depends(require_admin)):
    db = get_db(request)
    rows = db.q(
        "SELECT id, username, role, stages, totp_required, disabled, "
        " failed_count, locked_until, created_at FROM users ORDER BY id")
    return {"users": [dict(r) for r in rows]}


@router.post("/users")
async def create_user(body: UserIn, request: Request,
                      user: dict = Depends(require_admin)):
    db = get_db(request)
    salt, phash = hash_password(body.password)
    try:
        cur = db.ex(
            "INSERT INTO users(username, role, pwd_salt, pwd_hash, stages, "
            " totp_required, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (body.username, body.role, salt, phash, json.dumps(body.stages),
             1 if body.role == "admin" else 0, db.now(), db.now()),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "username_taken")
    return {"id": cur.lastrowid, "username": body.username, "role": body.role}


@router.post("/users/{uid}/disable")
async def disable_user(uid: int, request: Request,
                       user: dict = Depends(require_admin)):
    check_step_up(request, user)
    db = get_db(request)
    if not db.one("SELECT id FROM users WHERE id = ?", (uid,)):
        raise HTTPException(404, "not_found")
    db.ex("UPDATE sessions SET revoked = 1 WHERE user_id = ?", (uid,))
    db.ex("UPDATE users SET disabled = 1, updated_at = ? WHERE id = ?",
          (db.now(), uid))
    return {"ok": True}


@router.get("/sessions")
async def list_sessions(request: Request, user: dict = Depends(require_admin)):
    db = get_db(request)
    rows = db.q(
        "SELECT s.sid, s.user_id, u.username, u.role, s.created_at, "
        " s.last_seen, s.revoked FROM sessions s JOIN users u ON u.id = s.user_id "
        "ORDER BY s.last_seen DESC LIMIT 200")
    return {"sessions": [dict(r) for r in rows]}


@router.post("/sessions/revoke-all")
async def revoke_all(request: Request, user_id: int | None = None,
                     user: dict = Depends(require_admin)):
    check_step_up(request, user)
    db = get_db(request)
    if user_id:
        db.ex("UPDATE sessions SET revoked = 1 WHERE user_id = ?", (user_id,))
    else:
        db.ex("UPDATE sessions SET revoked = 1")
    return {"ok": True}


@router.get("/audit/auth")
async def audit_auth(request: Request, limit: int = 200,
                     user: dict = Depends(require_admin)):
    db = get_db(request)
    rows = db.q("SELECT * FROM auth_audit ORDER BY id DESC LIMIT ?",
                (min(max(limit, 1), 1000),))
    return {"events": [dict(r) for r in rows]}


@router.get("/health")
async def health(request: Request, user: dict = Depends(require_admin)):
    db, cfg = get_db(request), get_cfg(request)
    stat = os.stat(cfg.db_path)
    try:
        disk_free = shutil.disk_usage(cfg.db_path).free
    except OSError:
        disk_free = 0
    try:
        load = list(os.getloadavg())
    except (AttributeError, OSError):
        load = [0.0, 0.0, 0.0]
    fails = db.one(
        "SELECT COUNT(*) c FROM auth_audit WHERE event = 'login_fail' AND ts > ?",
        (db.now() - 3600,))["c"]
    return {
        "time": db.now(),
        "db_bytes": stat.st_size,
        "active_sessions": db.one(
            "SELECT COUNT(*) c FROM sessions WHERE revoked = 0")["c"],
        "sse_connections": len(request.app.state.subscribers),
        "disk_free_bytes": disk_free,
        "load_avg": load,
        "recent_auth_failures": fails,
    }


@router.post("/backup")
async def backup(request: Request, user: dict = Depends(require_admin)):
    check_step_up(request, user)
    cfg = get_cfg(request)
    src = Path(cfg.db_path)
    dst_dir = src.parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    stamp = _t.strftime("%Y%m%d-%H%M%S")
    dst = dst_dir / f"kalolsavam-{stamp}.db"
    src_con = sqlite3.connect(str(src))
    dst_con = sqlite3.connect(str(dst))
    src_con.backup(dst_con)
    dst_con.close()
    src_con.close()
    backups = sorted(dst_dir.glob("kalolsavam-*.db"))
    for old in backups[:-24]:
        old.unlink()
    return {"ok": True, "path": str(dst)}


@router.get("/flags")
async def get_flags(request: Request, user: dict = Depends(require_admin)):
    db, cfg = get_db(request), get_cfg(request)
    rows = db.q("SELECT k, v FROM settings")
    flags = {r["k"]: r["v"] for r in rows}
    return {"flags": flags, "results_url": flags.get("results_url", cfg.results_url)}


@router.post("/flags")
async def set_flag(body: FlagIn, request: Request,
                   user: dict = Depends(require_admin)):
    check_step_up(request, user)
    if body.key == "results_url" and not _valid_results_url(body.value):
        raise HTTPException(400, "results_url_must_be_https_gov_in")
    db = get_db(request)
    db.ex(
        "INSERT INTO settings(k, v, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(k) DO UPDATE SET v = excluded.v, updated_at = excluded.updated_at",
        (body.key, body.value, db.now()),
    )
    return {"ok": True}
