"""Shared dependencies: auth user, roles, stage checks, IP resolution."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress

from fastapi import Depends, HTTPException, Request, status

from .auth import AuthUser, current_user, get_user_stages, has_role

__all__ = [
    "get_db", "get_cfg", "require_admin", "require_staff",
    "check_stage", "client_ip", "hash_ip", "CurrentUser",
]

CurrentUser = AuthUser


def hash_ip(ip: str, secret: str = "") -> str:
    return hmac.new(secret.encode("utf-8"), ip.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def get_db(request: Request):
    return request.app.state.db


def get_cfg(request: Request):
    return request.app.state.cfg


def require_admin(user: AuthUser = Depends(current_user)) -> AuthUser:
    if not has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_only")
    return user


def require_staff(user: AuthUser = Depends(current_user)) -> AuthUser:
    if not has_role(user, "stagemaster", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    return user


def check_stage(user: AuthUser, venue_id: int) -> None:
    if has_role(user, "admin"):
        return
    if venue_id not in get_user_stages(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "stage_not_assigned")


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
