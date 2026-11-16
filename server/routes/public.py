"""Public read-only endpoints with short write-invalidated memory caching."""
from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

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
        rows = db.q("""
            SELECT v.id, v.name, v.kind, v.slug, v.active,
                   ls.state, ls.current_item, ls.current_chest, ls.upcoming_chests, ls.announcement
            FROM venues v
            LEFT JOIN live_state ls ON ls.venue_id = v.id
            ORDER BY v.id
        """)
        out = []
        for v in rows:
            is_active = bool(v["active"])
            if not is_active:
                state_str = "INACTIVE"
                now_obj = None
                upcoming: list[dict[str, str]] = []
            else:
                state_str = v["state"] or "IDLE"
                now_obj = (
                    {"event": v["current_item"] or "", "roll": v["current_chest"] or "", "chest_no": v["current_chest"]}
                    if (v["current_item"] or v["current_chest"])
                    else None
                )
                upcoming = (
                    [{"roll": t} for t in re.split(r"[\s,;]+", v["upcoming_chests"].strip()) if t][:8]
                    if v["upcoming_chests"]
                    else []
                )
            out.append({
                "id": v["id"],
                "name": v["name"],
                "kind": v["kind"],
                "slug": v["slug"],
                "active": is_active,
                "state": state_str,
                "announcement": v["announcement"] or "",
                "now": now_obj,
                "next": upcoming[0] if upcoming else None,
                "upcoming": upcoming,
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
        return {"venues": [dict(r) for r in db.q("SELECT id, name, kind, slug FROM venues WHERE active = 1 ORDER BY id")]}

    return JSONResponse(_cached(request, "venues", 10.0, build), headers={"Cache-Control": "public, max-age=60"})


@router.get("/schedule")
def schedule(request: Request, day: str | None = None, venue_id: int | None = None):
    db = request.app.state.db
    clean_day = day[:32] if day else None
    key = f"schedule:{clean_day or ''}:{venue_id if venue_id is not None else ''}"

    def build() -> dict[str, Any]:
        q = (
            "SELECT e.id, e.code, e.title, e.category, v.name AS venue, "
            "v.slug AS venue_slug, e.day, e.scheduled_time "
            "FROM events e LEFT JOIN venues v ON v.id = e.venue_id"
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
            q += " WHERE " + " AND ".join(clauses)  # noqa: S608
        return {"events": [dict(r) for r in db.q(q + " ORDER BY e.day, e.scheduled_time LIMIT 1000", tuple(params))]}

    return JSONResponse(_cached(request, key, 10.0, build), headers={"Cache-Control": "public, max-age=60"})


@router.get("/dashboard")
def dashboard_stats(request: Request):
    db = request.app.state.db

    def build() -> dict[str, Any]:
        row = db.one("""
            SELECT
                (SELECT COUNT(*) FROM venues) AS venues,
                (SELECT COUNT(*) FROM venues WHERE active = 1) AS active_venues,
                (SELECT COUNT(*) FROM venues v LEFT JOIN live_state ls ON ls.venue_id = v.id
                 WHERE v.active = 1 AND ls.state = 'RUNNING') AS running_venues,
                (SELECT COUNT(*) FROM events) AS events,
                (SELECT COUNT(*) FROM participants WHERE deleted_at IS NULL) AS participants,
                (SELECT COUNT(*) FROM participant_entries WHERE deleted_at IS NULL) AS entries,
                (SELECT COUNT(*) FROM photo_assets a JOIN photo_batches b ON b.id = a.batch_id
                 WHERE a.kind = 'stage' AND b.status = 'published') AS photos_published
        """)
        per_venue = [
            dict(r) for r in db.q("""
                SELECT v.id, v.name, v.kind, v.active,
                       COALESCE(ls.state, 'IDLE') AS state,
                       ls.current_item, ls.current_chest, ls.announcement
                FROM venues v
                LEFT JOIN live_state ls ON ls.venue_id = v.id
                ORDER BY v.id
            """)
        ]
        return {"updated_at": db.now(), "overall": dict(row), "per_venue": per_venue}

    return JSONResponse(_cached(request, "dashboard", 5.0, build), headers={"Cache-Control": "public, max-age=5"})
