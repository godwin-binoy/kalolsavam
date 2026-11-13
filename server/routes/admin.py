"""Admin API: master data CRUD, FullAuth users, health, audit, exports."""
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
from collections import defaultdict
from pathlib import Path

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlmodel import select

from ..auth import Role, User
from ..deps import client_ip, get_cfg, get_db, hash_ip, require_admin
from ..models import (
    AddToQueueIn, CategoryIn, CategoryUpdateIn, EventIn, EventUpdateIn,
    PasswordResetIn, QueueItemUpdateIn, QueueMoveIn, UserIn, UserUpdateIn,
    VenueIn, VenueUpdateIn,
)

router = APIRouter()
log = logging.getLogger("kalolsavam")
_ph = PasswordHasher()


def _admin_log(db, request: Request, user: User, action: str, detail: str = "") -> None:
    try:
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) "
            "VALUES (?,?,?,?,?)",
            (db.now(), user.email, hash_ip(client_ip(request)),
             "admin_action", f"{action}|{detail}"),
        )
    except Exception as exc:
        log.warning("audit_write_failed: %s", exc)


def _parse_uid(uid: str):
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
            (SELECT COUNT(*) FROM participants) AS participants,
            (SELECT COUNT(*) FROM scores) AS scores_entered,
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


def _compute_leaderboard(db) -> dict[str, list[dict]]:
    rows = db.q("""
        SELECT q.id AS queue_item_id, e.id AS event_id, e.code AS event_code,
               e.title AS event_title, p.school,
               COALESCE(SUM(s.value), 0) AS total_score,
               COUNT(s.id) AS judge_count
        FROM queue_items q
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participants p ON p.id = q.participant_id
        LEFT JOIN scores s ON s.queue_item_id = q.id
        WHERE q.status IN ('COMPLETE','ON-STAGE','PAUSED')
        GROUP BY q.id
    """)
    by_event = defaultdict(list)
    for r in rows:
        if r["judge_count"] and r["school"]:
            by_event[r["event_id"]].append(dict(r))

    points = defaultdict(lambda: {"first": 0, "second": 0, "third": 0, "total": 0})
    per_event = []
    for eid, items in by_event.items():
        items.sort(key=lambda x: (x["total_score"], x["judge_count"]), reverse=True)
        winners = []
        for rank, it in enumerate(items[:3], start=1):
            pts = {1: 5, 2: 3, 3: 1}[rank]
            school = it["school"]
            points[school]["total"] += pts
            if rank == 1:
                points[school]["first"] += 1
            elif rank == 2:
                points[school]["second"] += 1
            else:
                points[school]["third"] += 1
            winners.append({
                "rank": rank,
                "school": school,
                "total_score": round(it["total_score"], 2),
                "points": pts,
            })
        per_event.append({
            "event_id": eid,
            "event_code": items[0]["event_code"],
            "event_title": items[0]["event_title"],
            "winners": winners,
        })

    school_totals = [
        {"school": school, **data}
        for school, data in sorted(points.items(), key=lambda x: -x[1]["total"])
    ]
    return {"schools": school_totals, "events": per_event}


# ── Venues ────────────────────────────────────────────────────────────
@router.get("/venues")
def list_venues(request: Request, user=Depends(require_admin)):
    db = get_db(request)
    return {"venues": [dict(r) for r in db.q("SELECT * FROM venues ORDER BY id")]}


