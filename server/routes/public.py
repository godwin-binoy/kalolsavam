"""Public read-only endpoints with short write-invalidated memory caching."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()
_CACHE_LOCK = threading.Lock()


def invalidate_public_cache(app) -> None:
    cache = getattr(app.state, "public_cache", None)
    if cache is not None:
        with _CACHE_LOCK:
            cache.clear()


def _cached(request: Request, key: str, ttl: float, builder: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    cache = getattr(request.app.state, "public_cache", None)
    if cache is None:
        cache = {}
        request.app.state.public_cache = cache

    now = time.monotonic()
    with _CACHE_LOCK:
        hit = cache.get(key)
        if hit and (now - hit[0]) < ttl:
            return hit[1]

    payload = builder()
    with _CACHE_LOCK:
        cache[key] = (time.monotonic(), payload)
    return payload


@router.get("/status")
def status(request: Request):
    db = request.app.state.db

    def build() -> dict[str, Any]:
        venues_rows = db.q("""
            SELECT v.id, v.name, v.kind, v.slug, ls.state, ls.announcement,
                   COUNT(q.id) AS total,
                   SUM(CASE WHEN q.status = 'COMPLETE' THEN 1 ELSE 0 END) AS complete
            FROM venues v
            LEFT JOIN live_state ls ON ls.venue_id = v.id
            LEFT JOIN queue_items q ON q.venue_id = v.id
            WHERE v.active = 1
            GROUP BY v.id
            ORDER BY v.id
        """)

        items = db.q("""
            WITH ranked_waiting AS (
                SELECT q.id, q.venue_id, q.status, q.position,
                       e.title AS event, p.school, p.student_name, p.roll,
                       ROW_NUMBER() OVER (PARTITION BY q.venue_id ORDER BY q.position) AS rn
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

        by_venue: dict[int, list[dict[str, Any]]] = {}
        for i in items:
            by_venue.setdefault(i["venue_id"], []).append(dict(i))

        out = []
        for v in venues_rows:
            vitems = by_venue.get(v["id"], [])
            cur = next((x for x in vitems if x["status"] in ("ON-STAGE", "PAUSED")), None)
            waiting = [x for x in vitems if x["status"] == "WAITING"]
            out.append({
                "id": v["id"],
                "name": v["name"],
                "kind": v["kind"],
                "slug": v["slug"],
                "state": v["state"] or "IDLE",
                "announcement": v["announcement"] or "",
                "now": cur,
                "next": waiting[0] if waiting else None,
                "upcoming": waiting[:5],
                "progress": {"complete": v["complete"] or 0, "total": v["total"] or 0},
            })
        return {"updated_at": db.now(), "venues": out}

    return JSONResponse(
        _cached(request, "status", 2.0, build),
        headers={"Cache-Control": "public, max-age=4, must-revalidate"},
    )


@router.get("/venues")
def venues(request: Request):
    db = request.app.state.db

    def build() -> dict[str, Any]:
        rows = db.q("SELECT id, name, kind, slug FROM venues WHERE active = 1 ORDER BY id")
        return {"venues": [dict(r) for r in rows]}

    return JSONResponse(
        _cached(request, "venues", 10.0, build),
        headers={"Cache-Control": "public, max-age=60"},
    )


@router.get("/schedule")
def schedule(request: Request, day: str | None = None, venue_id: int | None = None):
    db = request.app.state.db
    clean_day = day[:32] if day else None
    key = f"schedule:{clean_day or ''}:{venue_id if venue_id is not None else ''}"

    def build() -> dict[str, Any]:
        q = (
            "SELECT e.id, e.code, e.title, c.name AS category, v.name AS venue, "
            " v.slug AS venue_slug, e.day, e.scheduled_time FROM events e "
            "LEFT JOIN categories c ON c.id = e.category_id "
            "LEFT JOIN venues v ON v.id = e.venue_id"
        )
        clauses: list[str] = []
        params: list[Any] = []
        if clean_day:
            clauses.append("e.day = ?")
            params.append(clean_day)
        if venue_id is not None:
            clauses.append("e.venue_id = ?")
            params.append(venue_id)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        rows = db.q(q + " ORDER BY e.day, e.scheduled_time LIMIT 1000", tuple(params))
        return {"events": [dict(r) for r in rows]}

    return JSONResponse(
        _cached(request, key, 10.0, build),
        headers={"Cache-Control": "public, max-age=60"},
    )
