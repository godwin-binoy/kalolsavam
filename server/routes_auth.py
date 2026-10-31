"""Login / session endpoints. One simple flow:

  POST /api/auth/login   {username, password, totp?}
      -> 200 {access, csrf, role, username, stages}   (session started)
      -> 401 {detail:"totp_enrollment_required", access, csrf}
             (password OK but no authenticator yet — run the setup wizard,
              then log in again)
  POST /api/auth/refresh   (HttpOnly cookie)  -> new access + rotated refresh
  POST /api/auth/logout    revokes this session (+ family)
  POST /api/auth/password  change own password (TOTP step-up for admins)
  POST /api/auth/totp/start|confirm   first-run authenticator enrollment

Security in one line: HTTPS at Cloudflare's edge protects the wire; PBKDF2
hashes, per-IP rate limits, per-account lockouts, uniform error messages and
TOTP protect the accounts. The access token lives only in browser memory.
"""
from __future__ import annotations

import json
import secrets as _secrets
import time

from fastapi import APIRouter, Request, Response, HTTPException, status
from pydantic import BaseModel, Field

from .auth import (
    make_password_hash, verify_password, new_refresh, consume_refresh,
    totp_verify, revoke_all_for_user, totp_provision, totp_uri,
)
from .app import REFRESH_COOKIE, CSRF_COOKIE

router = APIRouter()


def _ctx(request: Request):
    return request.app.state.db, request.app.state.tokens, request.app.state.cfg


def _client_ip(request: Request) -> str:
    from .app import client_ip
    return client_ip(request, request.app.state.cfg)


def _set_session_cookies(response: Response, cfg, rt_jti: str, exp: float,
                         csrf: str) -> None:
    # Visitors reach us over HTTPS via the Cloudflare tunnel, so Secure stays
    # on in production even though we listen on plain HTTP locally.
    secure = cfg.is_prod
    # Path=/ isolates these cookies from any other app on the same hostname,
    # SameSite=Strict blocks cross-site sends; the CSRF double-submit check
    # (cookie value must match the X-CSRF-Token header) is what actually
    # proves same-origin. Do NOT scope to /api/auth: then a login at a
    # non-canonical URL (e.g. /admin without trailing slash) would set
    # cookies the browser never sends back to /api/auth/refresh.
    response.set_cookie(REFRESH_COOKIE, rt_jti, httponly=True, secure=secure,
                        samesite="strict", path="/", max_age=max_age)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=secure,
                        samesite="strict", path="/", max_age=max_age)


