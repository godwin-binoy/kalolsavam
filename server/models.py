"""Unified SQLModel database tables and Pydantic request schemas.

Do NOT add `from __future__ import annotations` here: SQLModel's Relationship()
inspects string annotations at class creation time.
"""
import re

from fastapi_fullauth import UserSchema
from fastapi_fullauth.models.sqlmodel import (
    RefreshTokenMixin,
    RoleMixin,
    UserMixin,
    UserRoleMixin,
)
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlmodel import Field as SQLField
from sqlmodel import Relationship, SQLModel


def _require_non_blank(v: str | None) -> str | None:
    if v is None:
        return None
    stripped = v.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def _clean_slug_val(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip().lower()
    if not s:
        return None
    if not re.fullmatch(r"[a-z0-9-]+", s) or len(s) > 64:
        raise ValueError("invalid slug")
    return s


# ── Auth Tables (fastapi-fullauth SQLModel) ───────────────────────────────────
class RefreshToken(RefreshTokenMixin, table=True):
    pass


class Role(RoleMixin, table=True):
    pass


class UserRole(UserRoleMixin, table=True):
    pass


class User(UserMixin, table=True):
    __tablename__ = "fullauth_users"
    stages: str = SQLField(default="[]", max_length=2000)
    roles: list["Role"] = Relationship(
        link_model=UserRole,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    refresh_tokens: list["RefreshToken"] = Relationship(
        sa_relationship_kwargs={"lazy": "noload"},
    )


class KalUserSchema(UserSchema):
    stages: str = "[]"
    roles: list[str] = Field(default_factory=list)


# ── Festival Tables (SQLModel) ────────────────────────────────────────────────
class VenueBase(SQLModel):
    name: str = SQLField(min_length=1, max_length=120)
    kind: str = SQLField(default="stage", max_length=32)
    slug: str | None = SQLField(default=None, max_length=64)
    active: bool = SQLField(default=True)


class Venue(VenueBase, table=True):
    __tablename__ = "venues"
    __table_args__ = (
        Index("idx_venues_slug", "slug", unique=True, sqlite_where=text("slug IS NOT NULL")),
    )
    id: int | None = SQLField(default=None, primary_key=True)


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: int | None = SQLField(default=None, primary_key=True)
    name: str = SQLField(min_length=1, max_length=120)
    grp: str = SQLField(default="HSS GENERAL", max_length=64)


class EventBase(SQLModel):
    code: str = SQLField(min_length=1, max_length=32)
    title: str = SQLField(min_length=1, max_length=200)
    category_id: int | None = SQLField(default=None, foreign_key="categories.id")
    venue_id: int | None = SQLField(default=None, foreign_key="venues.id")
    day: str | None = SQLField(default=None, max_length=32)
    scheduled_time: str | None = SQLField(default=None, max_length=16)


class Event(EventBase, table=True):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("code", name="uq_events_code"),
        Index("idx_events_venue", "venue_id"),
        Index("idx_events_day_time", "day", "scheduled_time"),
    )
    id: int | None = SQLField(default=None, primary_key=True)


class Participant(SQLModel, table=True):
    __tablename__ = "participants"
    id: int | None = SQLField(default=None, primary_key=True)
    event_id: int | None = SQLField(
        default=None,
        sa_column=Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True),
    )
    school: str = SQLField(min_length=1, max_length=200)
    student_name: str | None = SQLField(default=None, max_length=200)
    roll: str | None = SQLField(default=None, max_length=64)


class QueueItem(SQLModel, table=True):
    __tablename__ = "queue_items"
    __table_args__ = (
        Index("idx_queue_board", "venue_id", "status", "position"),
        Index("idx_queue_venue_status_pos", "venue_id", "status", "position"),
    )
    id: int | None = SQLField(default=None, primary_key=True)
    venue_id: int = SQLField(foreign_key="venues.id")
    event_id: int = SQLField(foreign_key="events.id")
    participant_id: int | None = SQLField(
        default=None,
        sa_column=Column(Integer, ForeignKey("participants.id", ondelete="CASCADE"), nullable=True),
    )
    status: str = SQLField(default="WAITING", max_length=16)
    position: int = SQLField(default=0)
    version: int = SQLField(default=1)
    started_at: float | None = SQLField(default=None)
    completed_at: float | None = SQLField(default=None)
    updated_at: float


