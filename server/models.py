"""Unified SQLModel database tables and Pydantic request schemas.

Do NOT add `from __future__ import annotations` here: SQLModel's Relationship()
inspects string annotations at class creation time.
"""
import re
from typing import Annotated

from fastapi_fullauth import UserSchema
from fastapi_fullauth.models.sqlmodel import (
    RefreshTokenMixin,
    RoleMixin,
    UserMixin,
    UserRoleMixin,
)
from pydantic import BaseModel, BeforeValidator, EmailStr, Field
from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlmodel import Field as SQLField
from sqlmodel import Relationship, SQLModel


def _strip(v: object) -> object:
    return v.strip() if isinstance(v, str) else v


def _clean_slug(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s:
        return None
    if not re.fullmatch(r"[a-z0-9-]+", s) or len(s) > 64:
        raise ValueError("invalid slug")
    return s


CleanSlug = Annotated[str | None, BeforeValidator(_clean_slug)]
ReqStr = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=200)]
OptStr = Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=200)]
ReqShort = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=120)]
OptShort = Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=120)]


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
class Venue(SQLModel, table=True):
    __tablename__ = "venues"
    __table_args__ = (
        Index("idx_venues_slug", "slug", unique=True, sqlite_where=text("slug IS NOT NULL")),
    )
    id: int | None = SQLField(default=None, primary_key=True)
    name: str = SQLField(min_length=1, max_length=120)
    kind: str = SQLField(default="stage", max_length=32)
    slug: str | None = SQLField(default=None, max_length=64)
    active: bool = SQLField(default=True)


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: int | None = SQLField(default=None, primary_key=True)
    name: str = SQLField(min_length=1, max_length=120)
    grp: str = SQLField(default="HSS GENERAL", max_length=64)


class Event(SQLModel, table=True):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("code", name="uq_events_code"),
        Index("idx_events_venue", "venue_id"),
        Index("idx_events_day_time", "day", "scheduled_time"),
    )
    id: int | None = SQLField(default=None, primary_key=True)
    code: str = SQLField(min_length=1, max_length=32)
    title: str = SQLField(min_length=1, max_length=200)
    category_id: int | None = SQLField(default=None, foreign_key="categories.id")
    venue_id: int | None = SQLField(default=None, foreign_key="venues.id")
    day: str | None = SQLField(default=None, max_length=32)
    scheduled_time: str | None = SQLField(default=None, max_length=16)


class Participant(SQLModel, table=True):
    __tablename__ = "participants"
    __table_args__ = (
        Index(
            "uq_participants_register_no",
            "register_no",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("idx_participants_school_code", "school_code"),
    )
    id: int | None = SQLField(default=None, primary_key=True)
    register_no: str = SQLField(min_length=5, max_length=5)
    name: str = SQLField(min_length=1, max_length=200)
    school_name: str = SQLField(min_length=1, max_length=200)
    school_code: str = SQLField(min_length=5, max_length=6)
    student_class: int = SQLField(ge=1, le=12)
    created_at: float
    updated_at: float
    deleted_at: float | None = SQLField(default=None)


class ParticipantEntry(SQLModel, table=True):
    __tablename__ = "participant_entries"
    __table_args__ = (
        Index(
            "uq_participant_entries_item",
            "participant_id",
            "item_code",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index("idx_entries_item", "item_code"),
        Index("idx_entries_venue_date", "venue_id", "perf_date"),
    )
    id: int | None = SQLField(default=None, primary_key=True)
    participant_id: int = SQLField(
        sa_column=Column(
            Integer,
            ForeignKey("participants.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    item_code: str = SQLField(min_length=1, max_length=32)
    venue_id: int
    venue_name: str = SQLField(min_length=1, max_length=120)
    perf_date: str = SQLField(min_length=10, max_length=10)
    created_at: float
    updated_at: float
    deleted_at: float | None = SQLField(default=None)


class QueueItem(SQLModel, table=True):
    __tablename__ = "queue_items"
    __table_args__ = (
        Index("idx_queue_board", "venue_id", "status", "position"),
        Index("idx_queue_venue_status_pos", "venue_id", "status", "position"),
    )
    id: int | None = SQLField(default=None, primary_key=True)
    venue_id: int = SQLField(foreign_key="venues.id")
    event_id: int = SQLField(foreign_key="events.id")
    participant_id: int | None = SQLField(default=None)
    participant_entry_id: int | None = SQLField(
        default=None,
        sa_column=Column(Integer, ForeignKey("participant_entries.id", ondelete="SET NULL"), nullable=True),
    )
    chest_no: str | None = SQLField(default=None, max_length=16)
    status: str = SQLField(default="WAITING", max_length=16)
    position: int = SQLField(default=0)
    version: int = SQLField(default=1)
    started_at: float | None = SQLField(default=None)
    completed_at: float | None = SQLField(default=None)
    updated_at: float


class LiveState(SQLModel, table=True):
    __tablename__ = "live_state"
    venue_id: int = SQLField(primary_key=True, foreign_key="venues.id")
    state: str = SQLField(default="IDLE", max_length=16)
    current_item: str | None = SQLField(default=None, max_length=200)
    current_chest: str | None = SQLField(default=None, max_length=32)
    upcoming_chests: str | None = SQLField(default=None, max_length=280)
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


# ── Request Validation DTOs ───────────────────────────────────────────────────
class StateIn(BaseModel):
    venue_id: int
    active: bool | None = None
    state: str = Field(pattern=r"^(IDLE|RUNNING|PAUSED|BREAK|FINISHED)$")
    current_item: str | None = Field(default=None, max_length=200)
    current_chest: str | None = Field(default=None, max_length=32)
    upcoming_chests: str | None = Field(default=None, max_length=280)
    announcement: str = Field(default="", max_length=280)


class AdvanceIn(BaseModel):
    venue_id: int
    action: str = Field(pattern=r"^(START_NEXT|COMPLETE_CURRENT|PAUSE|RESUME|SKIP|RECALL)$")
    version: int | None = None
    item_id: int | None = None
    chest_no: str | None = Field(default=None, max_length=16)


class VenueIn(BaseModel):
    name: ReqShort
    kind: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = "stage"
    slug: CleanSlug = None
    active: bool = True


class VenueUpdateIn(BaseModel):
    name: OptShort = None
    kind: Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = None
    slug: CleanSlug = None
    active: bool | None = None


class CategoryIn(BaseModel):
    name: ReqShort
    group: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=64)] = "HSS GENERAL"


class CategoryUpdateIn(BaseModel):
    name: OptShort = None
    group: Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=64)] = None


class EventIn(BaseModel):
    code: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)]
    title: ReqStr
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


