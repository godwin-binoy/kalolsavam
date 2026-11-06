"""Public read-only endpoints. Cacheable, rate-limit friendly."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/status")
async def status(request: Request):
    db = request.app.state.db
    venues = db.q("SELECT id, name, kind, active FROM venues WHERE active = 1 ORDER BY id")
    out = []
    for v in venues:
        state = db.one("SELECT state, announcement FROM live_state WHERE venue_id = ?", (v["id"],))
        cur = db.one(
            "SELECT q.id, q.status, e.title AS event, p.school, p.student_name "
            "FROM queue_items q JOIN events e ON e.id = q.event_id "
            "LEFT JOIN participants p ON p.id = q.participant_id "
            "WHERE q.venue_id = ? AND q.status IN ('ON-STAGE','PAUSED') "
            "ORDER BY q.position LIMIT 1",
            (v["id"],),
        )
        nxt = db.one(
            "SELECT e.title AS event, p.school, p.student_name "
            "FROM queue_items q JOIN events e ON e.id = q.event_id "
            "LEFT JOIN participants p ON p.id = q.participant_id "
            "WHERE q.venue_id = ? AND q.status = 'WAITING' "
            "ORDER BY q.position LIMIT 1",
            (v["id"],),
        )
        done = db.one(
            "SELECT COUNT(*) c FROM queue_items WHERE venue_id = ? AND status = 'COMPLETE'",
            (v["id"],))["c"]
        total = db.one(
            "SELECT COUNT(*) c FROM queue_items WHERE venue_id = ?", (v["id"],))["c"]
        out.append({
            "id": v["id"], "name": v["name"], "kind": v["kind"],
            "state": (state["state"] if state else "IDLE"),
            "announcement": (state["announcement"] if state else ""),
            "now": dict(cur) if cur else None,
            "next": dict(nxt) if nxt else None,
            "progress": {"complete": done, "total": total},
        })
    return JSONResponse(
        {"updated_at": db.now(), "venues": out},
        headers={"Cache-Control": "public, max-age=5, must-revalidate"},
    )


@router.get("/schedule")
async def schedule(request: Request, day: str | None = None):
    db = request.app.state.db
    q = ("SELECT e.id, e.code, e.title, c.name AS category, v.name AS venue, "
         " e.day, e.scheduled_time FROM events e "
         "LEFT JOIN categories c ON c.id = e.category_id "
         "LEFT JOIN venues v ON v.id = e.venue_id")
    params: tuple = ()
    if day:
        q += " WHERE e.day = ?"
        params = (day[:32],)
    rows = db.q(q + " ORDER BY e.day, e.scheduled_time LIMIT 1000", params)
    return JSONResponse(
        {"events": [dict(r) for r in rows]},
        headers={"Cache-Control": "public, max-age=60"},
    )


@router.get("/meta")
async def meta(request: Request):
    cfg = request.app.state.cfg
    db = request.app.state.db
    row = db.one("SELECT v FROM settings WHERE k = 'results_url'")
    url = row["v"] if row else cfg.results_url
    return JSONResponse(
        {"results_url": url},
        headers={"Cache-Control": "public, max-age=300"},
    )
