"""Shared FastAPI dependencies: roles, stage enforcement, worker auth, rate limiting."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi_fullauth.dependencies import current_user

from .auth import get_user_stages, has_role
from .models import KalUserSchema

__all__ = [
    "CurrentUser",
    "check_rate_limit",
    "check_stage",
    "client_ip",
    "csv_cell",
    "derive_worker_token",
    "escape_like",
    "get_cfg",
    "get_db",
    "hash_ip",
    "rate_limit",
    "require_admin",
    "require_photo_staff",
    "require_staff",
    "require_worker",
]

CurrentUser = KalUserSchema
_RATE_LOCK = threading.Lock()
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def hash_ip(ip: str, secret: str = "") -> str:
    return hmac.new(secret.encode("utf-8"), ip.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def derive_worker_token(secret: str, scope: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"worker:{scope}".encode(),
        hashlib.sha256,
    ).hexdigest()


def csv_cell(val: object) -> str:
    s = "" if val is None else str(val)
    stripped = s.lstrip()
    if stripped and stripped[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def escape_like(val: str) -> str:
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_db(request: Request):
    return request.app.state.db


def get_cfg(request: Request):
    return request.app.state.cfg


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


def check_stage(user, venue_id: int) -> None:
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


def client_ip(request: Request) -> str:
    cfg = get_cfg(request)
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
            stale = [k for k, dq in _RATE_BUCKETS.items() if not dq or dq[-1] <= cutoff]
            for k in stale:
                del _RATE_BUCKETS[k]


def rate_limit(bucket: str, max_calls: int, window_sec: int):
    def _dep(request: Request) -> None:
        check_rate_limit(request, bucket, max_calls, window_sec)

    return _dep
