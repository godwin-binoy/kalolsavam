"""Public, unauthenticated read-only endpoints consumed by the festival website.

Hard rules (docs/SECURITY.md):
 - Only display-safe, sanitized data leaves this router. RESULTS ARE NOT
   HOSTED HERE at all — we redirect to the government site instead, so this
   API exposes live progress but never rankings or scores.
 - No user/session data, no error internals, short public caching only.
 - SSE stream carries only display-safe deltas (stage state, running order).
"""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

router = APIRouter()


def _db(request: Request):
    return request.app.state.db


@router.get("/status")
async def status(request: Request):
    """One compact snapshot for the whole site — poll/SSE-resync target."""
    db = _db(request)
    venues = db.query(
        "SELECT v.id, v.name, v.kind, COALESCE(l.state,'IDLE') AS state, "
        "COALESCE(l.announcement,'') AS announcement "
        "FROM venues v LEFT JOIN live_state l ON l.venue_id=v.id WHERE v.active=1"
    )
    out_v = []
    for v in venues:
        cur = db.one(
            "SELECT q.id, q.status, e.title AS event, p.school, p.student_name, "
            "p.roll, q.version FROM queue_items q "
            "JOIN events e ON e.id=q.event_id "
            "LEFT JOIN participants p ON p.id=q.participant_id "
            "WHERE q.venue_id=? AND q.status IN ('ON-STAGE','PAUSED') "
            "ORDER BY q.position LIMIT 1", (v["id"],))
        nxt = db.one(
            "SELECT e.title AS event, p.school, p.student_name FROM queue_items q "
            "JOIN events e ON e.id=q.event_id "
            "LEFT JOIN participants p ON p.id=q.participant_id "
            "WHERE q.venue_id=? AND q.status='WAITING' ORDER BY q.position LIMIT 1",
            (v["id"],))
        done = db.scalar(
            "SELECT COUNT(*) FROM queue_items WHERE venue_id=? AND status='COMPLETE'",
            (v["id"],)) or 0
        total = db.scalar(
            "SELECT COUNT(*) FROM queue_items WHERE venue_id=?", (v["id"],)) or 0
        out_v.append({
            "id": v["id"], "name": v["name"], "kind": v["kind"],
            "state": v["state"], "announcement": v["announcement"],
            "now": dict(cur) if cur else None,
            "next": dict(nxt) if nxt else None,
            "progress": {"complete": done, "total": total},
        })
    flags = {r["key"]: r["value"] for r in db.query("SELECT * FROM feature_flags")}
    return JSONResponse(
        {"updated_at": db.now(), "venues": out_v, "flags": flags},
        headers={"Cache-Control": "public, max-age=5, must-revalidate"})


@router.get("/meta")
async def meta(request: Request):
    """Small config bundle for the public site (no secrets, cacheable).

    `results_url` is where ALL "Results" links on the website point — the
    official government portal. We deliberately do not host results."""
    cfg = request.app.state.cfg
    return JSONResponse({"results_url": cfg.results_url},
                        headers={"Cache-Control": "public, max-age=300"})


@router.get("/schedule")
async def schedule(request: Request, day: str | None = None):
    db = _db(request)
    q = ("SELECT e.id, e.code, e.title, c.name AS category, c.grp AS grp, "
         "v.name AS venue, e.day, e.scheduled_time FROM events e "
         "LEFT JOIN categories c ON c.id=e.category_id "
         "LEFT JOIN venues v ON v.id=e.venue_id")
    params: tuple = ()
    if day:
        q += " WHERE e.day=?"
        params = (day[:32],)
    rows = db.query(q + " ORDER BY e.day, e.scheduled_time LIMIT 1000", params)
    return JSONResponse({"events": [dict(r) for r in rows]},
                        headers={"Cache-Control": "public, max-age=60"})


@router.get("/stream")
async def stream(request: Request):
    """SSE fan-out of display-safe changes. Anonymous; contains no secrets."""
    from .events import BUS

    safe_entities = {"live_state", "queue"}
    q = BUS.subscribe()

    async def gen():
        try:
            yield "retry: 3000\n\n"
            async for chunk in BUS.stream(q):
                # filter: only entities the public site may see
                try:
                    payload = json.loads(chunk.split("data: ", 1)[1].strip())
                    if payload.get("entity") not in safe_entities:
                        continue
                except (IndexError, json.JSONDecodeError):
                    pass  # keep-alives etc. pass through
                yield chunk
        finally:
            BUS.unsubscribe(q)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
