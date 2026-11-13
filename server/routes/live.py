"""Stagemaster run-of-show control. SSE via asyncio broadcast."""
from __future__ import annotations

import asyncio
import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ..auth import get_user_stages, has_role
from ..deps import check_stage, get_db, require_staff
from ..models import AdvanceIn, ScoreIn, StateIn

router = APIRouter()

_TRANSITIONS = {
    "START_NEXT":       ("WAITING",   "ON-STAGE"),
    "COMPLETE_CURRENT": ("ON-STAGE",  "COMPLETE"),
    "PAUSE":            ("ON-STAGE",  "PAUSED"),
    "RESUME":           ("PAUSED",    "ON-STAGE"),
    "SKIP":             ("WAITING",   "SKIPPED"),
    "RECALL":           ("COMPLETE",  "ON-STAGE"),
}


async def _broadcast(request: Request, msg: dict) -> None:
    venue_id = msg.get("venue_id")
    for q, venues in list(request.app.state.subscribers.items()):
        if venues is not None and venue_id is not None and venue_id not in venues:
            continue
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


def _broadcast_sync(request: Request, msg: dict) -> None:
    loop = getattr(request.app.state, "loop", None)
    if loop is None or loop.is_closed():
        return
    try:
        asyncio.run_coroutine_threadsafe(_broadcast(request, msg), loop)
    except Exception:
        pass


def _active_venues_for_user(db, user):
    if has_role(user, "admin"):
        return db.q("SELECT * FROM venues WHERE active = 1 ORDER BY id")
    stages = get_user_stages(user)
    if not stages:
        return []
    ph = ",".join("?" * len(stages))
    return db.q(
        f"SELECT * FROM venues WHERE active = 1 AND id IN ({ph}) ORDER BY id",
        tuple(stages),
    )


@router.get("/board")
def board(request: Request, user=Depends(require_staff)):
    db = get_db(request)
    venues = _active_venues_for_user(db, user)
    if not venues:
        return {"board": []}

    vids = [v["id"] for v in venues]
    ph = ",".join("?" * len(vids))
    items = db.q(
        "SELECT q.*, e.title AS event, c.name AS category, "
        " p.school, p.student_name, p.roll "
        "FROM queue_items q "
        "JOIN events e ON e.id = q.event_id "
        "LEFT JOIN categories c ON c.id = e.category_id "
        "LEFT JOIN participants p ON p.id = q.participant_id "
        f"WHERE q.venue_id IN ({ph}) "
        "ORDER BY q.venue_id, "
        "CASE q.status WHEN 'ON-STAGE' THEN 0 ELSE 1 END, q.position",
        tuple(vids),
    )
    states = db.q(
        f"SELECT venue_id, state, announcement FROM live_state WHERE venue_id IN ({ph})",
        tuple(vids),
    )
    state_map = {s["venue_id"]: dict(s) for s in states}
    by_venue: dict[int, list[dict]] = {}
    for it in items:
        by_venue.setdefault(it["venue_id"], []).append(dict(it))

    return {
        "board": [
            {
                "venue": dict(v),
                "state": state_map.get(v["id"], {"state": "IDLE", "announcement": ""}),
                "items": by_venue.get(v["id"], []),
            }
            for v in venues
        ]
    }


@router.get("/stream")
async def stream(request: Request, user=Depends(require_staff)):
    async def gen():
        q: asyncio.Queue = asyncio.Queue(maxsize=128)
        venues = None if has_role(user, "admin") else set(get_user_stages(user))
        request.app.state.subscribers[q] = venues
        try:
            yield "retry: 3000\nevent: hello\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: update\ndata: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            request.app.state.subscribers.pop(q, None)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/state")
def set_state(body: StateIn, request: Request, user=Depends(require_staff)):
    check_stage(user, body.venue_id)
    db = get_db(request)
    db.ex(
        "INSERT INTO live_state(venue_id, state, announcement, updated_at) "
        "VALUES (?,?,?,?) ON CONFLICT(venue_id) DO UPDATE SET "
        " state = excluded.state, announcement = excluded.announcement, "
        " updated_at = excluded.updated_at",
        (body.venue_id, body.state, body.announcement, db.now()),
    )
    _broadcast_sync(request, {"entity": "state", "venue_id": body.venue_id})
    return {"ok": True}


