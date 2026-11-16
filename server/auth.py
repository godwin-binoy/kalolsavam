"""Auth, JWT + refresh rotation, RBAC, worker HMAC auth, rate limiting, and shared helpers."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()
ph = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)
_RATE_LOCK = threading.Lock()
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_REFRESH_TTL_SEC = 30 * 86400


def get_db(request: Request):
    return request.app.state.db


def get_cfg(request: Request):
    return request.app.state.cfg


def hash_ip(ip: str, secret: str = "") -> str:
    return hmac.new(secret.encode("utf-8"), ip.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def derive_worker_token(secret: str, scope: str) -> str:
    return hmac.new(secret.encode("utf-8"), f"worker:{scope}".encode(), hashlib.sha256).hexdigest()


def csv_cell(val: object) -> str:
    s = "" if val is None else str(val)
    stripped = s.lstrip()
    return ("'" + s) if stripped and stripped[0] in ("=", "+", "-", "@", "\t", "\r") else s


def escape_like(val: str) -> str:
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def client_ip(request: Request) -> str:
    cfg = get_cfg(request)
    peer = request.client.host if request.client else ""
    if not peer:
        return "unknown"
    if cfg.trust_proxy_headers:
        for hdr in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
            val = request.headers.get(hdr, "")
            if not val:
                continue
            cand = val.split(",")[0].strip()
            try:
                ipaddress.ip_address(cand)
                return cand
            except ValueError:
                continue
    return peer


def check_rate_limit(request: Request, bucket: str, max_calls: int, window_sec: int) -> None:
    cfg = get_cfg(request)
    key = f"{bucket}:{hash_ip(client_ip(request), cfg.secret_key)}"
    now = time.monotonic()
    cutoff = now - window_sec
    with _RATE_LOCK:
        q = _RATE_BUCKETS[key]
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= max_calls:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")
        q.append(now)
        if len(_RATE_BUCKETS) > 4096:
            for k in [k for k, dq in _RATE_BUCKETS.items() if not dq or dq[-1] <= cutoff]:
                del _RATE_BUCKETS[k]


def rate_limit(bucket: str, max_calls: int, window_sec: int):
    def _dep(request: Request) -> None:
        check_rate_limit(request, bucket, max_calls, window_sec)

    return _dep


def get_user_stages(user: dict[str, Any]) -> list[int]:
    try:
        raw = user.get("stages", "[]")
        items = raw if isinstance(raw, list) else json.loads(raw or "[]")
        return [int(x) for x in items]
    except Exception:
        return []


def has_role(user: dict[str, Any], *names: str) -> bool:
    return user.get("role") in names


def _issue_tokens(db, cfg, user: dict[str, Any]) -> dict[str, str]:
    now = int(time.time())
    access = jwt.encode(
        {
            "sub": str(user["id"]),
            "typ": "access",
            "ver": int(user["token_version"]),
            "iat": now,
            "exp": now + cfg.session_ttl_min * 60,
            "jti": secrets.token_hex(8),
        },
        cfg.secret_key,
        algorithm="HS256",
    )
    raw_refresh = secrets.token_urlsafe(32)
    rhash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
    db.ex("DELETE FROM refresh_tokens WHERE expires_at < ?", (now,))
    db.ex(
        "INSERT INTO refresh_tokens(user_id, token_hash, expires_at, revoked, created_at) VALUES (?,?,?,0,?)",
        (user["id"], rhash, now + _REFRESH_TTL_SEC, now),
    )
    return {"access_token": access, "refresh_token": raw_refresh, "token_type": "bearer"}


def current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    cfg = get_cfg(request)
    try:
        payload = jwt.decode(creds.credentials, cfg.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token") from exc
    if payload.get("typ") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")

    db = get_db(request)
    try:
        uid = int(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token") from exc

    u = db.one("SELECT * FROM users WHERE id = ?", (uid,))
    if not u or not u["is_active"] or int(u["token_version"]) != int(payload.get("ver", -1)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session_invalidated")
    return dict(u)


def require_admin(user=Depends(current_user)):
    if not has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_only")
    return user


def require_staff(user=Depends(current_user)):
    if not has_role(user, "stagemaster", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    return user


def require_photo_staff(user=Depends(current_user)):
    if not has_role(user, "stagemaster", "dataworker", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    return user


def check_stage(user: dict[str, Any], venue_id: int) -> None:
    if has_role(user, "admin"):
        return
    if venue_id not in get_user_stages(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "stage_not_assigned")


def require_worker(scope: str):
    def _dep(request: Request, x_worker_token: str | None = Header(default=None)):
        cfg = get_cfg(request)
        if not x_worker_token or not cfg.secret_key:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid_worker_token")
        expected = derive_worker_token(cfg.secret_key, scope)
        if not hmac.compare_digest(x_worker_token.strip(), expected):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid_worker_token")
        return scope

    return _dep


# ── Auth HTTP Endpoints ───────────────────────────────────────────────────────
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=256)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


@router.post("/login")
def login(body: LoginIn, request: Request):
    db, cfg = get_db(request), get_cfg(request)
    email = body.email.strip().lower()
    ip_h = hash_ip(client_ip(request), cfg.secret_key)
    u = db.one("SELECT * FROM users WHERE email = ?", (email,))
    if not u or not u["is_active"]:
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (db.now(), email, ip_h, "login_fail", "invalid_or_disabled"),
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")
    try:
        ph.verify(u["password_hash"], body.password)
    except VerifyMismatchError as exc:
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (db.now(), email, ip_h, "login_fail", "bad_password"),
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials") from exc

    with db.transaction():
        if ph.check_needs_rehash(u["password_hash"]):
            db.ex("UPDATE users SET password_hash = ? WHERE id = ?", (ph.hash(body.password), u["id"]))
        tokens = _issue_tokens(db, cfg, dict(u))
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (db.now(), email, ip_h, "login_ok", "status=200"),
        )
    return tokens


@router.post("/refresh")
def refresh(body: RefreshIn, request: Request):
    db, cfg = get_db(request), get_cfg(request)
    rhash = hashlib.sha256(body.refresh_token.strip().encode("utf-8")).hexdigest()
    now = db.now()
    with db.transaction():
        row = db.one("SELECT * FROM refresh_tokens WHERE token_hash = ?", (rhash,))
        if not row or row["expires_at"] < now:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token")
        if row["revoked"]:
            # Reuse detection: invalidate all sessions for this user
            db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (row["user_id"],))
            db.ex("UPDATE users SET token_version = token_version + 1 WHERE id = ?", (row["user_id"],))
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh_token_reused")
        u = db.one("SELECT * FROM users WHERE id = ?", (row["user_id"],))
        if not u or not u["is_active"]:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account_disabled")
        db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE id = ?", (row["id"],))
        return _issue_tokens(db, cfg, dict(u))


@router.post("/logout")
def logout(request: Request, body: RefreshIn | None = None, user=Depends(current_user)):
    db = get_db(request)
    with db.transaction():
        if body and body.refresh_token:
            rhash = hashlib.sha256(body.refresh_token.strip().encode("utf-8")).hexdigest()
            db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ? AND user_id = ?", (rhash, user["id"]))
        else:
            db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user["id"],))
            db.ex("UPDATE users SET token_version = token_version + 1 WHERE id = ?", (user["id"],))
    return {"ok": True}


@router.get("/me")
def me(user=Depends(current_user)):
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "roles": [user["role"]],
        "stages": get_user_stages(user),
    }


@router.post("/change-password")
def change_password(body: ChangePasswordIn, request: Request, user=Depends(current_user)):
    db = get_db(request)
    try:
        ph.verify(user["password_hash"], body.old_password)
    except VerifyMismatchError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "wrong_current_password") from exc
    with db.transaction():
        db.ex(
            "UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE id = ?",
            (ph.hash(body.new_password), user["id"]),
        )
        db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user["id"],))
    return {"ok": True}
