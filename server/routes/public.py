"""Public read-only endpoints with short write-invalidated memory caching."""
from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..deps import rate_limit

router = APIRouter()
_CACHE_LOCK = threading.Lock()


def invalidate_public_cache(app: Any) -> None:
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
            SELECT v.id, v.name, v.kind, v.slug, v.active,
                   ls.state, ls.current_item, ls.current_chest, ls.upcoming_chests, ls.announcement,
                   COUNT(q.id) AS total,
                   SUM(CASE WHEN q.status = 'COMPLETE' THEN 1 ELSE 0 END) AS complete
            FROM venues v
            LEFT JOIN live_state ls ON ls.venue_id = v.id
            LEFT JOIN queue_items q ON q.venue_id = v.id
            GROUP BY v.id
            ORDER BY v.id
        """)

        items = db.q("""
            WITH ranked_waiting AS (
                SELECT q.id, q.venue_id, q.status, q.position, q.chest_no,
                       e.title AS event, p.school_name AS school,
                       p.name AS student_name, COALESCE(q.chest_no, p.register_no) AS roll,
                       ROW_NUMBER() OVER (PARTITION BY q.venue_id ORDER BY q.position) AS rn
                FROM queue_items q
                JOIN events e ON e.id = q.event_id
                LEFT JOIN participant_entries pe ON pe.id = q.participant_entry_id
                LEFT JOIN participants p ON p.id = pe.participant_id AND p.deleted_at IS NULL
                WHERE q.status = 'WAITING'
            )
            SELECT q.id, q.venue_id, q.status, q.position, q.chest_no,
                   e.title AS event, p.school_name AS school,
                   p.name AS student_name, COALESCE(q.chest_no, p.register_no) AS roll
            FROM queue_items q
            JOIN events e ON e.id = q.event_id
            LEFT JOIN participant_entries pe ON pe.id = q.participant_entry_id
            LEFT JOIN participants p ON p.id = pe.participant_id AND p.deleted_at IS NULL
            WHERE q.status IN ('ON-STAGE', 'PAUSED')
            UNION ALL
            SELECT id, venue_id, status, position, chest_no, event, school, student_name, roll
            FROM ranked_waiting
            WHERE rn <= 5
            ORDER BY venue_id, position
        """)

        by_venue: dict[int, list[dict[str, Any]]] = {}
        for i in items:
            by_venue.setdefault(i["venue_id"], []).append(dict(i))

        out = []
        for v in venues_rows:
            is_active = bool(v["active"])
            vitems = by_venue.get(v["id"], [])
            cur = next((x for x in vitems if x["status"] in ("ON-STAGE", "PAUSED")), None)
            waiting = [x for x in vitems if x["status"] == "WAITING"]

            if not is_active:
                now_obj = None
                upcoming_list: list[dict[str, Any]] = []
                state_str = "INACTIVE"
            else:
                state_str = v["state"] or "IDLE"
                if v["current_item"] or v["current_chest"]:
                    now_obj = {
                        "event": v["current_item"] or "",
                        "roll": v["current_chest"] or "",
                        "chest_no": v["current_chest"],
                        "student_name": None,
                        "school": None,
                    }
                else:
                    now_obj = cur

                if v["upcoming_chests"]:
                    tokens = [t for t in re.split(r"[\s,;]+", v["upcoming_chests"].strip()) if t]
                    upcoming_list = [{"roll": t} for t in tokens[:8]]
                else:
                    upcoming_list = waiting[:5]

            out.append({
                "id": v["id"],
                "name": v["name"],
                "kind": v["kind"],
                "slug": v["slug"],
                "active": is_active,
                "state": state_str,
                "announcement": v["announcement"] or "",
                "now": now_obj,
                "next": upcoming_list[0] if upcoming_list else None,
                "upcoming": upcoming_list,
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


@router.get("/dashboard")
def dashboard_stats(request: Request):
    db = request.app.state.db

    def build() -> dict[str, Any]:
        row = db.one("""
            SELECT
                (SELECT COUNT(*) FROM venues) AS venues,
                (SELECT COUNT(*) FROM venues WHERE active = 1) AS active_venues,
                (SELECT COUNT(*) FROM events) AS events,
                (SELECT COUNT(*) FROM participants WHERE deleted_at IS NULL) AS participants,
                COUNT(q.id) AS queue_items,
                COALESCE(SUM(CASE WHEN q.status = 'WAITING' THEN 1 ELSE 0 END), 0) AS queue_waiting,
                COALESCE(SUM(CASE WHEN q.status IN ('ON-STAGE', 'PAUSED') THEN 1 ELSE 0 END), 0) AS queue_onstage,
                COALESCE(SUM(CASE WHEN q.status = 'COMPLETE' THEN 1 ELSE 0 END), 0) AS queue_complete,
                COALESCE(SUM(CASE WHEN q.status = 'SKIPPED' THEN 1 ELSE 0 END), 0) AS queue_skipped
            FROM queue_items q
        """)
        per_venue = [
            dict(r) for r in db.q("""
                SELECT v.id, v.name, v.kind, v.active,
                       COUNT(q.id) AS total,
                       COALESCE(SUM(CASE WHEN q.status='WAITING' THEN 1 ELSE 0 END), 0) AS waiting,
                       COALESCE(SUM(CASE WHEN q.status IN ('ON-STAGE','PAUSED') THEN 1 ELSE 0 END), 0) AS onstage,
                       COALESCE(SUM(CASE WHEN q.status='COMPLETE' THEN 1 ELSE 0 END), 0) AS complete,
                       COALESCE(SUM(CASE WHEN q.status='SKIPPED' THEN 1 ELSE 0 END), 0) AS skipped
                FROM venues v
                LEFT JOIN queue_items q ON q.venue_id = v.id
                GROUP BY v.id ORDER BY v.id
            """)
        ]
        recent_completed = [
            dict(r) for r in db.q("""
                SELECT q.id, q.completed_at, e.code AS event_code, e.title AS event_title,
                       v.name AS venue_name
                FROM queue_items q
                JOIN events e ON e.id = q.event_id
                JOIN venues v ON v.id = q.venue_id
                WHERE q.status='COMPLETE' AND q.completed_at IS NOT NULL
                ORDER BY q.completed_at DESC LIMIT 20
            """)
        ]
        return {
            "updated_at": db.now(),
            "overall": dict(row),
            "per_venue": per_venue,
            "recent_completed": recent_completed,
        }

    return JSONResponse(
        _cached(request, "dashboard", 10.0, build),
        headers={"Cache-Control": "public, max-age=10"},
    )


class LookupIn(BaseModel):
    register_no: str = Field(pattern=r"^\d{5}$")
    name: str = Field(min_length=1, max_length=200)


@router.post("/participant-lookup", dependencies=[Depends(rate_limit("lookup", 12, 60))])
def participant_lookup(body: LookupIn, request: Request):
    db = request.app.state.db
    p = db.one(
        "SELECT id, name FROM participants WHERE register_no = ? AND lower(name) = lower(?) AND deleted_at IS NULL",
        (body.register_no.strip(), body.name.strip()),
    )
    if not p:
        raise HTTPException(404, "not_found")
    entries = db.q(
        "SELECT id, item_code, venue_name, perf_date FROM participant_entries "
        "WHERE participant_id = ? AND deleted_at IS NULL ORDER BY perf_date, item_code",
        (p["id"],),
    )
    return {"valid": True, "participant": dict(p), "entries": [dict(e) for e in entries]}
