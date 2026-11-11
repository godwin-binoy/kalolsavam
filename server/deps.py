"""Shared dependencies: FullAuth user, roles, stage checks, IP resolution."""
from __future__ import annotations

import hashlib
import ipaddress

from fastapi import Depends, HTTPException, Request, status
from fastapi_fullauth.dependencies import current_user

from .auth import User, get_user_stages, has_role

__all__ = [
    "get_db", "get_cfg", "require_admin", "require_staff",
    "check_stage", "client_ip", "hash_ip", "CurrentUser",
]

CurrentUser = User
_IP_SALT = b"kalolsavam_audit_salt_fixed"


def hash_ip(ip: str) -> str:
    return hashlib.sha256(_IP_SALT + ip.encode("utf-8")).hexdigest()[:32]


def get_db(request: Request):
    return request.app.state.db


def get_cfg(request: Request):
    return request.app.state.cfg


def require_admin(user: User = Depends(current_user)) -> User:
    if not has_role(user, "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin_only")
    return user


def require_staff(user: User = Depends(current_user)) -> User:
    if not has_role(user, "stagemaster", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
    return user


def check_stage(user: User, venue_id: int) -> None:
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
