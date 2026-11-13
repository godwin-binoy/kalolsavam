"""Runtime settings loaded from env / server/.env."""
from __future__ import annotations

import logging
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
    allowed_origins: str = Field(default="")
    session_ttl_min: int = Field(default=480, ge=1, le=10080)
    secret_key: str = Field(default="")
    db_path: str = Field(default=str(ROOT / "deployment" / "kalolsavam.db"))
    results_url: str = "https://kalolsavam.kerala.gov.in/"
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    dist_path: str = Field(default=str(ROOT / "dist"))
    trust_proxy_headers: bool = False

    @field_validator("db_path", "dist_path")
    @classmethod
    def _absolute(cls, v: str) -> str:
        # Relative paths must not drift between sqlite3 and aiosqlite callers.
        return str(Path(v).expanduser().resolve())

    @field_validator("public_origin")
    @classmethod
    def _valid_origin(cls, v: str) -> str:
        v = v.rstrip("/")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("PUBLIC_ORIGIN must start with http:// or https://")
        return v

    @field_validator("secret_key", mode="before")
    @classmethod
    def _ensure_secret(cls, v: str) -> str:
        if v:
            return v
        import secrets

        key_file = ROOT / "deployment" / "secret.key"
        log = logging.getLogger("kalolsavam")
        if key_file.exists():
            try:
                stored = key_file.read_text().strip()
                if stored:
                    return stored
            except Exception as exc:
                log.warning("Could not read secret.key: %s", exc)
        key = secrets.token_urlsafe(48)
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_text(key)
            try:
                key_file.chmod(0o600)
            except Exception as exc:
                log.warning("Could not chmod secret.key: %s", exc)
        except Exception as exc:
            log.warning("Could not persist secret.key: %s", exc)
        return key

    @field_validator("results_url")
    @classmethod
    def _valid_results(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("RESULTS_URL must be https")
        return v