class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    totp: str | None = Field(default=None, pattern=r"^\d{6}$")


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    db, tokens, cfg = _ctx(request)
    ip = _client_ip(request)
    bad = HTTPException(status.HTTP_401_UNAUTHORIZED, "auth_failed")

    user = db.one("SELECT * FROM users WHERE username=? AND disabled=0",
                  (body.username,))
    if user and user["locked_until"] > db.now():
        retry = int(user["locked_until"] - db.now())
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            {"detail": "account_locked", "retry_after": retry})

    ok = bool(user and user["pwd_salt_hex"] and user["pwd_hash_hex"]
              and verify_password(body.password, user["pwd_salt_hex"],
                                  user["pwd_hash_hex"]))
    if not ok:
        # Uniform "auth_failed" for unknown user AND wrong password (no
        # username enumeration); count failures only against real accounts.
        if user:
            fails = user["failed_count"] + 1
            lock_secs = [0, 0, 60, 300, 900][min(fails, 4)]
            db.execute("UPDATE users SET failed_count=?, locked_until=? WHERE id=?",
                       (fails, db.now() + lock_secs, user["id"]))
            db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                        event="login_fail", detail=f"count={fails}")
        else:
            db.log_auth(username=body.username[:64], user_id=None, ip=ip,
                        event="login_fail", detail="unknown_user")
        raise bad

    # ---- TOTP second factor (mandatory for admin) ----
    secret = bytes(user["totp_secret"]) if user["totp_secret"] else None
    if user["role"] == "admin" or user["totp_required"]:
        if not secret:
            # First run: password holder is genuine → hand out a short-lived
            # ENROLL-scoped token (only /totp/* accepts it) + cookies so the
            # standard CSRF/refresh machinery works during enrollment.
            db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                        event="totp_missing", detail="enrollment required")
            sess_id = _secrets.token_hex(16)
            rt_jti, exp = new_refresh(db, user["id"], None, None, sess_id,
                                      cfg.refresh_ttl_hours)
            access = tokens.issue_access(user_id=user["id"], username=user["username"],
                                         role=user["role"], sid=sess_id,
                                         stages=json.loads(user["stages"]),
                                         enroll=True)
            csrf = _secrets.token_urlsafe(32)
            _set_session_cookies(response, cfg, rt_jti, exp, csrf)
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                {"detail": "totp_enrollment_required", "access": access,
                 "csrf": csrf, "expires_in": 300})
        if not body.totp:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "totp_required")
        if not totp_verify(secret, body.totp):
            db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                        event="totp_fail", detail="")
            raise bad

    db.execute("UPDATE users SET failed_count=0, locked_until=0 WHERE id=?",
               (user["id"],))
    db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                event="login_ok", detail="")

    # ---- issue session ----
    stages = json.loads(user["stages"])
    sess_id = _secrets.token_hex(16)
    db.execute("INSERT INTO sessions(sid,user_id,created_at,last_seen) VALUES(?,?,?,?)",
               (sess_id, user["id"], db.now(), db.now()))
    rt_jti, exp = new_refresh(db, user["id"], None, None, sess_id,
                              cfg.refresh_ttl_hours)
    access = tokens.issue_access(user_id=user["id"], username=user["username"],
                                 role=user["role"], sid=sess_id, stages=stages)
    csrf = _secrets.token_urlsafe(32)
    _set_session_cookies(response, cfg, rt_jti, exp, csrf)
    return {"access": access, "csrf": csrf, "role": user["role"],
            "username": user["username"], "stages": stages,
            "expires_in": cfg.access_ttl_min * 60}


# ---------------------------------------------------------- refresh -------
@router.post("/refresh")
async def refresh(request: Request, response: Response):
    db, tokens, cfg = _ctx(request)
    ip = _client_ip(request)
    jti = request.cookies.get(REFRESH_COOKIE, "")
    if not jti:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no_refresh")
    res = consume_refresh(db, jti)
    if not res:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh")
    if res.get("reuse"):
        db.log_auth(username=None, user_id=res["user_id"], ip=ip,
                    event="refresh_reuse", detail="family revoked")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh_reused")
    user = db.one("SELECT * FROM users WHERE id=? AND disabled=0", (res["user_id"],))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh")
    sess = db.one("SELECT * FROM sessions WHERE current_jti=? AND revoked=0", (jti,))
    if not sess:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session_revoked")

    stages = json.loads(user["stages"])
    new_jti, exp = new_refresh(db, user["id"], res["family"], jti, sess["sid"],
                               cfg.refresh_ttl_hours)
    access = tokens.issue_access(user_id=user["id"], username=user["username"],
                                 role=user["role"], sid=sess["sid"], stages=stages)
    secure = cfg.is_prod
    response.set_cookie(REFRESH_COOKIE, new_jti, httponly=True, secure=secure,
                        samesite="strict", path="/",
                        max_age=int(exp - time.time()))
    return {"access": access, "expires_in": cfg.access_ttl_min * 60}


# ----------------------------------------------------------- logout -------
@router.post("/logout")
async def logout(request: Request, response: Response):
    db, _, _ = _ctx(request)
    claims = request.app.state.get_access(request)
    sid = claims["sid"]
    sess = db.one("SELECT * FROM sessions WHERE sid=?", (sid,))
    if sess and sess["current_jti"]:
        row = db.one("SELECT family FROM refresh_tokens WHERE jti=?",
                     (sess["current_jti"],))
        if row:
            db.execute("UPDATE refresh_tokens SET revoked=1 WHERE family=?",
                       (row["family"],))
    db.execute("UPDATE sessions SET revoked=1 WHERE sid=?", (sid,))
    db.log_auth(username=claims["usr"], user_id=int(claims["sub"]),
                ip=_client_ip(request), event="logout", detail="")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


