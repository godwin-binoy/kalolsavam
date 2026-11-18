"""Stagemaster direct stage control and SSE broadcast."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..auth import (
    check_stage,
    get_db,
    get_user_stages,
    has_role,
    require_photo_staff,
    require_staff,
)
from .public import invalidate_public_cache

router = APIRouter()
log = logging.getLogger("kalolsavam")
_MAX_SSE_SUBSCRIBERS = 200


class StateIn(BaseModel):
    venue_id: int
    active: bool | None = None
    state: str = Field(pattern=r"^(IDLE|RUNNING|PAUSED|BREAK|FINISHED)$")
    current_item: str | None = Field(default=None, max_length=200)
    current_chest: str | None = Field(default=None, max_length=32)
    upcoming_chests: str | None = Field(default=None, max_length=280)
    announcement: str = Field(default="", max_length=280)


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
    except Exception as exc:
        log.debug("SSE broadcast failed: %s", exc)


def _clean_opt(val: str | None) -> str | None:
    if val is None:
        return None
    s = val.strip()
    return s or None


@router.get("/board")
def board(request: Request, user=Depends(require_staff)):
    db = get_db(request)
    all_venues = db.q("SELECT * FROM venues ORDER BY id")
    if has_role(user, "admin"):
        venues = all_venues
    else:
        allowed = set(get_user_stages(user))
        venues = [v for v in all_venues if v["id"] in allowed]

    states = {s["venue_id"]: dict(s) for s in db.q("SELECT * FROM live_state")}
    default_state = {"state": "IDLE", "current_item": None, "current_chest": None, "upcoming_chests": None, "announcement": ""}
    return {
        "board": [
            {"venue": dict(v), "state": states.get(v["id"], default_state)}
            for v in venues
        ]
    }


@router.get("/stream")
async def stream(request: Request, user=Depends(require_photo_staff)):
    if len(request.app.state.subscribers) >= _MAX_SSE_SUBSCRIBERS:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "too_many_streams")

    async def gen():
        q: asyncio.Queue = asyncio.Queue(maxsize=128)
        venues = None if has_role(user, "admin", "dataworker") else set(get_user_stages(user))
        request.app.state.subscribers[q] = venues
        try:
            yield "retry: 3000\nevent: hello\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: update\ndata: {json.dumps(msg)}\n\n"
                except TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            request.app.state.subscribers.pop(q, None)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.post("/state")
def set_state(body: StateIn, request: Request, user=Depends(require_staff)):
    check_stage(user, body.venue_id)
    db = get_db(request)
    if not db.one("SELECT id FROM venues WHERE id = ?", (body.venue_id,)):
        raise HTTPException(404, "venue_not_found")
    with db.transaction():
        if body.active is not None:
            db.ex("UPDATE venues SET active = ? WHERE id = ?", (int(body.active), body.venue_id))
        db.ex(
            "INSERT INTO live_state(venue_id, state, current_item, current_chest, upcoming_chests, announcement, updated_at) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT(venue_id) DO UPDATE SET "
            "state = excluded.state, current_item = excluded.current_item, "
            "current_chest = excluded.current_chest, upcoming_chests = excluded.upcoming_chests, "
            "announcement = excluded.announcement, updated_at = excluded.updated_at",
            (
                body.venue_id,
                body.state,
                _clean_opt(body.current_item),
                _clean_opt(body.current_chest),
                _clean_opt(body.upcoming_chests),
                (body.announcement or "").strip(),
                db.now(),
            ),
        )
    invalidate_public_cache(request.app)
    _broadcast_sync(request, {"entity": "state", "venue_id": body.venue_id})
    return {"ok": True}
