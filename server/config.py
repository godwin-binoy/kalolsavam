"""Runtime settings loaded from env / server/.env."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / "server" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    public_origin: str = Field(default="http://localhost:8000")
    session_ttl_min: int = Field(default=480, ge=1, le=10080)
    idle_lock_min: int = Field(default=30, ge=1, le=1440)
    db_path: str = Field(default=str(ROOT / "server" / "data" / "kalolsavam.db"))
    results_url: str = "https://kalolsavam.kerala.gov.in/"
    server_host: str = "127.0.0.1"
    server_port: int = 8000

    @field_validator("public_origin")
    @classmethod
    def _valid_origin(cls, v: str) -> str:
        v = v.rstrip("/")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("PUBLIC_ORIGIN must start with http:// or https://")
        return v

    @field_validator("results_url")
    @classmethod
    def _valid_results(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("RESULTS_REDIRECT_URL must be https")
        return v
