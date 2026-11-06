"""Shared FastAPI dependencies: session resolution, roles, step-up."""
from __future__ import annotations

import json

from fastapi import Depends, HTTPException, Request, status

from .security import totp_verify

SESSION_COOKIE = "kal_sid"
CSRF_COOKIE = "kal_csrf"


def get_db(request: Request):
    return request.app.state.db


def get_cfg(request: Request):
    return request.app.state.cfg


def current_user(request: Request) -> dict:
    db = get_db(request)
    sid = request.cookies.get(SESSION_COOKIE, "")
    if not sid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no_session")
    row = db.one(
        "SELECT s.sid, s.expires_at, s.last_seen, s.revoked, "
        " u.id AS uid, u.username, u.role, u.totp_secret, u.totp_required, "
        " u.stages, u.disabled "
        "FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.sid = ? AND s.revoked = 0",
        (sid,),
    )
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_session")
    now = db.now()
    if row["expires_at"] < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session_expired")
    cfg = get_cfg(request)
    if now - row["last_seen"] > cfg.idle_lock_min * 60:
        db.ex("UPDATE sessions SET revoked = 1 WHERE sid = ?", (sid,))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "idle_locked")
    if row["disabled"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user_disabled")
    if now - row["last_seen"] > 60:
        db.ex("UPDATE sessions SET last_seen = ? WHERE sid = ?", (now, sid))
    return {
        "sid": sid,
        "id": row["uid"],
        "username": row["username"],
        "role": row["role"],
        "stages": json.loads(row["stages"]),
        "totp_secret": row["totp_secret"],
        "totp_required": bool(row["totp_required"]),
    }


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_only")
    return user


def require_staff(user: dict = Depends(current_user)) -> dict:
    if user["role"] not in ("stagemaster", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    return user


def check_stage(user: dict, venue_id: int) -> None:
    if user["role"] == "admin":
        return
    if venue_id not in user["stages"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "stage_not_assigned")


def check_step_up(request: Request, user: dict) -> None:
    secret = user.get("totp_secret")
    if not secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "totp_required")
    code = request.headers.get("x-step-up-totp", "")
    if not code or not totp_verify(bytes(secret), code):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "stepup_failed")


def client_ip(request: Request) -> str:
    cf = request.headers.get("cf-connecting-ip", "")
    if cf:
        return cf.split(",")[0].strip()
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
