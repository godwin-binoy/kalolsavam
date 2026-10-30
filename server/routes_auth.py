"""SRP-6a login endpoints + refresh rotation + logout + TOTP step-up.

Flow (see docs/SECURITY.md §2):
  1. POST /challenge {username, A_hex}      -> {sid, salt, B_hex}   (server stores b)
  2. POST /verify    {sid, M1_hex, totp?}   -> {M2_hex, access, csrf cookie, rt cookie}
  3. POST /refresh   (HttpOnly cookie)      -> new access + rotated rt
  4. POST /logout                            -> revoke session + family
The password never leaves the client; even over TLS we run SRP so a
compromised proxy/log cannot replay credentials.
"""
from __future__ import annotations

import hmac
import secrets as _secrets
import time

from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .auth import (
    srp_server_ephemeral, srp_server_secret, srp_M, srp_HAMK,
    _to_bytes, _from_bytes, N, new_refresh, consume_refresh,
    totp_verify, revoke_all_for_user,
)
from .app import REFRESH_COOKIE, CSRF_COOKIE

router = APIRouter()

SRP_TTL = 60.0  # challenge must be completed within 60s


def _ctx(request: Request):
    return request.app.state.db, request.app.state.tokens, \
        request.app.state.field, request.app.state.cfg


def _client_ip(request: Request) -> str:
    from .app import client_ip
    return client_ip(request)


class ChallengeIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    A: str = Field(pattern=r"^[0-9a-fA-F]{1,512}$")  # hex big-endian


@router.post("/challenge")
async def challenge(body: ChallengeIn, request: Request):
    db, _, _, cfg = _ctx(request)
    ip = _client_ip(request)
    user = db.one("SELECT * FROM users WHERE username=? AND disabled=0",
                  (body.username,))
    # Uniform response — do NOT reveal whether the account exists.
    fake_sid = _secrets.token_hex(16)
    if not user or not user["srp_verifier_hex"]:
        # burn CPU identically: compute with random verifier
        v = _from_bytes(_secrets.token_bytes(256)) % N
        b, B = srp_server_ephemeral(v)
        db.execute(
            "INSERT INTO srp_sessions(sid,user_id,private_b_hex,B_hex,salt_hex,A_hex,issued_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (fake_sid, 0, hex(b), hex(B), _secrets.token_hex(16),
             body.A.lower(), db.now()),
        )
        return {"sid": fake_sid, "salt": _secrets.token_hex(16), "B": hex(B)}

    if user["locked_until"] > db.now():
        retry = int(user["locked_until"] - db.now())
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            {"detail": "account_locked", "retry_after": retry})

    b, B = srp_server_ephemeral(int(user["srp_verifier_hex"], 16))
    sid = _secrets.token_hex(16)
    db.execute(
        "INSERT INTO srp_sessions(sid,user_id,private_b_hex,B_hex,salt_hex,A_hex,issued_at)"
        " VALUES(?,?,?,?,?,?,?)",
        (sid, user["id"], hex(b), hex(B), user["srp_salt_hex"],
         body.A.lower(), db.now()),
    )
    db.log_auth(username=body.username, user_id=user["id"], ip=ip,
                event="challenge", detail="")
    return {"sid": sid, "salt": user["srp_salt_hex"], "B": hex(B)}


class VerifyIn(BaseModel):
    sid: str = Field(min_length=8, max_length=64, pattern=r"^[0-9a-f]+$")
    M1: str = Field(pattern=r"^[0-9a-f]{64}$")           # SHA-256 hex
    totp: str | None = Field(default=None, pattern=r"^\d{6}$")