@router.post("/advance")
def advance(body: AdvanceIn, request: Request, user=Depends(require_staff)):
    check_stage(user, body.venue_id)
    db = get_db(request)

    idem = request.headers.get("idempotency-key", "")[:96]
    if not idem:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "idempotency_required")

    hit = db.one("SELECT response FROM idempotency WHERE key = ?", (idem,))
    if hit:
        return {**json.loads(hit["response"]), "replayed": True}

    frm, to = _TRANSITIONS[body.action]
    broadcasts: list[dict] = []
    resp: dict | None = None

    try:
        with db.transaction():
            now = db.now()
            db.ex("DELETE FROM idempotency WHERE created_at < ?", (now - 86400,))

            hit = db.one("SELECT response FROM idempotency WHERE key = ?", (idem,))
            if hit:
                return {**json.loads(hit["response"]), "replayed": True}

            # Ensure any currently active item is cleanly completed (START_NEXT) or paused (RECALL)
            if body.action in ("START_NEXT", "RECALL"):
                cur = db.one(
                    "SELECT * FROM queue_items WHERE venue_id = ? "
                    "AND status IN ('ON-STAGE', 'PAUSED')",
                    (body.venue_id,),
                )
                if cur:
                    next_status = "COMPLETE" if body.action == "START_NEXT" else "PAUSED"
                    completed_val = now if next_status == "COMPLETE" else cur["completed_at"]
                    db.ex(
                        "UPDATE queue_items SET status = ?, "
                        " version = version + 1, completed_at = ?, updated_at = ? "
                        "WHERE id = ?",
                        (next_status, completed_val, now, cur["id"]),
                    )
                    broadcasts.append({
                        "entity": "queue", "venue_id": body.venue_id,
                        "item_id": cur["id"], "status": next_status,
                    })

            if body.action == "RECALL" and body.item_id is not None:
                row = db.one(
                    "SELECT * FROM queue_items WHERE id = ? AND venue_id = ? "
                    "AND status = 'COMPLETE'",
                    (body.item_id, body.venue_id),
                )
            else:
                row = db.one(
                    "SELECT * FROM queue_items WHERE venue_id = ? AND status = ? "
                    "ORDER BY position LIMIT 1",
                    (body.venue_id, frm),
                )
            if not row:
                raise HTTPException(status.HTTP_409_CONFLICT, "no_item_in_state")
            if body.version is not None and row["version"] != body.version:
                raise HTTPException(status.HTTP_409_CONFLICT, "version_conflict")

            cur_db = db.ex(
                "UPDATE queue_items SET status = ?, version = version + 1, "
                " updated_at = ?, started_at = COALESCE(started_at, ?), "
                " completed_at = CASE "
                "   WHEN ? IN ('COMPLETE','SKIPPED') THEN ? "
                "   WHEN ? IN ('ON-STAGE','PAUSED') THEN NULL "
                "   ELSE completed_at END "
                "WHERE id = ? AND version = ?",
                (to, now, now, to, now, to, row["id"], row["version"]),
            )
            if cur_db.rowcount == 0:
                raise HTTPException(status.HTTP_409_CONFLICT, "version_conflict")

            resp = {
                "ok": True,
                "item_id": row["id"],
                "status": to,
                "version": row["version"] + 1,
            }
            db.ex(
                "INSERT INTO idempotency(key, response, created_at) VALUES (?,?,?)",
                (idem, json.dumps(resp), now),
            )
            broadcasts.append({
                "entity": "queue", "venue_id": body.venue_id,
                "item_id": row["id"], "status": to,
            })
    except sqlite3.IntegrityError:
        hit = db.one("SELECT response FROM idempotency WHERE key = ?", (idem,))
        if hit:
            return {**json.loads(hit["response"]), "replayed": True}
        raise

    for msg in broadcasts:
        _broadcast_sync(request, msg)
    assert resp is not None
    return resp


@router.post("/score")
def enter_score(body: ScoreIn, request: Request, user=Depends(require_staff)):
    db = get_db(request)
    item = db.one("SELECT * FROM queue_items WHERE id = ?", (body.queue_item_id,))
    if not item:
        raise HTTPException(404, "item_not_found")
    check_stage(user, item["venue_id"])
    if item["status"] not in ("ON-STAGE", "PAUSED", "COMPLETE"):
        raise HTTPException(409, "item_not_scorable")
    db.ex(
        "INSERT INTO scores(queue_item_id, judge_no, value, entered_by, entered_at) "
        "VALUES (?,?,?,?,?) ON CONFLICT(queue_item_id, judge_no) DO UPDATE SET "
        " value = excluded.value, entered_by = excluded.entered_by, "
        " entered_at = excluded.entered_at",
        (body.queue_item_id, body.judge_no, body.value, str(user.id), db.now()),
    )
    rows = db.q(
        "SELECT judge_no, value FROM scores WHERE queue_item_id = ? ORDER BY judge_no",
        (body.queue_item_id,),
    )
    vals = [r["value"] for r in rows]
    _broadcast_sync(
        request,
        {"entity": "score", "venue_id": item["venue_id"], "queue_item_id": body.queue_item_id},
    )
    return {
        "scores": [dict(r) for r in rows],
        "total": round(sum(vals), 2),
        "mean": round(sum(vals) / len(vals), 2) if vals else None,
    }
