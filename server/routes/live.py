"""Stagemaster run-of-show control. SSE via asyncio broadcast."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

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
    for q in list(request.app.state.subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


@router.get("/board")
async def board(request: Request, user: dict = Depends(require_staff)):
    db = get_db(request)
    if user["role"] == "admin":
        venues = db.q("SELECT * FROM venues WHERE active = 1 ORDER BY id")
    else:
        if not user["stages"]:
            return {"board": []}
        ph = ",".join("?" * len(user["stages"]))
        venues = db.q(
            "SELECT * FROM venues WHERE active = 1 AND id IN (" + ph + ") ORDER BY id",
            tuple(user["stages"]),
        )
    out = []
    for v in venues:
        items = db.q(
            "SELECT q.*, e.title AS event, c.name AS category, "
            " p.school, p.student_name, p.roll "
            "FROM queue_items q "
            "JOIN events e ON e.id = q.event_id "
            "LEFT JOIN categories c ON c.id = e.category_id "
            "LEFT JOIN participants p ON p.id = q.participant_id "
            "WHERE q.venue_id = ? "
            "ORDER BY CASE q.status WHEN 'ON-STAGE' THEN 0 ELSE 1 END, q.position",
            (v["id"],),
        )
        state = db.one("SELECT state, announcement FROM live_state WHERE venue_id = ?",
                       (v["id"],))
        out.append({
            "venue": dict(v),
            "state": dict(state) if state else {"state": "IDLE", "announcement": ""},
            "items": [dict(r) for r in items],
        })
    return {"board": out}


@router.get("/stream")
async def stream(request: Request, user: dict = Depends(require_staff)):
    async def gen():
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        request.app.state.subscribers.add(q)
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
            request.app.state.subscribers.discard(q)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/state")
async def set_state(body: StateIn, request: Request,
                    user: dict = Depends(require_staff)):
    check_stage(user, body.venue_id)
    db = get_db(request)
    db.ex(
        "INSERT INTO live_state(venue_id, state, announcement, updated_at) "
        "VALUES (?,?,?,?) ON CONFLICT(venue_id) DO UPDATE SET "
        " state = excluded.state, announcement = excluded.announcement, "
        " updated_at = excluded.updated_at",
        (body.venue_id, body.state, body.announcement, db.now()),
    )
    await _broadcast(request, {"entity": "state", "venue_id": body.venue_id})
    return {"ok": True}


@router.post("/advance")
async def advance(body: AdvanceIn, request: Request,
                  user: dict = Depends(require_staff)):
    check_stage(user, body.venue_id)
    db = get_db(request)

    idem = request.headers.get("idempotency-key", "")[:96]
    if not idem:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "idempotency_required")
    db.ex("DELETE FROM idempotency WHERE created_at < ?", (db.now() - 86400,))
    hit = db.one("SELECT * FROM idempotency WHERE key = ?", (idem,))
    if hit:
        return {**json.loads(hit["response"]), "replayed": True}

    frm, to = _TRANSITIONS[body.action]

    if body.action == "START_NEXT":
        cur = db.one(
            "SELECT * FROM queue_items WHERE venue_id = ? AND status = 'ON-STAGE'",
            (body.venue_id,),
        )
        if cur:
            db.ex(
                "UPDATE queue_items SET status = 'COMPLETE', "
                " version = version + 1, completed_at = ?, updated_at = ? "
                "WHERE id = ?",
                (db.now(), db.now(), cur["id"]),
            )

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
        " completed_at = CASE WHEN ? IN ('COMPLETE','SKIPPED') THEN ? "
        " ELSE completed_at END "
        "WHERE id = ? AND version = ?",
        (to, db.now(), db.now(), to, db.now(), row["id"], row["version"]),
    )
    if cur_db.rowcount == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "version_conflict")

    resp = {"ok": True, "item_id": row["id"], "status": to,
            "version": row["version"] + 1}
    db.ex(
        "INSERT INTO idempotency(key, response, created_at) VALUES (?,?,?)",
        (idem, json.dumps(resp), db.now()),
    )
    await _broadcast(request, {"entity": "queue", "venue_id": body.venue_id,
                               "item_id": row["id"], "status": to})
    return resp


@router.post("/score")
async def enter_score(body: ScoreIn, request: Request,
                      user: dict = Depends(require_staff)):
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
        (body.queue_item_id, body.judge_no, body.value, user["id"], db.now()),
    )
    rows = db.q("SELECT judge_no, value FROM scores WHERE queue_item_id = ?",
                (body.queue_item_id,))
    vals = [r["value"] for r in rows]
    return {
        "scores": [dict(r) for r in rows],
        "total": round(sum(vals), 2),
        "mean": round(sum(vals) / len(vals), 2) if vals else None,
    }
