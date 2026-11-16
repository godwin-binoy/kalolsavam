"""Admin API: master data CRUD, FullAuth user administration, dashboard, CSV exports."""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import shutil
import sqlite3
import time as _t
import uuid as _uuid
from pathlib import Path

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlmodel import select

from ..deps import client_ip, csv_cell, get_cfg, get_db, hash_ip, require_admin
from ..models import (
    AddToQueueIn,
    CategoryIn,
    CategoryUpdateIn,
    EventIn,
    EventUpdateIn,
    PasswordResetIn,
    QueueItemUpdateIn,
    QueueMoveIn,
    Role,
    User,
    UserIn,
    UserUpdateIn,
    VenueIn,
    VenueUpdateIn,
)
from .public import invalidate_public_cache

router = APIRouter()
log = logging.getLogger("kalolsavam")
_ph = PasswordHasher()


def _admin_log(db, request: Request, user: object, action: str, detail: str = "") -> None:
    try:
        secret = get_cfg(request).secret_key
        email = getattr(user, "email", "admin")
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (db.now(), email, hash_ip(client_ip(request), secret), "admin_action", f"{action}|{detail}"),
        )
    except Exception as exc:
        log.warning("audit_write_failed: %s", exc)


def _parse_uid(uid: str) -> _uuid.UUID | int | str:
    try:
        return _uuid.UUID(uid)
    except (ValueError, AttributeError):
        try:
            return int(uid)
        except ValueError:
            return uid


def _validate_stage_ids(db, stages: list[int]) -> None:
    if not stages:
        return
    valid = {r["id"] for r in db.q("SELECT id FROM venues")}
    invalid = [s for s in stages if s not in valid]
    if invalid:
        raise HTTPException(400, f"invalid_stage_ids:{invalid}")


def _collect_stats(db) -> dict[str, int]:
    row = db.one("""
        SELECT
            (SELECT COUNT(*) FROM venues) AS venues,
            (SELECT COUNT(*) FROM venues WHERE active = 1) AS active_venues,
            (SELECT COUNT(*) FROM categories) AS categories,
            (SELECT COUNT(*) FROM events) AS events,
            (SELECT COUNT(*) FROM participants WHERE deleted_at IS NULL) AS participants,
            COUNT(q.id) AS queue_items,
            COALESCE(SUM(CASE WHEN q.status = 'WAITING' THEN 1 ELSE 0 END), 0) AS queue_waiting,
            COALESCE(SUM(CASE WHEN q.status = 'ON-STAGE' THEN 1 ELSE 0 END), 0) AS queue_onstage_only,
            COALESCE(SUM(CASE WHEN q.status IN ('ON-STAGE', 'PAUSED') THEN 1 ELSE 0 END), 0) AS queue_active,
            COALESCE(SUM(CASE WHEN q.status = 'COMPLETE' THEN 1 ELSE 0 END), 0) AS queue_complete,
            COALESCE(SUM(CASE WHEN q.status = 'SKIPPED' THEN 1 ELSE 0 END), 0) AS queue_skipped
        FROM queue_items q
    """)
    return dict(row)


def _collect_health(db, cfg, sse_connections: int, fail_window_sec: int) -> dict[str, int | float]:
    try:
        db_bytes = os.stat(cfg.db_path).st_size
    except OSError:
        db_bytes = 0
    try:
        disk_free = shutil.disk_usage(cfg.db_path).free
    except OSError:
        disk_free = 0
    fails = db.one(
        "SELECT COUNT(*) c FROM auth_audit WHERE event = 'login_fail' AND ts > ?",
        (db.now() - fail_window_sec,),
    )["c"]
    return {
        "db_bytes": db_bytes,
        "disk_free_bytes": disk_free,
        "sse_connections": sse_connections,
        "auth_failures": fails,
    }


async def _get_or_create_role(session, role_name: str) -> Role:
    role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if not role:
        role = Role(name=role_name)
        session.add(role)
        await session.flush()
    return role


# ── Venues ────────────────────────────────────────────────────────────────────
@router.get("/venues")
def list_venues(request: Request, user=Depends(require_admin)):
    return {"venues": [dict(r) for r in get_db(request).q("SELECT * FROM venues ORDER BY id")]}