@router.post("/venues")
def create_venue(body: VenueIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    cur = db.ex(
        "INSERT INTO venues(name, kind, active) VALUES (?,?,?)",
        (body.name, body.kind, int(body.active)),
    )
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
    active = int(body.active) if body.active is not None else row["active"]
    db.ex(
        "UPDATE venues SET name = ?, kind = ?, active = ? WHERE id = ?",
        (name, kind, active, vid),
    )
    _admin_log(db, request, user, "update_venue", f"id={vid}")
    return dict(db.one("SELECT * FROM venues WHERE id = ?", (vid,)))


@router.delete("/venues/{vid}")
def delete_venue(vid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("SELECT * FROM venues WHERE id = ?", (vid,))
    if not row:
        raise HTTPException(404, "venue_not_found")
    if db.one("SELECT COUNT(*) c FROM events WHERE venue_id = ?", (vid,))["c"]:
        raise HTTPException(409, "venue_has_events")
    if db.one("SELECT COUNT(*) c FROM queue_items WHERE venue_id = ?", (vid,))["c"]:
        raise HTTPException(409, "venue_has_queue_items")
    with db.transaction():
        db.ex("DELETE FROM live_state WHERE venue_id = ?", (vid,))
        db.ex("DELETE FROM venues WHERE id = ?", (vid,))
    _admin_log(db, request, user, "delete_venue", f"id={vid}")
    return {"ok": True}


# ── Categories ────────────────────────────────────────────────────────
@router.get("/categories")
def list_categories(request: Request, user=Depends(require_admin)):
    db = get_db(request)
    return {"categories": [dict(r) for r in db.q("SELECT * FROM categories ORDER BY name")]}


@router.post("/categories")
def create_category(body: CategoryIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    cur = db.ex("INSERT INTO categories(name, grp) VALUES (?,?)", (body.name, body.group))
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
    _admin_log(db, request, user, "update_category", f"id={cid}")
    return dict(db.one("SELECT * FROM categories WHERE id = ?", (cid,)))


@router.delete("/categories/{cid}")
def delete_category(cid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("SELECT * FROM categories WHERE id = ?", (cid,))
    if not row:
        raise HTTPException(404, "category_not_found")
    if db.one("SELECT COUNT(*) c FROM events WHERE category_id = ?", (cid,))["c"]:
        raise HTTPException(409, "category_has_events")
    db.ex("DELETE FROM categories WHERE id = ?", (cid,))
    _admin_log(db, request, user, "delete_category", f"id={cid}")
    return {"ok": True}


# ── Events ────────────────────────────────────────────────────────────
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
            "INSERT INTO events(code, title, category_id, venue_id, day, scheduled_time) "
            "VALUES (?,?,?,?,?,?)",
            (body.code, body.title, body.category_id, body.venue_id, body.day, body.scheduled_time),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "duplicate_or_fk")
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
            " day = ?, scheduled_time = ? WHERE id = ?",
            (code, title, cat, ven, day, when, eid),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "duplicate_code_or_fk")
    _admin_log(db, request, user, "update_event", f"id={eid}")
    return dict(db.one("SELECT * FROM events WHERE id = ?", (eid,)))


@router.delete("/events/{eid}")
def delete_event(eid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("SELECT * FROM events WHERE id = ?", (eid,))
    if not row:
        raise HTTPException(404, "event_not_found")
    if db.one("SELECT COUNT(*) c FROM queue_items WHERE event_id = ?", (eid,))["c"]:
        raise HTTPException(409, "event_has_queue_items")
    with db.transaction():
        db.ex("DELETE FROM participants WHERE event_id = ?", (eid,))
        db.ex("DELETE FROM events WHERE id = ?", (eid,))
    _admin_log(db, request, user, "delete_event", f"id={eid}")
    return {"ok": True}


# ── Queue ─────────────────────────────────────────────────────────────
@router.get("/queue")
def list_queue(request: Request, venue_id: int | None = None, user=Depends(require_admin)):
    db = get_db(request)
    q = """
        SELECT q.id, q.venue_id, q.event_id, q.participant_id, q.status, q.position,
               q.version, q.started_at, q.completed_at,
               e.title AS event_title, e.code AS event_code,
               p.school, p.student_name, p.roll
        FROM queue_items q
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participants p ON p.id = q.participant_id
    """
    params: tuple = ()
    if venue_id is not None:
        q += " WHERE q.venue_id = ?"
        params = (venue_id,)
    q += " ORDER BY q.venue_id, q.position LIMIT 2000"
    return {"items": [dict(r) for r in db.q(q, params)]}


@router.get("/queue/{item_id}")
def get_queue_item(item_id: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("""
        SELECT q.*, e.title AS event_title, e.code AS event_code,
               p.school, p.student_name, p.roll
        FROM queue_items q
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participants p ON p.id = q.participant_id
        WHERE q.id = ?
    """, (item_id,))
    if not row:
        raise HTTPException(404, "not_found")
    scores = db.q(
        "SELECT judge_no, value, entered_by, entered_at FROM scores "
        "WHERE queue_item_id = ? ORDER BY judge_no",
        (item_id,),
    )
    total = sum(s["value"] for s in scores)
    mean = total / len(scores) if scores else None
    return {
        "item": dict(row),
        "scores": [dict(s) for s in scores],
        "total": round(total, 2),
        "mean": round(mean, 2) if mean is not None else None,
    }


@router.put("/queue/{item_id}")
def update_queue_item(item_id: int, body: QueueItemUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        row = db.one("SELECT * FROM queue_items WHERE id = ?", (item_id,))
        if not row:
            raise HTTPException(404, "not_found")
        pid = row["participant_id"]
        if not pid:
            raise HTTPException(409, "no_participant")
        updates: list[str] = []
        params: list = []
        if body.school is not None:
            updates.append("school = ?")
            params.append(body.school)
        if body.student_name is not None:
            updates.append("student_name = ?")
            params.append(body.student_name.strip() or None)
        if body.roll is not None:
            updates.append("roll = ?")
            params.append(body.roll.strip() or None)
        if updates:
            params.append(pid)
            db.ex(f"UPDATE participants SET {', '.join(updates)} WHERE id = ?", tuple(params))
        db.ex(
            "UPDATE queue_items SET version = version + 1, updated_at = ? WHERE id = ?",
            (db.now(), item_id),
        )
    _admin_log(db, request, user, "queue_edit", f"id={item_id}")
    return {"ok": True}


@router.delete("/queue/{item_id}")
def delete_queue_item(item_id: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        row = db.one("SELECT * FROM queue_items WHERE id = ?", (item_id,))
        if not row:
            raise HTTPException(404, "not_found")
        if row["status"] != "WAITING":
            raise HTTPException(409, "only_waiting_items_deletable")
        db.ex("DELETE FROM queue_items WHERE id = ?", (item_id,))
        if row["participant_id"]:
            db.ex("DELETE FROM participants WHERE id = ?", (row["participant_id"],))
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

        op, order = ("<", "DESC") if body.direction == "up" else (">", "ASC")
        neighbor = db.one(
            f"SELECT * FROM queue_items WHERE venue_id = ? AND position {op} ? "
            f"ORDER BY position {order} LIMIT 1",
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
    _admin_log(db, request, user, "queue_move", f"id={item_id},dir={body.direction}")
    return {"ok": True, "moved": True}


@router.post("/queue")
def add_to_queue(body: AddToQueueIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        if not db.one("SELECT id FROM venues WHERE id = ?", (body.venue_id,)):
            raise HTTPException(404, "venue_not_found")
        if not db.one("SELECT id FROM events WHERE id = ?", (body.event_id,)):
            raise HTTPException(404, "event_not_found")
        cur_p = db.ex(
            "INSERT INTO participants(event_id, school, student_name, roll) VALUES (?,?,?,?)",
            (
                body.event_id,
                body.school,
                (body.student_name or "").strip() or None,
                (body.roll or "").strip() or None,
            ),
        )
        pid = cur_p.lastrowid
        row = db.one(
            "SELECT COALESCE(MAX(position),-1)+1 AS p FROM queue_items WHERE venue_id = ?",
            (body.venue_id,),
        )
        cur_q = db.ex(
            "INSERT INTO queue_items(venue_id, event_id, participant_id, status, "
            " position, version, updated_at) VALUES (?,?,?, 'WAITING', ?, 1, ?)",
            (body.venue_id, body.event_id, pid, row["p"], db.now()),
        )
    _admin_log(db, request, user, "queue_add", f"venue={body.venue_id},event={body.event_id}")
    return {"id": cur_q.lastrowid, "participant_id": pid}


# ── Users ─────────────────────────────────────────────────────────────
@router.get("/users")
async def list_users(request: Request, user=Depends(require_admin)):
    async with request.app.state.auth_session_maker() as session:
        result = await session.execute(select(User).order_by(User.email))
        users = result.scalars().all()
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
    _validate_stage_ids(get_db(request), body.stages)
    async with request.app.state.auth_session_maker() as session:
        existing = (
            await session.execute(select(User).where(User.email == body.email))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(409, "email_taken")
        role = (
            await session.execute(select(Role).where(Role.name == body.role))
        ).scalar_one_or_none()
        if not role:
            raise HTTPException(400, "role_missing")
        u = User(
            email=body.email,
            hashed_password=_ph.hash(body.password),
            is_active=True,
            is_verified=True,
            stages=json.dumps(body.stages),
        )
        u.roles.append(role)
        session.add(u)
        await session.commit()
        return {"id": str(u.id), "email": u.email, "role": body.role}


@router.put("/users/{uid}")
async def update_user(uid: str, body: UserUpdateIn, request: Request, user=Depends(require_admin)):
    if body.stages is not None:
        _validate_stage_ids(get_db(request), body.stages)
    async with request.app.state.auth_session_maker() as session:
        target = await session.get(User, _parse_uid(uid))
        if not target:
            raise HTTPException(404, "not_found")
        if body.email is not None and body.email != target.email:
            dup = (
                await session.execute(select(User).where(User.email == body.email))
            ).scalar_one_or_none()
            if dup:
                raise HTTPException(409, "email_taken")
            target.email = body.email
        if body.stages is not None:
            target.stages = json.dumps(body.stages)
        if body.is_active is not None:
            target.is_active = body.is_active
        if body.role is not None:
            new_role = (
                await session.execute(select(Role).where(Role.name == body.role))
            ).scalar_one_or_none()
            if not new_role:
                raise HTTPException(400, "role_missing")
            target.roles.clear()
            target.roles.append(new_role)
        session.add(target)
        await session.commit()
        return {"ok": True}


@router.post("/users/{uid}/disable")
async def disable_user(uid: str, request: Request, user=Depends(require_admin)):
    async with request.app.state.auth_session_maker() as session:
        u = await session.get(User, _parse_uid(uid))
        if not u:
            raise HTTPException(404, "not_found")
        u.is_active = False
        session.add(u)
        await session.commit()
        return {"ok": True}


@router.post("/users/{uid}/enable")
async def enable_user(uid: str, request: Request, user=Depends(require_admin)):
    async with request.app.state.auth_session_maker() as session:
        u = await session.get(User, _parse_uid(uid))
        if not u:
            raise HTTPException(404, "not_found")
        u.is_active = True
        session.add(u)
        await session.commit()
        return {"ok": True}


@router.post("/users/{uid}/reset-password")
async def reset_user_password(uid: str, body: PasswordResetIn, request: Request, user=Depends(require_admin)):
    async with request.app.state.auth_session_maker() as session:
        u = await session.get(User, _parse_uid(uid))
        if not u:
            raise HTTPException(404, "not_found")
        u.hashed_password = _ph.hash(body.password)
        session.add(u)
        await session.commit()
        return {"ok": True}


# ── Audit / Stats / Health ────────────────────────────────────────────
@router.get("/audit")
def list_audit(request: Request, limit: int = 100, offset: int = 0, user=Depends(require_admin)):
    limit = max(1, min(limit, 500))
    db = get_db(request)
    rows = db.q("SELECT * FROM auth_audit ORDER BY ts DESC LIMIT ? OFFSET ?", (limit, offset))
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
        "scores_entered": s["scores_entered"],
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
    cfg = get_cfg(request)
    dst_dir = Path(cfg.db_path).parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    ts = _t.strftime("%Y%m%d-%H%M%S")

    paths = [cfg.db_path]
    if cfg.auth_db_path and cfg.auth_db_path != cfg.db_path:
        paths.append(cfg.auth_db_path)

    backed_up = []
    for p in paths:
        src = Path(p)
        if not src.exists():
            continue
        dst = dst_dir / f"{src.stem}-{ts}.db"
        src_con = sqlite3.connect(str(src))
        dst_con = sqlite3.connect(str(dst))
        try:
            src_con.backup(dst_con)
        finally:
            dst_con.close()
            src_con.close()
        backed_up.append(str(dst))

        # Keep the 24 newest backups per database stem.
        existing = sorted(dst_dir.glob(f"{src.stem}-*.db"), key=lambda f: f.stat().st_mtime)
        for old in existing[:-24]:
            try:
                old.unlink()
            except OSError:
                pass
    return {"ok": True, "backups": backed_up}


# ── Leaderboard / Dashboard / Exports ─────────────────────────────────
@router.get("/leaderboard")
def leaderboard(request: Request, user=Depends(require_admin)):
    return _compute_leaderboard(get_db(request))


@router.get("/dashboard")
def dashboard(request: Request, user=Depends(require_admin)):
    """Aggregated stats for the /dashboard/ statistics page."""
    db, cfg = get_db(request), get_cfg(request)
    s = _collect_stats(db)
    overall = {
        "venues": s["venues"],
        "active_venues": s["active_venues"],
        "categories": s["categories"],
        "events": s["events"],
        "participants": s["participants"],
        "queue_items": s["queue_items"],
        "queue_waiting": s["queue_waiting"],
        "queue_onstage": s["queue_active"],
        "queue_complete": s["queue_complete"],
        "queue_skipped": s["queue_skipped"],
        "scores_entered": s["scores_entered"],
    }

    per_venue = [
        dict(r) for r in db.q("""
            SELECT v.id, v.name, v.kind, v.active,
                   COUNT(q.id) AS total,
                   SUM(CASE WHEN q.status='WAITING' THEN 1 ELSE 0 END) AS waiting,
                   SUM(CASE WHEN q.status IN ('ON-STAGE','PAUSED') THEN 1 ELSE 0 END) AS onstage,
                   SUM(CASE WHEN q.status='COMPLETE' THEN 1 ELSE 0 END) AS complete,
                   SUM(CASE WHEN q.status='SKIPPED' THEN 1 ELSE 0 END) AS skipped
            FROM venues v
            LEFT JOIN queue_items q ON q.venue_id = v.id
            GROUP BY v.id
            ORDER BY v.id
        """)
    ]

    lb = _compute_leaderboard(db)
    recent_scores = [
        dict(r) for r in db.q("""
            SELECT s.queue_item_id, s.judge_no, s.value, s.entered_at,
                   e.code AS event_code, e.title AS event_title,
                   p.school, p.student_name
            FROM scores s
            JOIN queue_items q ON q.id = s.queue_item_id
            JOIN events e ON e.id = q.event_id
            LEFT JOIN participants p ON p.id = q.participant_id
            ORDER BY s.entered_at DESC LIMIT 20
        """)
    ]
    recent_completed = [
        dict(r) for r in db.q("""
            SELECT q.id, q.completed_at, e.code AS event_code, e.title AS event_title,
                   p.school, p.student_name
            FROM queue_items q
            JOIN events e ON e.id = q.event_id
            LEFT JOIN participants p ON p.id = q.participant_id
            WHERE q.status='COMPLETE' AND q.completed_at IS NOT NULL
            ORDER BY q.completed_at DESC LIMIT 20
        """)
    ]
    health_data = _collect_health(db, cfg, len(request.app.state.subscribers), 86400)

    return {
        "updated_at": db.now(),
        "overall": overall,
        "per_venue": per_venue,
        "top_schools": lb["schools"][:10],
        "recent_scores": recent_scores,
        "recent_completed": recent_completed,
        "health": {
            "db_bytes": health_data["db_bytes"],
            "disk_free_bytes": health_data["disk_free_bytes"],
            "sse_connections": health_data["sse_connections"],
            "auth_failures_24h": health_data["auth_failures"],
        },
    }


@router.get("/export/participants.csv")
def export_participants(request: Request, user=Depends(require_admin)):
    db = get_db(request)
    rows = db.q("""
        SELECT q.id, v.name AS venue, e.code AS event_code, e.title AS event,
               p.school, p.student_name, p.roll, q.status, q.position
        FROM queue_items q
        JOIN venues v ON v.id = q.venue_id
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participants p ON p.id = q.participant_id
        ORDER BY v.id, q.position
    """)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id", "venue", "event_code", "event", "school",
                "student_name", "roll", "status", "position"])
    for r in rows:
        w.writerow([r["id"], r["venue"], r["event_code"], r["event"],
                    r["school"] or "", r["student_name"] or "", r["roll"] or "",
                    r["status"], r["position"]])
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants.csv"},
    )


@router.get("/export/results.csv")
def export_results(request: Request, user=Depends(require_admin)):
    db = get_db(request)
    rows = db.q("""
        SELECT q.id AS queue_item_id, v.name AS venue,
               e.code AS event_code, e.title AS event,
               p.school, p.student_name, p.roll,
               COUNT(s.id) AS judges,
               COALESCE(SUM(s.value), 0) AS total,
               CASE WHEN COUNT(s.id) > 0 THEN SUM(s.value)/COUNT(s.id) ELSE NULL END AS average
        FROM queue_items q
        JOIN venues v ON v.id = q.venue_id
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participants p ON p.id = q.participant_id
        LEFT JOIN scores s ON s.queue_item_id = q.id
        GROUP BY q.id
        ORDER BY e.id, total DESC
    """)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["queue_item_id", "venue", "event_code", "event", "school",
                "student_name", "roll", "judges", "total", "average"])
    for r in rows:
        w.writerow([r["queue_item_id"], r["venue"], r["event_code"], r["event"],
                    r["school"] or "", r["student_name"] or "", r["roll"] or "",
                    r["judges"], round(r["total"], 2),
                    round(r["average"], 2) if r["average"] is not None else ""])
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"},
    )
