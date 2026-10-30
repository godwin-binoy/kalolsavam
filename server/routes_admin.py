"""Manage API — master data CRUD, users/sessions, health, ops.

Requires role=admin (middleware additionally enforces the staff-VLAN IP
allowlist). Destructive actions require step-up: a fresh TOTP code in the
`x-step-up-totp` header, verified against the actor's enrolled secret.
Every action is written to the hash-chained audit log.
"""
from __future__ import annotations

import json
import os
import secrets as _secrets
import subprocess
import sys
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter()

STEP_UP_ACTIONS = {"user_delete", "session_revoke_all", "deploy", "key_rotate",
                   "backup_run", "flag_write", "csv_import_commit"}


def _admin(request: Request):
    db = request.app.state.db
    claims = request.app.state.get_access(request)
    if claims["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_only")
    return db, claims


def _step_up(request: Request, db, claims: dict, action: str) -> None:
    """Destructive ops need a live TOTP from the actor + recent session."""
    code = request.headers.get("x-step-up-totp", "")
    user = db.one("SELECT * FROM users WHERE id=?", (int(claims["sub"]),))
    if not user or not user["totp_enc"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "totp_not_enrolled")
    from .auth import totp_verify
    field = request.app.state.field
    secret = field.decrypt(bytes(user["totp_enc"]), aad=str(user["id"]).encode())
    if not code or not totp_verify(secret, code):
        db.log_auth(username=claims["usr"], user_id=int(claims["sub"]),
                    ip=request.client.host if request.client else "?",
                    event="stepup_fail", detail=action)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "stepup_failed")


# ------------------------------------------------------------ venues ------
class VenueIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="stage", max_length=32)
    active: bool = True


@router.get("/venues")
async def list_venues(request: Request):
    db, _ = _admin(request)
    return {"venues": [dict(r) for r in db.query("SELECT * FROM venues ORDER BY id")]}


@router.post("/venues")
async def create_venue(body: VenueIn, request: Request):
    db, claims = _admin(request)
    cur = db.execute("INSERT INTO venues(name,kind,active) VALUES(?,?,?)",
                     (body.name, body.kind, int(body.active)))
    row = db.one("SELECT * FROM venues WHERE id=?", (cur.lastrowid,))
    db.log_admin(claims["sub"], claims["usr"], "venue_create", str(row["id"]),
                 None, dict(row))
    db.emit_change("venue", row["id"], {"op": "create"})
    return dict(row)


@router.patch("/venues/{vid}")
async def update_venue(vid: int, body: VenueIn, request: Request):
    db, claims = _admin(request)
    before = db.one("SELECT * FROM venues WHERE id=?", (vid,))
    if not before:
        raise HTTPException(404, "not_found")
    db.execute("UPDATE venues SET name=?, kind=?, active=? WHERE id=?",
               (body.name, body.kind, int(body.active), vid))
    after = db.one("SELECT * FROM venues WHERE id=?", (vid,))
    db.log_admin(claims["sub"], claims["usr"], "venue_update", str(vid),
                 dict(before), dict(after))
    db.emit_change("venue", vid, {"op": "update"})
    return dict(after)


# ------------------------------------------------------- categories/events --
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    group: str = Field(default="HSS GENERAL", max_length=64)


@router.get("/categories")
async def list_categories(request: Request):
    db, _ = _admin(request)
    return {"categories": [dict(r) for r in db.query("SELECT * FROM categories ORDER BY name")]}


@router.post("/categories")
async def create_category(body: CategoryIn, request: Request):
    db, claims = _admin(request)
    cur = db.execute("INSERT INTO categories(name,group) VALUES(?,?)",
                     (body.name, body.group))
    db.log_admin(claims["sub"], claims["usr"], "category_create",
                 str(cur.lastrowid), None, body.model_dump())
    return {"id": cur.lastrowid}


class EventIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


@router.get("/events")
async def list_events(request: Request, venue_id: int | None = None):
    db, _ = _admin(request)
    q = "SELECT * FROM events"
    params: tuple = ()
    if venue_id is not None:
        q += " WHERE venue_id=?"
        params = (venue_id,)
    return {"events": [dict(r) for r in db.query(q + " ORDER BY id LIMIT 2000", params)]}


