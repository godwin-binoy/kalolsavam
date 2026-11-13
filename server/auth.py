"""Single-DB authentication: Argon2id + Bearer/Cookie sessions + rate limiting."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()
_ph = PasswordHasher()
_DUMMY_HASH = _ph.hash("kalolsavam-constant-time-dummy-secret")

_FAIL_WINDOW_SEC = 900
_MAX_FAILS_PER_IP = 15
_MAX_FAILS_PER_USER_IP = 8


@dataclass
class AuthUser:
    id: int
    email: str
    role: str
    stages: list[int]
    is_active: bool = True


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except VerifyMismatchError:
        return False


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def parse_stages(raw: str | list[int] | None) -> list[int]:
    if isinstance(raw, list):
        return [int(x) for x in raw]
    try:
        vals = json.loads(raw or "[]")
        return [int(x) for x in vals] if isinstance(vals, list) else []
    except Exception:
        return []


def has_role(user: AuthUser, *names: str) -> bool:
    return user.role in names


def get_user_stages(user: AuthUser) -> list[int]:
    return list(user.stages)


def _req_ip(request: Request) -> str:
    cfg = request.app.state.cfg
    peer = request.client.host if request.client else ""
    if not peer:
        return "unknown"
    if cfg.trust_proxy_headers:
        for header in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
            val = request.headers.get(header, "")
            if not val:
                continue
            candidate = val.split(",")[0].strip()
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                continue
    return peer


def _req_ip_hash(request: Request) -> str:
    secret = request.app.state.cfg.secret_key.encode("utf-8")
    return hmac.new(secret, _req_ip(request).encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def _extract_token(request: Request) -> tuple[str | None, str | None]:
    auth_hdr = request.headers.get("authorization", "")
    if auth_hdr.lower().startswith("bearer "):
        tok = auth_hdr[7:].strip()
        if tok:
            return tok, "bearer"
    cookie_tok = request.cookies.get("kal_session", "").strip()
    if cookie_tok:
        return cookie_tok, "cookie"
    return None, None


def current_user(request: Request) -> AuthUser:
    raw_token, via = _extract_token(request)
    if not raw_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not_authenticated")

    db = request.app.state.db
    row = db.one(
        "SELECT u.id, u.email, u.role, u.stages, u.is_active, s.expires_at "
        "FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ?",
        (hash_token(raw_token),),
    )
    if not row or row["expires_at"] <= db.now() or not row["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_or_expired_session")

    request.state.auth_via = via
    return AuthUser(
        id=int(row["id"]),
        email=str(row["email"]),
        role=str(row["role"]),
        stages=parse_stages(row["stages"]),
        is_active=bool(row["is_active"]),
    )


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    db = request.app.state.db
    cfg = request.app.state.cfg
    email = body.email.strip().lower()
    ip_h = _req_ip_hash(request)
    now = db.now()
    cutoff = now - _FAIL_WINDOW_SEC

    ip_fails = db.one(
        "SELECT COUNT(*) c FROM auth_audit WHERE ip_hash = ? AND event = 'login_fail' AND ts > ?",
        (ip_h, cutoff),
    )["c"]
    user_ip_fails = db.one(
        "SELECT COUNT(*) c FROM auth_audit WHERE ip_hash = ? AND username = ? AND event = 'login_fail' AND ts > ?",
        (ip_h, email, cutoff),
    )["c"]
    if ip_fails >= _MAX_FAILS_PER_IP or user_ip_fails >= _MAX_FAILS_PER_USER_IP:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_attempts")

    row = db.one("SELECT * FROM users WHERE email = ?", (email,))
    if not row:
        verify_password(_DUMMY_HASH, body.password)
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (now, email, ip_h, "login_fail", "unknown_user"),
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")

    if not verify_password(row["password_hash"], body.password):
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (now, email, ip_h, "login_fail", "bad_password"),
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")

    if not row["is_active"]:
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (now, email, ip_h, "login_fail", "user_disabled"),
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "user_disabled")

    raw_token = secrets.token_urlsafe(32)
    ttl_sec = cfg.session_ttl_min * 60
    with db.transaction():
        if _ph.check_needs_rehash(row["password_hash"]):
            db.ex(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (hash_password(body.password), now, row["id"]),
            )
        db.ex("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        db.ex(
            "INSERT INTO sessions(token_hash, user_id, expires_at, created_at) VALUES (?,?,?,?)",
            (hash_token(raw_token), row["id"], now + ttl_sec, now),
        )
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (now, email, ip_h, "login_ok", f"role={row['role']}"),
        )

    is_https = cfg.public_origin.startswith("https://")
    samesite = (cfg.cookie_samesite or ("none" if is_https else "lax")).lower()
    response.set_cookie(
        key="kal_session",
        value=raw_token,
        max_age=ttl_sec,
        httponly=True,
        secure=is_https,
        samesite=samesite,
        path="/",
    )
    return {
        "access_token": raw_token,
        "token_type": "bearer",
        "user": {
            "id": str(row["id"]),
            "email": row["email"],
            "roles": [row["role"]],
            "stages": parse_stages(row["stages"]),
        },
    }


@router.get("/me")
def me(user: AuthUser = Depends(current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "roles": [user.role],
        "stages": user.stages,
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    raw_token, _ = _extract_token(request)
    if raw_token:
        request.app.state.db.ex(
            "DELETE FROM sessions WHERE token_hash = ?",
            (hash_token(raw_token),),
        )
    response.delete_cookie("kal_session", path="/")
    return {"ok": True}
