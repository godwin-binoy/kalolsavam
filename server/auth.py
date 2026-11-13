"""FullAuth setup: cookie sessions, Argon2, roles.

NOTE: Do NOT add `from __future__ import annotations` to this module.
SQLModel's Relationship() helper inspects __annotations__ at class-creation
time. With future annotations active, `list["Role"]` becomes the literal
string `"list['Role']"`, which SQLModel forwards to SQLAlchemy as the
target model — causing `InvalidRequestError: relationship("list['Role']")`.
"""
import json
from pathlib import Path

from fastapi_fullauth import FullAuth, FullAuthConfig, UserSchema
from fastapi_fullauth.adapters import SQLModelAdapter
from fastapi_fullauth.backends import CookieBackend
from fastapi_fullauth.models.sqlmodel import (
    RefreshTokenMixin,
    RoleMixin,
    UserMixin,
    UserRoleMixin,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from pydantic import Field as PydanticField
from sqlmodel import Field, Relationship

from .config import Settings


class RefreshToken(RefreshTokenMixin, table=True):
    pass


class Role(RoleMixin, table=True):
    pass


class UserRole(UserRoleMixin, table=True):
    pass


class User(UserMixin, table=True):
    __tablename__ = "fullauth_users"
    stages: str = Field(default="[]", max_length=2000)
    roles: list["Role"] = Relationship(
        link_model=UserRole,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    refresh_tokens: list["RefreshToken"] = Relationship(
        sa_relationship_kwargs={"lazy": "noload"},
    )


class KalUserSchema(UserSchema):
    stages: str = "[]"
    roles: list[str] = PydanticField(default_factory=list)


def create_auth(cfg: Settings):
    db_path = Path(cfg.auth_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
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
    )
    is_https = cfg.public_origin.startswith("https://")
    samesite = (cfg.cookie_samesite or ("none" if is_https else "lax")).lower()
    fullauth = FullAuth(
        adapter=adapter,
        config=config,
        backends=[CookieBackend(config, secure=is_https, samesite=samesite)],
    )
    return fullauth, engine, session_maker


def get_user_stages(user: User | KalUserSchema) -> list[int]:
    try:
        return json.loads(getattr(user, "stages", "[]") or "[]")
    except Exception:
        return []


def has_role(user: User | KalUserSchema, *names: str) -> bool:
    for r in getattr(user, "roles", ()) or ():
        role_name = r if isinstance(r, str) else getattr(r, "name", None)
        if role_name in names:
            return True
    return False