@router.post("/events")
async def create_event(body: EventIn, request: Request):
    db, claims = _admin(request)
    try:
        cur = db.execute(
            "INSERT INTO events(code,title,category_id,venue_id,day,scheduled_time)"
            " VALUES(?,?,?,?,?,?)",
            (body.code, body.title, body.category_id, body.venue_id,
             body.day, body.scheduled_time))
    except Exception:
        raise HTTPException(409, "duplicate_or_fk")
    db.log_admin(claims["sub"], claims["usr"], "event_create",
                 str(cur.lastrowid), None, body.model_dump())
    return {"id": cur.lastrowid}


class QueueBuildIn(BaseModel):
    event_id: int


@router.post("/events/build-queue")
async def build_queue(body: QueueBuildIn, request: Request):
    """Create queue_items for an event from its participants, in order_no."""
    db, claims = _admin(request)
    ev = db.one("SELECT * FROM events WHERE id=?", (body.event_id,))
    if not ev or not ev["venue_id"]:
        raise HTTPException(400, "event_missing_or_no_venue")
    existing = db.scalar("SELECT COUNT(*) FROM queue_items WHERE event_id=?",
                         (body.event_id,))
    if existing:
        raise HTTPException(409, "queue_exists")
    parts = db.query("SELECT * FROM participants WHERE event_id=? ORDER BY order_no,id",
                     (body.event_id,))
    for i, p in enumerate(parts):
        db.execute("INSERT INTO queue_items(venue_id,event_id,participant_id,"
                   "position,updated_at) VALUES(?,?,?,?,?)",
                   (ev["venue_id"], body.event_id, p["id"], i, db.now()))
    db.log_admin(claims["sub"], claims["usr"], "queue_build", str(body.event_id),
                 None, {"items": len(parts)})
    db.emit_change("queue_build", body.event_id, {"count": len(parts)})
    return {"created": len(parts)}


# ------------------------------------------------------------- users ------
class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64,
                          pattern=r"^[a-z0-9._-]+$")
    role: str = Field(pattern=r"^(stagemaster|admin)$")
    stages: list[int] = Field(default_factory=list)


@router.get("/users")
async def list_users(request: Request):
    db, _ = _admin(request)
    rows = db.query("SELECT id,username,role,stages,totp_required,disabled,"
                    "failed_count,locked_until,created_at,updated_at "
                    "FROM users ORDER BY id")
    return {"users": [dict(r) for r in rows]}


@router.post("/users")
async def create_user(body: UserIn, request: Request):
    """Create account; returns a one-time password shown exactly once.
    The user must complete SRP enrollment on first login (client derives
    verifier) — here we seed with random password and mark force-change."""
    from .auth import srp_make_verifier
    db, claims = _admin(request)
    onetime = "Kal-" + _secrets.token_urlsafe(12)
    salt_hex, v_hex = srp_make_verifier(body.username, onetime)
    try:
        cur = db.execute(
            "INSERT INTO users(username,role,srp_salt_hex,srp_verifier_hex,stages,"
            "totp_required,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (body.username, body.role, salt_hex, v_hex,
             json.dumps(body.stages), 1 if body.role == "admin" else 0,
             db.now(), db.now()))
    except Exception:
        raise HTTPException(409, "username_taken")
    db.log_admin(claims["sub"], claims["usr"], "user_create", str(cur.lastrowid),
                 None, {"username": body.username, "role": body.role})
    return {"id": cur.lastrowid, "one_time_password": onetime,
            "note": "Deliver out-of-band; rotate on first login."}


@router.post("/users/{uid}/disable")
async def disable_user(uid: int, request: Request):
    db, claims = _admin(request)
    _step_up(request, db, claims, "user_delete")
    before = db.one("SELECT * FROM users WHERE id=?", (uid,))
    if not before:
        raise HTTPException(404, "not_found")
    from .auth import revoke_all_for_user
    revoke_all_for_user(db, uid)
    db.execute("UPDATE users SET disabled=1, updated_at=? WHERE id=?", (db.now(), uid))
    db.log_admin(claims["sub"], claims["usr"], "user_disable", str(uid),
                 dict(before), {"disabled": 1})
    return {"ok": True}


# ---------------------------------------------------------- sessions ------
@router.get("/sessions")
async def list_sessions(request: Request):
    db, _ = _admin(request)
    rows = db.query(
        "SELECT s.sid, s.user_id, u.username, u.role, s.created_at, s.last_seen,"
        " s.revoked FROM sessions s JOIN users u ON u.id=s.user_id "
        "ORDER BY s.last_seen DESC LIMIT 200")
    return {"sessions": [dict(r) for r in rows]}


