"""Public read-only endpoints. Efficient, cacheable."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/status")
def status(request: Request):
    db = request.app.state.db

    venues = db.q("""
        SELECT v.id, v.name, v.kind, ls.state, ls.announcement,
               COUNT(q.id) AS total,
               SUM(CASE WHEN q.status = 'COMPLETE' THEN 1 ELSE 0 END) AS complete
        FROM venues v
        LEFT JOIN live_state ls ON ls.venue_id = v.id
        LEFT JOIN queue_items q ON q.venue_id = v.id
        WHERE v.active = 1
        GROUP BY v.id
        ORDER BY v.id
    """)

    # Query only active items and top 5 waiting items per venue
    items = db.q("""
        WITH ranked_waiting AS (
            SELECT q.id, q.venue_id, q.status, q.position,
                   e.title AS event, p.school, p.student_name, p.roll,
                   ROW_NUMBER() OVER (PARTITION BY q.venue_id ORDER BY q.position) as rn
            FROM queue_items q
            JOIN events e ON e.id = q.event_id
            LEFT JOIN participants p ON p.id = q.participant_id
            WHERE q.status = 'WAITING'
        )
        SELECT q.id, q.venue_id, q.status, q.position,
               e.title AS event, p.school, p.student_name, p.roll
        FROM queue_items q
        JOIN events e ON e.id = q.event_id
        LEFT JOIN participants p ON p.id = q.participant_id
        WHERE q.status IN ('ON-STAGE', 'PAUSED')
        UNION ALL
        SELECT id, venue_id, status, position, event, school, student_name, roll
        FROM ranked_waiting
        WHERE rn <= 5
        ORDER BY venue_id, position
    """)

    by_venue = {}
    for i in items:
        by_venue.setdefault(i["venue_id"], []).append(dict(i))

    out = []
    for v in venues:
        vitems = by_venue.get(v["id"], [])
        cur = next((x for x in vitems if x["status"] in ('ON-STAGE', 'PAUSED')), None)
        waiting = [x for x in vitems if x["status"] == 'WAITING']
        out.append({
            "id": v["id"],
            "name": v["name"],
            "kind": v["kind"],
            "state": v["state"] or "IDLE",
            "announcement": v["announcement"] or "",
            "now": cur,
            "next": waiting[0] if waiting else None,
            "upcoming": waiting[:5],
            "progress": {"complete": v["complete"] or 0, "total": v["total"] or 0},
        })

    return JSONResponse(
        {"updated_at": db.now(), "venues": out},
        headers={"Cache-Control": "public, max-age=4, must-revalidate"},
    )


@router.get("/venues")
def venues(request: Request):
    """Active venues list. The live tracker maps stage card names to
    backend venue IDs via this endpoint; /status then supplies the live
    state for each venue."""
    db = request.app.state.db
    rows = db.q("SELECT id, name, kind FROM venues WHERE active = 1 ORDER BY id")
    return JSONResponse(
        {"venues": [dict(r) for r in rows]},
        headers={"Cache-Control": "public, max-age=60"},
    )


@router.get("/schedule")
def schedule(request: Request, day: str | None = None, venue_id: int | None = None):
    db = request.app.state.db
    q = ("SELECT e.id, e.code, e.title, c.name AS category, v.name AS venue, "
         " e.day, e.scheduled_time FROM events e "
         "LEFT JOIN categories c ON c.id = e.category_id "
         "LEFT JOIN venues v ON v.id = e.venue_id")
    clauses: list[str] = []
    params: list = []
    if day:
        clauses.append("e.day = ?")
        params.append(day[:32])
    if venue_id is not None:
        clauses.append("e.venue_id = ?")
        params.append(venue_id)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    rows = db.q(q + " ORDER BY e.day, e.scheduled_time LIMIT 1000", tuple(params))
    return JSONResponse(
        {"events": [dict(r) for r in rows]},
        headers={"Cache-Control": "public, max-age=60"},
    )