@router.post("/venues")
def create_venue(body: VenueIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    try:
        cur = db.ex(
            "INSERT INTO venues(name, kind, slug, active) VALUES (?,?,?,?)",
            (body.name, body.kind, body.slug, int(body.active)),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_slug") from exc
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "create_venue", f"id={cur.lastrowid}")
    return dict(db.one("SELECT * FROM venues WHERE id = ?", (cur.lastrowid,)))


@router.put("/venues/{vid}")
def update_venue(vid: int, body: VenueUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("SELECT * FROM venues WHERE id = ?", (vid,))
    if not row:
        raise HTTPException(404, "venue_not_found")
    name = body.name if body.name is not None else row["name"]
    kind = body.kind if body.kind is not None else row["kind"]
    slug = body.slug if "slug" in body.model_fields_set else row["slug"]
    active = int(body.active) if body.active is not None else row["active"]
    try:
        db.ex(
            "UPDATE venues SET name = ?, kind = ?, slug = ?, active = ? WHERE id = ?",
            (name, kind, slug, active, vid),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_slug") from exc
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "update_venue", f"id={vid}")
    return dict(db.one("SELECT * FROM venues WHERE id = ?", (vid,)))


@router.delete("/venues/{vid}")
def delete_venue(vid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    if not db.one("SELECT id FROM venues WHERE id = ?", (vid,)):
        raise HTTPException(404, "venue_not_found")
    if db.one("SELECT COUNT(*) c FROM events WHERE venue_id = ?", (vid,))["c"]:
        raise HTTPException(409, "venue_has_events")
    if db.one("SELECT COUNT(*) c FROM queue_items WHERE venue_id = ?", (vid,))["c"]:
        raise HTTPException(409, "venue_has_queue_items")
    with db.transaction():
        db.ex("DELETE FROM live_state WHERE venue_id = ?", (vid,))
        db.ex("DELETE FROM venues WHERE id = ?", (vid,))
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "delete_venue", f"id={vid}")
    return {"ok": True}


# ── Categories ────────────────────────────────────────────────────────────────
@router.get("/categories")
def list_categories(request: Request, user=Depends(require_admin)):
    return {"categories": [dict(r) for r in get_db(request).q("SELECT * FROM categories ORDER BY name")]}


@router.post("/categories")
def create_category(body: CategoryIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    cur = db.ex("INSERT INTO categories(name, grp) VALUES (?,?)", (body.name, body.group))
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "create_category", f"id={cur.lastrowid}")
    return {"id": cur.lastrowid}


@router.put("/categories/{cid}")
def update_category(cid: int, body: CategoryUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("SELECT * FROM categories WHERE id = ?", (cid,))
    if not row:
        raise HTTPException(404, "category_not_found")
    name = body.name if body.name is not None else row["name"]
    group = body.group if body.group is not None else row["grp"]
    db.ex("UPDATE categories SET name = ?, grp = ? WHERE id = ?", (name, group, cid))
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "update_category", f"id={cid}")
    return dict(db.one("SELECT * FROM categories WHERE id = ?", (cid,)))


@router.delete("/categories/{cid}")
def delete_category(cid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    if not db.one("SELECT id FROM categories WHERE id = ?", (cid,)):
        raise HTTPException(404, "category_not_found")
    if db.one("SELECT COUNT(*) c FROM events WHERE category_id = ?", (cid,))["c"]:
        raise HTTPException(409, "category_has_events")
    db.ex("DELETE FROM categories WHERE id = ?", (cid,))
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "delete_category", f"id={cid}")
    return {"ok": True}


# ── Events ────────────────────────────────────────────────────────────────────
@router.get("/events")
def list_events(request: Request, venue_id: int | None = None, user=Depends(require_admin)):
    db = get_db(request)
    q = "SELECT * FROM events"
    params: tuple = ()
    if venue_id is not None:
        q += " WHERE venue_id = ?"
        params = (venue_id,)
    return {"events": [dict(r) for r in db.q(q + " ORDER BY id LIMIT 5000", params)]}


@router.post("/events")
def create_event(body: EventIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    try:
        cur = db.ex(
            "INSERT INTO events(code, title, category_id, venue_id, day, scheduled_time) VALUES (?,?,?,?,?,?)",
            (body.code, body.title, body.category_id, body.venue_id, body.day, body.scheduled_time),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_or_fk") from exc
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "create_event", f"id={cur.lastrowid},code={body.code}")
    return {"id": cur.lastrowid}


@router.put("/events/{eid}")
def update_event(eid: int, body: EventUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("SELECT * FROM events WHERE id = ?", (eid,))
    if not row:
        raise HTTPException(404, "event_not_found")
    code = body.code if body.code is not None else row["code"]
    title = body.title if body.title is not None else row["title"]
    cat = body.category_id if body.category_id is not None else row["category_id"]
    ven = body.venue_id if body.venue_id is not None else row["venue_id"]
    day = body.day if body.day is not None else row["day"]
    when = body.scheduled_time if body.scheduled_time is not None else row["scheduled_time"]
    try:
        db.ex(
            "UPDATE events SET code = ?, title = ?, category_id = ?, venue_id = ?, "
            "day = ?, scheduled_time = ? WHERE id = ?",
            (code, title, cat, ven, day, when, eid),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_code_or_fk") from exc
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "update_event", f"id={eid}")
    return dict(db.one("SELECT * FROM events WHERE id = ?", (eid,)))


@router.delete("/events/{eid}")
def delete_event(eid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    if not db.one("SELECT id FROM events WHERE id = ?", (eid,)):
        raise HTTPException(404, "event_not_found")
    if db.one("SELECT COUNT(*) c FROM queue_items WHERE event_id = ?", (eid,))["c"]:
        raise HTTPException(409, "event_has_queue_items")
    db.ex("DELETE FROM events WHERE id = ?", (eid,))
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "delete_event", f"id={eid}")
    return {"ok": True}


# ── Queue ─────────────────────────────────────────────────────────────────────
@router.get("/queue")
def list_queue(request: Request, venue_id: int | None = None, user=Depends(require_admin)):
    db = get_db(request)
    q = """
        SELECT q.id, q.venue_id, q.event_id, q.participant_entry_id, q.chest_no,
               q.status, q.position, q.version, q.started_at, q.completed_at,
               e.title AS event_title, e.code AS event_code,
               p.school_name AS school, p.name AS student_name, p.register_no AS roll
        FROM queue_items q
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participant_entries pe ON pe.id = q.participant_entry_id
        LEFT JOIN participants p ON p.id = pe.participant_id
    """
    params: tuple = ()
    if venue_id is not None:
        q += " WHERE q.venue_id = ?"
        params = (venue_id,)
    q += " ORDER BY q.venue_id, q.position LIMIT 2000"
    return {"items": [dict(r) for r in db.q(q, params)]}


@router.put("/queue/{item_id}")
def update_queue_item(item_id: int, body: QueueItemUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        row = db.one("SELECT id FROM queue_items WHERE id = ?", (item_id,))
        if not row:
            raise HTTPException(404, "not_found")
        chest = body.chest_no.strip() if body.chest_no and body.chest_no.strip() else None
        db.ex(
            "UPDATE queue_items SET chest_no = ?, version = version + 1, updated_at = ? WHERE id = ?",
            (chest, db.now(), item_id),
        )
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "queue_edit", f"id={item_id}")
    return {"ok": True}


@router.delete("/queue/{item_id}")
def delete_queue_item(item_id: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        row = db.one("SELECT status FROM queue_items WHERE id = ?", (item_id,))
        if not row:
            raise HTTPException(404, "not_found")
        if row["status"] != "WAITING":
            raise HTTPException(409, "only_waiting_items_deletable")
        db.ex("DELETE FROM queue_items WHERE id = ?", (item_id,))
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "queue_delete", f"id={item_id}")
    return {"ok": True}


@router.post("/queue/{item_id}/move")
def move_queue_item(item_id: int, body: QueueMoveIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        item = db.one("SELECT * FROM queue_items WHERE id = ?", (item_id,))
        if not item:
            raise HTTPException(404, "not_found")
        venue_id = item["venue_id"]
        cur_pos = item["position"]
        cmp_op, order_dir = ("<", "DESC") if body.direction == "up" else (">", "ASC")
        neighbor = db.one(
            f"SELECT * FROM queue_items WHERE venue_id = ? AND position {cmp_op} ? "  # noqa: S608
            f"ORDER BY position {order_dir} LIMIT 1",
            (venue_id, cur_pos),
        )
        if not neighbor:
            return {"ok": True, "moved": False}
        now = db.now()
        db.ex(
            "UPDATE queue_items SET position = ?, version = version + 1, updated_at = ? WHERE id = ?",
            (neighbor["position"], now, item_id),
        )
        db.ex(
            "UPDATE queue_items SET position = ?, version = version + 1, updated_at = ? WHERE id = ?",
            (cur_pos, now, neighbor["id"]),
        )
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "queue_move", f"id={item_id},dir={body.direction}")
    return {"ok": True, "moved": True}


@router.post("/queue")
def add_to_queue(body: AddToQueueIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        if not db.one("SELECT id FROM venues WHERE id = ?", (body.venue_id,)):
            raise HTTPException(404, "venue_not_found")
        entry = db.one("""
            SELECT pe.id, pe.item_code
            FROM participant_entries pe
            JOIN participants p ON p.id = pe.participant_id
            WHERE pe.id = ? AND pe.deleted_at IS NULL AND p.deleted_at IS NULL
        """, (body.participant_entry_id,))
        if not entry:
            raise HTTPException(404, "participant_entry_not_found")
        ev = db.one("SELECT id, venue_id FROM events WHERE code = ?", (entry["item_code"],))
        if not ev:
            raise HTTPException(404, "event_not_found_for_item")
        if ev["venue_id"] is not None and ev["venue_id"] != body.venue_id:
            raise HTTPException(409, "event_venue_mismatch")

        row = db.one("SELECT COALESCE(MAX(position),-1)+1 AS p FROM queue_items WHERE venue_id = ?", (body.venue_id,))
        chest = body.chest_no.strip() if body.chest_no and body.chest_no.strip() else None
        cur_q = db.ex(
            "INSERT INTO queue_items(venue_id, event_id, participant_entry_id, chest_no, status, position, version, updated_at) "
            "VALUES (?,?,?,?, 'WAITING', ?, 1, ?)",
            (body.venue_id, ev["id"], entry["id"], chest, row["p"], db.now()),
        )
    invalidate_public_cache(request.app)
    _admin_log(db, request, user, "queue_add", f"venue={body.venue_id},event={ev['id']}")
    return {"id": cur_q.lastrowid}


# ── FullAuth Users Administration ─────────────────────────────────────────────
@router.get("/users")
async def list_users(request: Request, user=Depends(require_admin)):
    async with request.app.state.auth_session_maker() as session:
        users = (await session.execute(select(User).order_by(User.email))).scalars().all()
        return {
            "users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "stages": u.stages,
                    "roles": [r.name for r in u.roles],
                    "disabled": not u.is_active,
                }
                for u in users
            ]
        }


@router.post("/users")
async def create_user(body: UserIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _validate_stage_ids(db, body.stages)
    async with request.app.state.auth_session_maker() as session:
        clean_email = body.email.strip().lower()
        if (await session.execute(select(User).where(User.email == clean_email))).scalar_one_or_none():
            raise HTTPException(409, "email_taken")
        role = await _get_or_create_role(session, body.role)
        u = User(
            email=clean_email,
            hashed_password=_ph.hash(body.password),
            is_active=True,
            is_verified=True,
            stages=json.dumps(body.stages),
        )
        u.roles.append(role)
        session.add(u)
        await session.commit()
        await session.refresh(u)
        _admin_log(db, request, user, "create_user", f"id={u.id},role={body.role}")
        return {"id": str(u.id), "email": u.email, "role": body.role}


@router.put("/users/{uid}")
async def update_user(uid: str, body: UserUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    if body.stages is not None:
        _validate_stage_ids(db, body.stages)
    async with request.app.state.auth_session_maker() as session:
        target = await session.get(User, _parse_uid(uid))
        if not target:
            raise HTTPException(404, "not_found")

        curr_user_id = str(getattr(user, "id", ""))
        if str(target.id) == curr_user_id:
            if body.is_active is False or (body.role is not None and body.role != "admin"):
                raise HTTPException(400, "cannot_modify_own_access")

        if body.email is not None and body.email.strip().lower() != target.email:
            new_email = body.email.strip().lower()
            if (await session.execute(select(User).where(User.email == new_email))).scalar_one_or_none():
                raise HTTPException(409, "email_taken")
            target.email = new_email
        if body.stages is not None:
            target.stages = json.dumps(body.stages)
        if body.is_active is not None:
            target.is_active = body.is_active
        if body.role is not None:
            new_role = await _get_or_create_role(session, body.role)
            target.roles.clear()
            target.roles.append(new_role)

        session.add(target)
        await session.commit()
        _admin_log(db, request, user, "update_user", f"id={target.id}")
        return {"ok": True}


@router.post("/users/{uid}/disable")
async def disable_user(uid: str, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    curr_user_id = str(getattr(user, "id", ""))
    async with request.app.state.auth_session_maker() as session:
        u = await session.get(User, _parse_uid(uid))
        if not u:
            raise HTTPException(404, "not_found")
        if str(u.id) == curr_user_id:
            raise HTTPException(400, "cannot_disable_self")
        u.is_active = False
        session.add(u)
        await session.commit()
        _admin_log(db, request, user, "disable_user", f"id={u.id}")
        return {"ok": True}


@router.post("/users/{uid}/enable")
async def enable_user(uid: str, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    async with request.app.state.auth_session_maker() as session:
        u = await session.get(User, _parse_uid(uid))
        if not u:
            raise HTTPException(404, "not_found")
        u.is_active = True
        session.add(u)
        await session.commit()
        _admin_log(db, request, user, "enable_user", f"id={u.id}")
        return {"ok": True}


@router.post("/users/{uid}/reset-password")
async def reset_user_password(uid: str, body: PasswordResetIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    async with request.app.state.auth_session_maker() as session:
        u = await session.get(User, _parse_uid(uid))
        if not u:
            raise HTTPException(404, "not_found")
        u.hashed_password = _ph.hash(body.password)
        session.add(u)
        await session.commit()
        _admin_log(db, request, user, "reset_password", f"id={u.id}")
        return {"ok": True}


# ── Audit / Stats / Health / Backup ───────────────────────────────────────────
@router.get("/audit")
def list_audit(request: Request, limit: int = 100, offset: int = 0, user=Depends(require_admin)):
    limit = max(1, min(limit, 500))
    rows = get_db(request).q(
        "SELECT * FROM auth_audit ORDER BY ts DESC LIMIT ? OFFSET ?", (limit, offset)
    )
    return {"items": [dict(r) for r in rows]}


@router.get("/stats")
def stats(request: Request, user=Depends(require_admin)):
    s = _collect_stats(get_db(request))
    return {
        "venues": s["venues"],
        "categories": s["categories"],
        "events": s["events"],
        "participants": s["participants"],
        "queue_items": s["queue_items"],
        "queue_waiting": s["queue_waiting"],
        "queue_onstage": s["queue_onstage_only"],
        "queue_complete": s["queue_complete"],
    }


@router.get("/health")
def health(request: Request, user=Depends(require_admin)):
    db, cfg = get_db(request), get_cfg(request)
    h = _collect_health(db, cfg, len(request.app.state.subscribers), 3600)
    return {
        "time": db.now(),
        "db_bytes": h["db_bytes"],
        "sse_connections": h["sse_connections"],
        "disk_free_bytes": h["disk_free_bytes"],
        "recent_auth_failures": h["auth_failures"],
    }


@router.post("/backup")
def backup(request: Request, user=Depends(require_admin)):
    db, cfg = get_db(request), get_cfg(request)
    dst_dir = Path(cfg.db_path).parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    ts = _t.strftime("%Y%m%d-%H%M%S")
    src = Path(cfg.db_path)
    if not src.exists():
        raise HTTPException(500, "db_not_found")

    dst = dst_dir / f"{src.stem}-{ts}.db"
    src_con = sqlite3.connect(str(src))
    dst_con = sqlite3.connect(str(dst))
    try:
        src_con.backup(dst_con)
    finally:
        dst_con.close()
        src_con.close()

    existing = sorted(dst_dir.glob(f"{src.stem}-*.db"), key=lambda f: f.stat().st_mtime)
    for old in existing[:-24]:
        try:
            old.unlink()
        except OSError:
            pass

    _admin_log(db, request, user, "backup", f"file={dst.name}")
    return {"ok": True, "backups": [str(dst)]}


@router.get("/export/participants.csv")
def export_participants(request: Request, user=Depends(require_admin)):
    rows = get_db(request).q("""
        SELECT q.id, v.name AS venue, e.code AS event_code, e.title AS event,
               p.school_name AS school, p.name AS student_name,
               COALESCE(q.chest_no, p.register_no) AS roll, q.status, q.position
        FROM queue_items q
        JOIN venues v ON v.id = q.venue_id
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participant_entries pe ON pe.id = q.participant_entry_id
        LEFT JOIN participants p ON p.id = pe.participant_id
        ORDER BY v.id, q.position
    """)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "venue", "event_code", "event", "school",
                "student_name", "roll", "status", "position"])
    for r in rows:
        w.writerow([
            r["id"],
            csv_cell(r["venue"]),
            csv_cell(r["event_code"]),
            csv_cell(r["event"]),
            csv_cell(r["school"]),
            csv_cell(r["student_name"]),
            csv_cell(r["roll"]),
            r["status"],
            r["position"],
        ])
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants.csv"},
    )