class Score(SQLModel, table=True):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("queue_item_id", "judge_no", name="uq_scores_item_judge"),)
    id: int | None = SQLField(default=None, primary_key=True)
    queue_item_id: int | None = SQLField(
        default=None,
        sa_column=Column(Integer, ForeignKey("queue_items.id", ondelete="CASCADE"), nullable=True),
    )
    judge_no: int
    value: float
    entered_by: str
    entered_at: float


class LiveState(SQLModel, table=True):
    __tablename__ = "live_state"
    venue_id: int = SQLField(primary_key=True, foreign_key="venues.id")
    state: str = SQLField(default="IDLE", max_length=16)
    announcement: str = SQLField(default="", max_length=280)
    updated_at: float


class Idempotency(SQLModel, table=True):
    __tablename__ = "idempotency"
    key: str = SQLField(primary_key=True)
    response: str
    created_at: float


class AuthAudit(SQLModel, table=True):
    __tablename__ = "auth_audit"
    __table_args__ = (
        Index("idx_audit_ts", "ts"),
        Index("idx_audit_ip_event_ts", "ip_hash", "event", "ts"),
    )
    id: int | None = SQLField(default=None, primary_key=True)
    ts: float
    username: str | None = SQLField(default=None)
    ip_hash: str | None = SQLField(default=None)
    event: str
    detail: str | None = SQLField(default=None)


# ── Request Validation DTOs (Pydantic v2 BaseModel) ───────────────────────────
class StateIn(BaseModel):
    venue_id: int
    state: str = Field(pattern=r"^(IDLE|RUNNING|PAUSED|BREAK|FINISHED)$")
    announcement: str = Field(default="", max_length=280)


class AdvanceIn(BaseModel):
    venue_id: int
    action: str = Field(pattern=r"^(START_NEXT|COMPLETE_CURRENT|PAUSE|RESUME|SKIP|RECALL)$")
    version: int | None = None
    item_id: int | None = None


class ScoreIn(BaseModel):
    queue_item_id: int
    judge_no: int = Field(ge=1, le=10)
    value: float = Field(ge=0, le=100)


class VenueIn(VenueBase):
    @field_validator("slug", mode="before")
    @classmethod
    def _clean_slug(cls, v: str | None) -> str | None:
        return _clean_slug_val(v)

    @field_validator("name", "kind")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _require_non_blank(v)  # type: ignore[return-value]


class VenueUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = Field(default=None, max_length=32)
    slug: str | None = Field(default=None, max_length=64)
    active: bool | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def _clean_slug(cls, v: str | None) -> str | None:
        return _clean_slug_val(v)

    @field_validator("name", "kind")
    @classmethod
    def _clean(cls, v: str | None) -> str | None:
        return _require_non_blank(v)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    group: str = Field(default="HSS GENERAL", max_length=64)

    @field_validator("name", "group")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _require_non_blank(v)  # type: ignore[return-value]


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    group: str | None = Field(default=None, max_length=64)

    @field_validator("name", "group")
    @classmethod
    def _clean(cls, v: str | None) -> str | None:
        return _require_non_blank(v)


class EventIn(EventBase):
    @field_validator("code", "title")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _require_non_blank(v)  # type: ignore[return-value]


class EventUpdateIn(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)

    @field_validator("code", "title")
    @classmethod
    def _clean(cls, v: str | None) -> str | None:
        return _require_non_blank(v)


class UserIn(BaseModel):
    email: EmailStr
    role: str = Field(pattern=r"^(stagemaster|admin)$")
    stages: list[int] = Field(default_factory=list)
    password: str = Field(min_length=12, max_length=256)


class UserUpdateIn(BaseModel):
    email: EmailStr | None = None
    role: str | None = Field(default=None, pattern=r"^(stagemaster|admin)$")
    stages: list[int] | None = None
    is_active: bool | None = None


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class AddToQueueIn(BaseModel):
    venue_id: int
    event_id: int
    school: str = Field(min_length=1, max_length=200)
    student_name: str | None = Field(default=None, max_length=200)
    roll: str | None = Field(default=None, max_length=64)

    @field_validator("school")
    @classmethod
    def _clean_school(cls, v: str) -> str:
        return _require_non_blank(v)  # type: ignore[return-value]


class QueueItemUpdateIn(BaseModel):
    school: str | None = Field(default=None, min_length=1, max_length=200)
    student_name: str | None = Field(default=None, max_length=200)
    roll: str | None = Field(default=None, max_length=64)

    @field_validator("school")
    @classmethod
    def _clean_school(cls, v: str | None) -> str | None:
        return _require_non_blank(v)


class QueueMoveIn(BaseModel):
    direction: str = Field(pattern=r"^(up|down)$")
