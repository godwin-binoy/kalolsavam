"""Request DTOs."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    totp: str | None = Field(default=None, pattern=r"^\d{6}$")


class TotpSetupIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    code: str = Field(pattern=r"^\d{6}$")


class PasswordIn(BaseModel):
    new_password: str = Field(min_length=10, max_length=256)


class StateIn(BaseModel):
    venue_id: int
    state: str = Field(pattern=r"^(IDLE|RUNNING|PAUSED|BREAK|FINISHED)$")
    announcement: str = Field(default="", max_length=280)


class AdvanceIn(BaseModel):
    venue_id: int
    action: str = Field(pattern=r"^(START_NEXT|COMPLETE_CURRENT|PAUSE|RESUME|SKIP|RECALL)$")
    version: int | None = None


class ScoreIn(BaseModel):
    queue_item_id: int
    judge_no: int = Field(ge=1, le=10)
    value: float = Field(ge=0, le=100)


class VenueIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="stage", max_length=32)
    active: bool = True


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    group: str = Field(default="HSS GENERAL", max_length=64)


class EventIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    category_id: int | None = None
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9._-]+$")
    role: str = Field(pattern=r"^(stagemaster|admin)$")
    stages: list[int] = Field(default_factory=list)
    password: str = Field(min_length=12, max_length=256)


class FlagIn(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_.]+$")
    value: str = Field(max_length=512)
