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
        self.port = _get_int("SERVER_PORT", 8000)

        # TLS: NOT handled here any more. The venue's internet is unreliable,
        # so the site is published through a Cloudflare Tunnel (cloudflared),
        # which terminates HTTPS at Cloudflare's edge and reaches this server
        # over plain HTTP on localhost. No local CA / certificates to manage.
        # Set FORCE_TLS=1 only if you run your own HTTPS reverse proxy instead.
        self.force_tls = _get("FORCE_TLS", "0") in ("1", "true", "yes", "on")
        self.tls_cert = Path(_get("TLS_CERT_PATH", "")) if self.force_tls else None
        self.tls_key = Path(_get("TLS_KEY_PATH", "")) if self.force_tls else None

        # Behind a tunnel/proxy the socket peer is always 127.0.0.1, so real
        # client IPs must come from CF-Connecting-IP / X-Forwarded-For. Enable
        # ONLY when a tunnel or reverse proxy fronts us (spoofable otherwise).
        self.trust_proxy = _get("TRUST_PROXY", "1") in ("1", "true", "yes", "on")

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

        # Optional WAN source-IP allowlist for /api/admin/* (CIDRs applied to
        # the REAL visitor IP from CF-Connecting-IP). There is no LAN access:
        # everything arrives over the internet through the Cloudflare tunnel,
        # so this is empty by default and protection comes entirely from
        # auth (SRP + JWT + mandatory TOTP step-up) plus rate limits/lockouts.
        # Only set this if you want to pin admin to known static IPs.
        self.admin_nets = []
        allow = _get("ADMIN_IP_ALLOWLIST", "")
        for cidr in [c.strip() for c in allow.split(",") if c.strip()]:
            try:
                self.admin_nets.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                pass

        self.public_origin = _get("PUBLIC_SITE_ORIGIN", "")

        # Optional path suffix for the dashboard mounts, e.g. "7f3a" →
        # /stagemaster-7f3a and /admin-7f3a. Convenience only (quieter logs);
        # NEVER a security boundary — all protection lives in the APIs.
        salt = _get("DASHBOARD_PATH_SALT")
        salt = re.sub(r"[^A-Za-z0-9_-]", "", salt)[:16]
        self.dash_suffix = f"-{salt}" if salt else ""

        # Where the official results live. We do NOT host or publish results —
        # the public site's "Results" links redirect to this government URL.
        self.results_url = _get(
            "RESULTS_REDIRECT_URL",
            "https://kalolsavam.kerala.gov.in/")

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
        if self.is_prod and not self.force_tls \
                and self.host not in ("127.0.0.1", "::1", "localhost"):
            problems.append(
                "SERVER_HOST is not loopback while TLS is off — with the "
                "Cloudflare tunnel the server must bind 127.0.0.1 (the tunnel "
                "connects locally). Set SERVER_HOST=127.0.0.1, or FORCE_TLS=1 "
                "if you front it with your own HTTPS reverse proxy.")
        # No LAN access any more: every visitor (public + staff) reaches us
        # over the internet through Cloudflare. If someone left TRUST_PROXY=0
        # in .env, CF-Connecting-IP would be ignored and all rate-limiting /
        # auditing would key on 127.0.0.1 — refuse to boot instead.
        if self.is_prod and not self.trust_proxy:
            problems.append(
                "TRUST_PROXY=0 in production — behind the Cloudflare tunnel "
                "every request arrives from localhost, so real client IPs "
                "(CF-Connecting-IP) must be trusted for rate limits and the "
                "admin allowlist to work. Set TRUST_PROXY=1.")
        if self.force_tls and (not self.tls_cert or not self.tls_key):
            problems.append("FORCE_TLS=1 but TLS_CERT_PATH/TLS_KEY_PATH unset")
        if problems:
            raise SystemExit("Config error(s):\n - " + "\n - ".join(problems))

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def generate_seeds_example() -> str:
    kid = "k" + secrets.token_hex(2)
    return f"{kid}:{secrets.token_hex(32)}"
