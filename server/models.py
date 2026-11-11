"""Request DTOs."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


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
    active: bool = True


class VenueUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = Field(default=None, max_length=32)
    active: bool | None = None


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    group: str = Field(default="HSS GENERAL", max_length=64)


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    group: str | None = Field(default=None, max_length=64)


class EventIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


class EventUpdateIn(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


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
    school: str = Field(max_length=200)
    student_name: str | None = Field(default=None, max_length=200)
    roll: str | None = Field(default=None, max_length=64)


class QueueItemUpdateIn(BaseModel):
    school: str | None = Field(default=None, max_length=200)
    student_name: str | None = Field(default=None, max_length=200)
    roll: str | None = Field(default=None, max_length=64)


class QueueMoveIn(BaseModel):
    direction: str = Field(pattern=r"^(up|down)$")