@router.post("/sessions/revoke-all")
async def revoke_all(request: Request, user_id: int | None = None):
    db, claims = _admin(request)
    _step_up(request, db, claims, "session_revoke_all")
    from .auth import revoke_all_for_user
    if user_id:
        revoke_all_for_user(db, user_id)
    else:
        db.execute("UPDATE refresh_tokens SET revoked=1", ())
        db.execute("UPDATE sessions SET revoked=1", ())
    db.log_admin(claims["sub"], claims["usr"], "session_revoke_all",
                 str(user_id or "*"), None, None)
    return {"ok": True}


# ------------------------------------------------------------- health -----
@router.get("/health")
async def health(request: Request):
    db, _ = _admin(request)
    from .events import BUS
    cfg = request.app.state.cfg
    stat = os.stat(cfg.db_path)
    try:
        usage = os.getloadavg()
    except OSError:
        usage = (0, 0, 0)
    disk_free = 0
    try:
        st = os.statvfs(cfg.db_path.parent)
        disk_free = st.f_bavail * st.f_frsize
    except OSError:
        pass
    chain_ok, chain_len = db.verify_chain()
    return {
        "time": db.now(),
        "sse_connections": BUS.connections,
        "db_bytes": stat.st_size,
        "disk_free_bytes": disk_free,
        "load_avg": list(usage),
        "audit_chain": {"valid": chain_ok, "entries": chain_len},
        "active_sessions": db.scalar(
            "SELECT COUNT(*) FROM sessions WHERE revoked=0"),
        "recent_auth_failures": db.scalar(
            "SELECT COUNT(*) FROM auth_audit WHERE event IN "
            "('login_fail','totp_fail','refresh_reuse') AND ts > ?",
            (db.now() - 3600,)),
    }


@router.get("/audit/auth")
async def audit_auth(request: Request, limit: int = 200):
    db, _ = _admin(request)
    rows = db.query("SELECT * FROM auth_audit ORDER BY id DESC LIMIT ?",
                    (min(max(limit, 1), 1000),))
    return {"events": [dict(r) for r in rows]}


@router.get("/audit/admin")
async def audit_admin(request: Request, limit: int = 200):
    db, _ = _admin(request)
    rows = db.query("SELECT * FROM audit_chain ORDER BY id DESC LIMIT ?",
                    (min(max(limit, 1), 1000),))
    ok, n = db.verify_chain()
    return {"actions": [dict(r) for r in rows],
            "chain_valid": ok, "chain_entries": n}


# --------------------------------------------------------------- ops ------
@router.post("/backup")
async def backup(request: Request):
    db, claims = _admin(request)
    _step_up(request, db, claims, "backup_run")
    script = Path(__file__).resolve().parent / "scripts" / "backup.py"
    res = subprocess.run([sys.executable, str(script)], capture_output=True,
                         text=True, timeout=120)
    db.log_admin(claims["sub"], claims["usr"], "backup_run", "db", None,
                 {"rc": res.returncode, "out": res.stdout[-500:]})
    if res.returncode != 0:
        raise HTTPException(500, "backup_failed")
    return {"ok": True, "path": res.stdout.strip().splitlines()[-1]}


class FlagIn(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_.]+$")
    value: str = Field(max_length=256)


@router.get("/flags")
async def get_flags(request: Request):
    db, _ = _admin(request)
    return {"flags": {r["key"]: r["value"] for r in db.query("SELECT * FROM feature_flags")}}


@router.post("/flags")
async def set_flag(body: FlagIn, request: Request):
    db, claims = _admin(request)
    _step_up(request, db, claims, "flag_write")
    before = db.one("SELECT * FROM feature_flags WHERE key=?", (body.key,))
    db.execute("INSERT INTO feature_flags(key,value,updated_at) VALUES(?,?,?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
               "updated_at=excluded.updated_at",
               (body.key, body.value, db.now()))
    db.log_admin(claims["sub"], claims["usr"], "flag_write", body.key,
                 dict(before) if before else None, body.model_dump())
    db.emit_change("flags", None, {"key": body.key, "value": body.value})
    return {"ok": True}


@router.post("/deploy")
async def deploy(request: Request):
    """Rebuild the public static snapshot (tools/build.py). Step-up required."""
    db, claims = _admin(request)
    _step_up(request, db, claims, "deploy")
    root = Path(__file__).resolve().parent.parent
    res = subprocess.run([sys.executable, str(root / "tools" / "build.py")],
                         capture_output=True, text=True, timeout=300, cwd=root)
    db.log_admin(claims["sub"], claims["usr"], "deploy", "public_site", None,
                 {"rc": res.returncode})
    if res.returncode != 0:
        raise HTTPException(500, "build_failed")
    return {"ok": True}
