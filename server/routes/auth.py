"""Login, logout, TOTP enrollment, password change. Cookie sessions only."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from ..deps import (
    CSRF_COOKIE, SESSION_COOKIE, client_ip, current_user, get_cfg, get_db,
)
from ..models import LoginIn, PasswordIn, TotpSetupIn
from ..security import (
    hash_ip, hash_password, new_csrf_token, new_session_id,
    totp_provision, totp_uri, totp_verify, verify_password,
)

router = APIRouter()


def _set_session_cookies(resp: Response, cfg, sid: str, csrf: str, max_age: int) -> None:
    https = cfg.public_origin.startswith("https://")
    resp.set_cookie(
        SESSION_COOKIE, sid, max_age=max_age, httponly=True,
        secure=https, samesite="strict", path="/",
    )
    resp.set_cookie(
        CSRF_COOKIE, csrf, max_age=max_age, httponly=False,
        secure=https, samesite="strict", path="/",
    )


def _log(db, *, username, user_id, ip, event, detail=""):
    db.ex(
        "INSERT INTO auth_audit(ts, username, user_id, ip_hash, event, detail) "
        "VALUES (?,?,?,?,?,?)",
        (db.now(), username, user_id, hash_ip(ip), event, detail),
    )


@router.post("/login")
async def login(body: LoginIn, request: Request):
    db, cfg = get_db(request), get_cfg(request)
    ip = client_ip(request)
    user = db.one("SELECT * FROM users WHERE username = ? AND disabled = 0", (body.username,))
    if user and user["locked_until"] > db.now():
        retry = int(user["locked_until"] - db.now())
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            {"error": "account_locked", "retry_after": retry},
        )
    if not user or not verify_password(body.password, user["pwd_salt"], user["pwd_hash"]):
        if user:
            fails = user["failed_count"] + 1
            lock_secs = [0, 0, 60, 300, 900][min(fails, 4)]
            db.ex(
                "UPDATE users SET failed_count = ?, locked_until = ? WHERE id = ?",
                (fails, db.now() + lock_secs, user["id"]),
            )
            _log(db, username=user["username"], user_id=user["id"], ip=ip,
                 event="login_fail", detail=f"count={fails}")
        else:
            _log(db, username=body.username[:64], user_id=None, ip=ip,
                 event="login_fail", detail="unknown_user")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "auth_failed")

    if user["role"] == "admin":
        if not user["totp_secret"]:
            secret = totp_provision()
            db.ex("UPDATE users SET pending_totp_secret = ? WHERE id = ?",
                  (secret, user["id"]))
            _log(db, username=user["username"], user_id=user["id"], ip=ip,
                 event="totp_setup_needed")
            return JSONResponse(
                {"error": "totp_setup_required",
                 "uri": totp_uri(secret, user["username"])},
                status_code=200,
            )
        if not body.totp or not totp_verify(bytes(user["totp_secret"]), body.totp):
            _log(db, username=user["username"], user_id=user["id"], ip=ip,
                 event="totp_fail")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "totp_required")

    db.ex("UPDATE users SET failed_count = 0, locked_until = 0 WHERE id = ?", (user["id"],))
    _log(db, username=user["username"], user_id=user["id"], ip=ip, event="login_ok")

    sid = new_session_id()
    csrf = new_csrf_token()
    now = db.now()
    exp = now + cfg.session_ttl_min * 60
    db.ex(
        "INSERT INTO sessions(sid, user_id, ip_hash, created_at, last_seen, expires_at) "
        "VALUES (?,?,?,?,?,?)",
        (sid, user["id"], hash_ip(ip), now, now, exp),
    )
    resp = JSONResponse(
        {"ok": True, "role": user["role"], "username": user["username"],
         "stages": json.loads(user["stages"])},
    )
    _set_session_cookies(resp, cfg, sid, csrf, cfg.session_ttl_min * 60)
    return resp


@router.post("/logout")
async def logout(request: Request, response: Response):
    db = get_db(request)
    sid = request.cookies.get(SESSION_COOKIE, "")
    if sid:
        db.ex("UPDATE sessions SET revoked = 1 WHERE sid = ?", (sid,))
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return {
        "ok": True,
        "username": user["username"],
        "role": user["role"],
        "stages": user["stages"],
    }


@router.post("/totp/setup")
async def totp_setup(body: TotpSetupIn, request: Request):
    db = get_db(request)
    user = db.one("SELECT * FROM users WHERE username = ? AND disabled = 0",
                  (body.username,))
    if not user or not verify_password(body.password, user["pwd_salt"], user["pwd_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "auth_failed")
    pending = user["pending_totp_secret"]
    if not pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no_pending_setup")
    if not totp_verify(bytes(pending), body.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad_code")
    db.ex(
        "UPDATE users SET totp_secret = ?, pending_totp_secret = NULL, "
        " totp_required = 1, updated_at = ? WHERE id = ?",
        (pending, db.now(), user["id"]),
    )
    return {"ok": True}


@router.post("/password")
async def change_password(body: PasswordIn, request: Request,
                          user: dict = Depends(current_user)):
    db = get_db(request)
    if user["role"] == "admin":
        secret = user.get("totp_secret")
        code = request.headers.get("x-step-up-totp", "")
        if not secret or not code or not totp_verify(bytes(secret), code):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "stepup_failed")
    salt, phash = hash_password(body.new_password)
    db.ex(
        "UPDATE users SET pwd_salt = ?, pwd_hash = ?, failed_count = 0, "
        " locked_until = 0, updated_at = ? WHERE id = ?",
        (salt, phash, db.now(), user["id"]),
    )
    return {"ok": True}