@router.post("/verify")
async def verify(body: VerifyIn, request: Request, response: Response):
    db, tokens, field, cfg = _ctx(request)
    ip = _client_ip(request)
    row = db.one("SELECT * FROM srp_sessions WHERE sid=?", (body.sid,))
    bad = HTTPException(status.HTTP_401_UNAUTHORIZED, "auth_failed")
    if not row or row["consumed"] or db.now() - row["issued_at"] > SRP_TTL:
        raise bad
    db.execute("UPDATE srp_sessions SET consumed=1 WHERE sid=?", (body.sid,))

    user = db.one("SELECT * FROM users WHERE id=?", (row["user_id"],))
    if not user or user["disabled"]:
        raise bad

    if not row["A_hex"]:
        raise bad
    A_int = _from_bytes(bytes.fromhex(row["A_hex"]))
    if A_int % N == 0 or A_int >= N:
        raise bad
    B_int = _from_bytes(bytes.fromhex(row["B_hex"]))

    try:
        S = srp_server_secret(A_int, B_int,
                              int(row["private_b_hex"], 16),
                              int(user["srp_verifier_hex"], 16))
    except ValueError:
        raise bad
    expected_M = srp_M(user["username"], row["salt_hex"], A_int, B_int, S)
    if not hmac.compare_digest(expected_M.hex(), body.M1.lower()):
        # failed proof → increment lockout
        fails = user["failed_count"] + 1
        lock_secs = [0, 0, 60, 300, 900][min(fails, 4)]
        db.execute("UPDATE users SET failed_count=?, locked_until=? WHERE id=?",
                   (fails, db.now() + lock_secs, user["id"]))
        db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                    event="login_fail", detail=f"count={fails}")
        raise bad

    # ---- TOTP second factor (mandatory for admin, optional otherwise) ----
    if user["totp_required"] or user["role"] == "admin":
        if not user["totp_enc"]:
            db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                        event="totp_missing", detail="enrollment required")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "totp_enrollment_required")
        if not body.totp:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "totp_required")
        secret = field.decrypt(bytes(user["totp_enc"]),
                               aad=str(user["id"]).encode())
        if not totp_verify(secret, body.totp):
            db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                        event="totp_fail", detail="")
            raise bad

    db.execute("UPDATE users SET failed_count=0, locked_until=0 WHERE id=?",
               (user["id"],))
    db.log_auth(username=user["username"], user_id=user["id"], ip=ip,
                event="login_ok", detail="")

    M2 = srp_HAMK(user["username"], row["salt_hex"], A_int, B_int, S)

    # ---- issue session ----
    import json as _json
    stages = _json.loads(user["stages"])
    sess_id = _secrets.token_hex(16)
    db.execute("INSERT INTO sessions(sid,user_id,created_at,last_seen) VALUES(?,?,?,?)",
               (sess_id, user["id"], db.now(), db.now()))
    rt_jti, exp = new_refresh(db, user["id"], None, None, sess_id,
                              cfg.refresh_ttl_hours)
    access = tokens.issue_access(user_id=user["id"], username=user["username"],
                                 role=user["role"], sid=sess_id, stages=stages)
    csrf = _secrets.token_urlsafe(32)

    secure = cfg.is_prod
    response.set_cookie(REFRESH_COOKIE, rt_jti, httponly=True, secure=secure,
                        samesite="strict", path="/api/auth", max_age=int(exp - db.now()))
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=secure,
                        samesite="strict", path="/api/auth",
                        max_age=int(exp - db.now()))
    return {"M2": M2.hex(), "access": access, "csrf": csrf,
            "role": user["role"], "username": user["username"],
            "stages": stages, "expires_in": cfg.access_ttl_min * 60}


# ---------------------------------------------------------- refresh -------
@router.post("/refresh")
async def refresh(request: Request, response: Response):
    db, tokens, _, cfg = _ctx(request)
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

    import json as _json
    stages = _json.loads(user["stages"])
    new_jti, exp = new_refresh(db, user["id"], res["family"], jti, sess["sid"],
                               cfg.refresh_ttl_hours)
    access = tokens.issue_access(user_id=user["id"], username=user["username"],
                                 role=user["role"], sid=sess["sid"], stages=stages)
    secure = cfg.is_prod
    response.set_cookie(REFRESH_COOKIE, new_jti, httponly=True, secure=secure,
                        samesite="strict", path="/api/auth",
                        max_age=int(exp - db.now()))
    return {"access": access, "expires_in": cfg.access_ttl_min * 60}


# ----------------------------------------------------------- logout -------
@router.post("/logout")
async def logout(request: Request, response: Response):
    db, _, _, cfg = _ctx(request)
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
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
    response.delete_cookie(CSRF_COOKIE, path="/api/auth")
    return {"ok": True}# ------------------------------------------------- TOTP enrollment --------
PENDING_TOTP: dict[str, tuple[int, bytes, float]] = {}


@router.post("/totp/start")
async def totp_start(request: Request):
    """Authenticated: generate a fresh secret, return its otpauth:// URI so the
    staff member can scan it with their authenticator app. Confirm within 10 min."""
    from .auth import totp_provision, totp_uri
    claims = request.app.state.get_access(request)
    db, _, field, _ = _ctx(request)
    uid = int(claims["sub"])
    secret = totp_provision()
    token = _secrets.token_hex(16)
    PENDING_TOTP[token] = (uid, field.encrypt(secret, aad=str(uid).encode()),
                           time.time())
    # single-use cleanup of stale pendings
    stale = [k for k, (_, _, ts) in PENDING_TOTP.items() if time.time() - ts > 600]
    for k in stale:
        PENDING_TOTP.pop(k, None)
    return {"uri": totp_uri(secret, claims["usr"]), "confirm_token": token}


@router.post("/totp/confirm")
async def totp_confirm(body: TotpConfirmIn, request: Request):
    from .auth import totp_verify
    claims = request.app.state.get_access(request)
    db, _, field, _ = _ctx(request)
    ip = _client_ip(request)
    entry = PENDING_TOTP.get(body.confirm_token)
    if not entry or entry[0] != int(claims["sub"]) or time.time() - entry[2] > 600:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "confirm_expired")
    uid, enc_secret, _ = entry
    secret = field.decrypt(enc_secret, aad=str(uid).encode())
    if not totp_verify(secret, body.code):
        db.log_auth(username=claims["usr"], user_id=uid, ip=ip,
                    event="totp_enroll_fail", detail="")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad_code")
    PENDING_TOTP.pop(body.confirm_token, None)
    db.execute("UPDATE users SET totp_enc=?, totp_required=1, updated_at=? WHERE id=?",
               (enc_secret, db.now(), uid))
    db.log_auth(username=claims["usr"], user_id=uid, ip=ip,
                event="totp_enrolled", detail="")
    return {"ok": True}