# ------------------------------------------------- password change --------
class PasswordChangeIn(BaseModel):
    new_password: str = Field(min_length=10, max_length=256)


@router.post("/password")
async def change_password(body: PasswordChangeIn, request: Request):
    """Change your own password. Admins must also supply a live TOTP code in
    the x-step-up-totp header."""
    claims = request.app.state.get_access(request)
    db, _, _ = _ctx(request)
    uid = int(claims["sub"])
    user = db.one("SELECT * FROM users WHERE id=?", (uid,))
    if not user or user["disabled"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_user")
    if user["role"] == "admin" or user["totp_required"]:
        secret = bytes(user["totp_secret"]) if user["totp_secret"] else None
        code = request.headers.get("x-step-up-totp", "")
        if not secret or not code or not totp_verify(secret, code):
            db.log_auth(username=claims["usr"], user_id=uid,
                        ip=_client_ip(request), event="pwd_change_stepup_fail",
                        detail="")
            raise HTTPException(status.HTTP_403_FORBIDDEN, "stepup_failed")
    salt_hex, hash_hex = make_password_hash(body.new_password)
    db.execute("UPDATE users SET pwd_salt_hex=?, pwd_hash_hex=?, "
               "failed_count=0, locked_until=0, updated_at=? WHERE id=?",
               (salt_hex, hash_hex, db.now(), uid))
    db.log_auth(username=user["username"], user_id=uid,
                ip=_client_ip(request), event="password_changed", detail="")
    return {"ok": True}


# ------------------------------------------------- TOTP enrollment --------
PENDING_TOTP: dict[str, tuple[int, bytes, float]] = {}


@router.post("/totp/start")
async def totp_start(request: Request):
    """Authenticated (also by the enroll-scoped token): generate a fresh
    secret and return its otpauth:// URI to add to any authenticator app."""
    claims = request.app.state.get_access(request, allow_enroll=True)
    db, _, _ = _ctx(request)
    secret = totp_provision()
    token = _secrets.token_hex(16)
    PENDING_TOTP[token] = (int(claims["sub"]), secret, time.time())
    stale = [k for k, (_, _, ts) in PENDING_TOTP.items() if time.time() - ts > 600]
    for k in stale:
        PENDING_TOTP.pop(k, None)
    return {"uri": totp_uri(secret, claims["usr"]), "confirm_token": token}


class TotpConfirmIn(BaseModel):
    confirm_token: str = Field(min_length=8, max_length=64)
    code: str = Field(pattern=r"^\d{6}$")


@router.post("/totp/confirm")
async def totp_confirm(body: TotpConfirmIn, request: Request):
    claims = request.app.state.get_access(request, allow_enroll=True)
    db, _, _ = _ctx(request)
    ip = _client_ip(request)
    entry = PENDING_TOTP.get(body.confirm_token)
    if not entry or entry[0] != int(claims["sub"]) or time.time() - entry[2] > 600:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "confirm_expired")
    uid, secret, _ = entry
    if not totp_verify(secret, body.code):
        db.log_auth(username=claims["usr"], user_id=uid, ip=ip,
                    event="totp_enroll_fail", detail="")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad_code")
    PENDING_TOTP.pop(body.confirm_token, None)
    # Stored PLAINTEXT by policy: the database is never encrypted so access
    # can never be lost to a missing/rotated key. DB file protection = OS perms.
    db.execute("UPDATE users SET totp_secret=?, totp_required=1, updated_at=? "
               "WHERE id=?", (secret, db.now(), uid))
    db.log_auth(username=claims["usr"], user_id=uid, ip=ip,
                event="totp_enrolled", detail="")
    return {"ok": True}
