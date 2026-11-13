"""Request DTOs with input normalization and validation."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


def _require_non_blank(v: str | None) -> str | None:
    if v is None:
        return None
    stripped = v.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def _optional_slug(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip().lower()
    return s or None


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


class VenueIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="stage", max_length=32)
    slug: str | None = Field(default=None, max_length=64, pattern=r"^[a-z0-9-]+$")
    active: bool = True

    @field_validator("slug", mode="before")
    @classmethod
    def _clean_slug(cls, v: str | None) -> str | None:
        return _optional_slug(v)

    @field_validator("name", "kind")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _require_non_blank(v)  # type: ignore[return-value]


class VenueUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = Field(default=None, max_length=32)
    slug: str | None = Field(default=None, max_length=64, pattern=r"^[a-z0-9-]+$")
    active: bool | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def _clean_slug(cls, v: str | None) -> str | None:
        return _optional_slug(v)

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


class EventIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)

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