class EventUpdateIn(BaseModel):
    code: Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = None
    title: OptStr = None
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


class UserIn(BaseModel):
    email: EmailStr
    role: str = Field(pattern=r"^(stagemaster|dataworker|admin)$")
    stages: list[int] = Field(default_factory=list)
    password: str = Field(min_length=12, max_length=256)


class UserUpdateIn(BaseModel):
    email: EmailStr | None = None
    role: str | None = Field(default=None, pattern=r"^(stagemaster|dataworker|admin)$")
    stages: list[int] | None = None
    is_active: bool | None = None


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class AddToQueueIn(BaseModel):
    venue_id: int
    participant_entry_id: int
    chest_no: str | None = Field(default=None, max_length=16)


class QueueItemUpdateIn(BaseModel):
    chest_no: str | None = Field(default=None, max_length=16)


class QueueMoveIn(BaseModel):
    direction: str = Field(pattern=r"^(up|down)$")


class ParticipantIn(BaseModel):
    register_no: str = Field(pattern=r"^\d{5}$")
    name: ReqStr
    school_name: ReqStr
    school_code: str = Field(pattern=r"^\d{5,6}$")
    student_class: int = Field(alias="class", ge=1, le=12)

    model_config = {"populate_by_name": True}


class ParticipantUpdateIn(BaseModel):
    register_no: str | None = Field(default=None, pattern=r"^\d{5}$")
    name: OptStr = None
    school_name: OptStr = None
    school_code: str | None = Field(default=None, pattern=r"^\d{5,6}$")
    student_class: int | None = Field(default=None, alias="class", ge=1, le=12)

    model_config = {"populate_by_name": True}


class ParticipantEntryIn(BaseModel):
    item_code: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)]
    venue_id: int
    venue_name: ReqShort
    perf_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class ParticipantEntryUpdateIn(BaseModel):
    item_code: Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = None
    venue_id: int | None = None
    venue_name: OptShort = None
    perf_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PhotoBatchIn(BaseModel):
    queue_item_id: int | None = None
    venue_id: int
    workflow: str = Field(pattern=r"^(bulk|quick)$")
    perf_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PhotoAssignIn(BaseModel):
    asset_id: int
    participant_entry_ids: list[int] = Field(min_length=1, max_length=30)


class PhotoAssignByRegisterIn(BaseModel):
    asset_id: int
    venue_id: int
    item_code: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)]
    register_nos: list[str] = Field(min_length=1, max_length=30)
    perf_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PhotoLookupIn(BaseModel):
    register_no: str = Field(pattern=r"^\d{5}$")
    name: ReqStr
