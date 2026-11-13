"""FastAPI FullAuth setup: SQLModel adapter, Bearer + refresh tokens, roles."""
from __future__ import annotations

import json
from typing import Any

from fastapi_fullauth import FullAuth, FullAuthConfig
from fastapi_fullauth.adapters import SQLModelAdapter
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import Settings
from .database import make_engine, make_session_maker
from .models import KalUserSchema, RefreshToken, Role, User, UserRole


def create_auth(
    cfg: Settings,
    engine: AsyncEngine | None = None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> tuple[FullAuth, AsyncEngine, async_sessionmaker[AsyncSession]]:
    if engine is None:
        engine = make_engine(cfg.db_path)
    if session_maker is None:
        session_maker = make_session_maker(engine)

    adapter = SQLModelAdapter(
        session_maker=session_maker,
        user_model=User,
        refresh_token_model=RefreshToken,
        role_model=Role,
        user_role_model=UserRole,
        user_schema=KalUserSchema,
    )
    config = FullAuthConfig(
        SECRET_KEY=cfg.secret_key,
        ACCESS_TOKEN_EXPIRE_MINUTES=cfg.session_ttl_min,
        API_PREFIX="/api/v1",
        LOGIN_FIELD="email",
    )
    fullauth = FullAuth(adapter=adapter, config=config)
    return fullauth, engine, session_maker


def get_user_stages(user: Any) -> list[int]:
    try:
        raw = getattr(user, "stages", "[]") or "[]"
        if isinstance(raw, list):
            return [int(x) for x in raw]
        return [int(x) for x in json.loads(raw)]
    except Exception:
        return []


def has_role(user: Any, *names: str) -> bool:
    roles = getattr(user, "roles", []) or []
    for r in roles:
        r_name = r if isinstance(r, str) else getattr(r, "name", None)
        if r_name in names:
            return True
    return False
