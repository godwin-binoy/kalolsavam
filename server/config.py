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
    allowed_origins: str = Field(default="")
    cookie_samesite: str = Field(default="")
    session_ttl_min: int = Field(default=480, ge=1, le=10080)
    secret_key: str = Field(default="")
    auth_db_path: str = Field(default=str(ROOT / "deployment" / "fullauth.db"))
    db_path: str = Field(default=str(ROOT / "deployment" / "kalolsavam.db"))
    results_url: str = "https://kalolsavam.kerala.gov.in/"
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    dist_path: str = Field(default=str(ROOT / "dist"))
    trust_proxy_headers: bool = False

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
        if not v:
            import secrets
            key_file = ROOT / "deployment" / "secret.key"
            if key_file.exists():
                try:
                    stored = key_file.read_text().strip()
                    if stored:
                        return stored
                except Exception:
                    pass
            key = secrets.token_urlsafe(48)
            try:
                key_file.parent.mkdir(parents=True, exist_ok=True)
                key_file.write_text(key)
                try:
                    key_file.chmod(0o600)
                except Exception:
                    pass
            except Exception:
                pass
            return key
        return v

    @field_validator("results_url")
    @classmethod
    def _valid_results(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("RESULTS_REDIRECT_URL must be https")
        return v
