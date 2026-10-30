"""Runtime configuration — loaded from an untracked .env file (see .env.example).

Never commit real values. Secrets are validated at startup; the server refuses
to boot in production mode with missing/weak secrets.
"""
from __future__ import annotations

import ipaddress
import os
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path(os.environ.get("KAL_ENV", ROOT / "server" / ".env"))


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_env_file(ENV_PATH)


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_int(key: str, default: int) -> int:
    try:
        return int(_get(key, str(default)))
    except ValueError:
        return default


HEX32_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class Config:
    def __init__(self) -> None:
        self.env_name = _get("ENVIRONMENT", "development")
        self.is_prod = self.env_name == "production"

        self.host = _get("SERVER_HOST", "127.0.0.1")
        self.port = _get_int("SERVER_PORT", 8443)
        self.tls_cert = Path(_get("TLS_CERT_PATH", "server/certs/server.pem"))
        self.tls_key = Path(_get("TLS_KEY_PATH", "server/certs/server.key"))

        self.db_path = Path(_get("DB_PATH", "server/data/kalolsavam.db"))

        # Ed25519 signing seeds: "kid:hexseed,kid2:hexseed2"
        self.signing_seeds: dict[str, bytes] = {}
        raw_seeds = _get("SESSION_SIGNING_SEEDS")
        active_kid = ""
        for pair in [p.strip() for p in raw_seeds.split(",") if p.strip()]:
            kid, _, seed = pair.partition(":")
            if HEX32_RE.match(seed):
                self.signing_seeds[kid.strip()] = bytes.fromhex(seed)
                active_kid = kid.strip()
        self.active_kid = active_kid

        # LEGACY (optional): old AES-GCM key for TOTP blobs written before the
        # no-DB-encryption policy. Only needed to auto-migrate an existing DB.
        self.field_key_raw = _get("DB_FIELD_KEY")

        self.access_ttl_min = _get_int("ACCESS_TOKEN_TTL_MIN", 15)
        self.refresh_ttl_hours = _get_int("REFRESH_TOKEN_TTL_HOURS", 8)
        self.idle_lock_min = _get_int("IDLE_LOCK_MIN", 30)

        allow = _get("ADMIN_IP_ALLOWLIST", "")
        self.admin_nets = []
        for cidr in [c.strip() for c in allow.split(",") if c.strip()]:
            try:
                self.admin_nets.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                pass

        self.public_origin = _get("PUBLIC_SITE_ORIGIN", "")

    @property
    def field_key(self) -> bytes:
        """Derive a stable 32-byte symmetric key from DB_FIELD_KEY."""
        import hashlib

        src = self.field_key_raw.encode() if self.field_key_raw else b"dev-only-insecure"
        return hashlib.sha256(src).digest()

    def validate(self) -> None:
        problems = []
        if not self.signing_seeds:
            problems.append("SESSION_SIGNING_SEEDS is empty/invalid")
        if not self.field_key_raw and self.is_prod:
            # Not fatal any more (DB is never encrypted); just warn so a stale
            # empty value doesn't look like a hard requirement.
            print("note: DB_FIELD_KEY unset — fine unless migrating a legacy "
                  "database with encrypted TOTP blobs")
        if self.is_prod and self.host in ("0.0.0.0", "::"):
            problems.append("SERVER_HOST wildcard bind without reverse proxy")
        if problems:
            raise SystemExit("Config error(s):\n - " + "\n - ".join(problems))

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def generate_seeds_example() -> str:
    kid = "k" + secrets.token_hex(2)
    return f"{kid}:{secrets.token_hex(32)}"
