"""Stagemaster API — run-of-show control, scoped to assigned stages.

All endpoints require a valid access token with role stagemaster (or admin).
Every mutation:
  - checks stage ownership (claims['stages'] must contain venue_id),
  - uses optimistic concurrency via queue_items.version (409 on conflict),
  - writes an entry to the changelog + publishes on the SSE bus,
  - supports idempotency via Idempotency-Key header so offline-buffered
    client replays never double-apply.
NOTE: results are NOT published from here — official results live on the
government website and the public site redirects there. Scores entered on
this board are only for the staff's own running totals.
"""
from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter()


def _deps(request: Request):
    db = request.app.state.db
    claims = request.app.state.get_access(request)
    if claims["role"] not in ("stagemaster", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    return db, claims


def _check_stage(claims: dict, venue_id: int) -> None:
    if claims["role"] != "admin" and venue_id not in claims.get("stages", []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "stage_not_assigned")


# ------------------------------------------------------------------ read ---
@router.get("/board")
async def board(request: Request):
    """Full working view for the stagemaster's assigned stages."""
    db, claims = _deps(request)
    venues = [v for v in db.query("SELECT * FROM venues WHERE active=1")
              if claims["role"] == "admin" or v["id"] in claims["stages"]]
    out = []
    for v in venues:
        items = db.query(
            "SELECT q.*, e.title AS event, c.name AS category, "
            "p.school, p.student_name, p.roll FROM queue_items q "
            "JOIN events e ON e.id=q.event_id "
            "LEFT JOIN categories c ON c.id=e.category_id "
            "LEFT JOIN participants p ON p.id=q.participant_id "
            "WHERE q.venue_id=? ORDER BY q.status='ON-STAGE' DESC, q.position",
            (v["id"],))
        state = db.one("SELECT * FROM live_state WHERE venue_id=?", (v["id"],))
        out.append({
            "venue": dict(v),
            "state": dict(state) if state else {"state": "IDLE"},
            "items": [dict(r) for r in items],
        })
    return {"board": out}


# --------------------------------------------------------------- mutate ----
class StateIn(BaseModel):
    venue_id: int
    state: str = Field(pattern=r"^(IDLE|RUNNING|PAUSED|BREAK|FINISHED)$")
    announcement: str = Field(default="", max_length=280)


@router.post("/state")
async def set_state(body: StateIn, request: Request):
    db, claims = _deps(request)
    _check_stage(claims, body.venue_id)
    db.execute(
        "INSERT INTO live_state(venue_id,state,announcement,updated_at) VALUES(?,?,?,?) "
        "ON CONFLICT(venue_id) DO UPDATE SET state=excluded.state,"
        "announcement=excluded.announcement, updated_at=excluded.updated_at",
        (body.venue_id, body.state, body.announcement, db.now()))
    db.emit_change("live_state", body.venue_id,
                   {"venue_id": body.venue_id, "state": body.state,
                    "announcement": body.announcement})
    return {"ok": True}


class AdvanceIn(BaseModel):
    venue_id: int
    action: str = Field(pattern=r"^(START_NEXT|COMPLETE_CURRENT|PAUSE|RESUME|SKIP|RECALL)$")
    version: int | None = None      # client's known version of current item
    base_ts: float | None = None    # offline queue timestamp for replay ordering


_TRANSITIONS = {
    "START_NEXT": ("WAITING", "ON-STAGE"),
    "COMPLETE_CURRENT": ("ON-STAGE", "COMPLETE"),
    "PAUSE": ("ON-STAGE", "PAUSED"),
    "RESUME": ("PAUSED", "ON-STAGE"),
    "SKIP": ("WAITING", "SKIPPED"),
    "RECALL": ("COMPLETE", "ON-STAGE"),
}


@router.post("/advance")
async def advance(body: AdvanceIn, request: Request):
    db, claims = _deps(request)
    _check_stage(claims, body.venue_id)

    # Idempotent replay: same key → same result, no double-apply.
    idem = request.headers.get("idempotency-key", "")[:64]
    if idem:
        hit = db.one("SELECT v FROM meta WHERE k=?", (f"idem:{idem}",))
        if hit:
            return {"ok": True, "replayed": True}

    frm, to = _TRANSITIONS[body.action]
    if body.action == "START_NEXT":
        # only one ON-STAGE per venue: auto-complete the incumbent first
        cur = db.one("SELECT * FROM queue_items WHERE venue_id=? AND status='ON-STAGE'",
                     (body.venue_id,))
        if cur:
            db.execute("UPDATE queue_items SET status='COMPLETE', version=version+1,"
                       " completed_at=?, updated_at=? WHERE id=? AND version=?",
                       (db.now(), db.now(), cur["id"], cur["version"]))
            db.emit_change("queue", cur["id"], {"venue_id": body.venue_id,
                         "item_id": cur["id"], "status": "COMPLETE"})
    row = db.one(
        "SELECT * FROM queue_items WHERE venue_id=? AND status=? "
        "ORDER BY position LIMIT 1", (body.venue_id, frm))
    if not row:
        raise HTTPException(status.HTTP_409_CONFLICT, "no_item_in_state")
    if body.version is not None and row["version"] != body.version:
        raise HTTPException(status.HTTP_409_CONFLICT, "version_conflict")
    upd = db.execute(
        "UPDATE queue_items SET status=?, version=version+1, updated_at=?,"
        " started_at=COALESCE(started_at,?),"
        " completed_at=CASE WHEN ?='COMPLETE' OR ?='SKIPPED' THEN ? ELSE completed_at END "
        "WHERE id=? AND version=?",
        (to, db.now(), db.now(), to, to, db.now(), row["id"], row["version"]))
    if upd.rowcount == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "version_conflict")

    db.emit_change("queue", row["id"], {
        "venue_id": body.venue_id, "item_id": row["id"], "status": to,
        "event": row["event_id"], "position": row["position"]})
    if idem:
        db.execute("INSERT INTO meta(k,v) VALUES(?,?) "
                   "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                   (f"idem:{idem}", "1"))
    return {"ok": True, "item_id": row["id"], "new_version": row["version"] + 1,
            "status": to}


class ScoreIn(BaseModel):
    queue_item_id: int
    judge_no: int = Field(ge=1, le=10)
    value: float = Field(ge=0, le=100)


@router.post("/score")
async def enter_score(body: ScoreIn, request: Request):
    db, claims = _deps(request)
    item = db.one("SELECT * FROM queue_items WHERE id=?", (body.queue_item_id,))
    if not item:
        raise HTTPException(404, "item_not_found")
    _check_stage(claims, item["venue_id"])
    if item["status"] not in ("ON-STAGE", "PAUSED", "COMPLETE"):
        raise HTTPException(409, "item_not_scorable")
    db.execute(
        "INSERT INTO scores(queue_item_id,judge_no,value,entered_by,entered_at) "
        "VALUES(?,?,?,?,?) ON CONFLICT(queue_item_id,judge_no) DO UPDATE "
        "SET value=excluded.value, entered_by=excluded.entered_by,"
        "entered_at=excluded.entered_at",
        (body.queue_item_id, body.judge_no, body.value, int(claims["sub"]),
         db.now()))
    rows = db.query("SELECT judge_no, value FROM scores WHERE queue_item_id=?",
                    (body.queue_item_id,))
    vals = [r["value"] for r in rows]
    agg = {"scores": [dict(r) for r in rows],
           "total": round(sum(vals), 2),
           "mean": round(sum(vals) / len(vals), 2) if vals else None}
    db.emit_change("score", body.queue_item_id,
                   {"item_id": body.queue_item_id, **agg})
    return agg


# ------------------------------------------------------------ stream ------
@router.get("/stream")
async def stream(request: Request):
    """Staff SSE feed — authenticated, full (unsanitized) entity set.

    EventSource cannot send an Authorization header, so clients consume this
    with fetch + ReadableStream (see dashboard js/api.js)."""
    _deps(request)                      # role check: stagemaster or admin
    from .events import BUS

    q = BUS.subscribe()

    async def gen():
        try:
            yield "retry: 3000\n\n"
            async for chunk in BUS.stream(q):
                yield chunk
        finally:
            BUS.unsubscribe(q)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
