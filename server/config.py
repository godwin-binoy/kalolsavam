"""Runtime configuration — loaded from an untracked .env file (see .env.example).

Setup is intentionally tiny: copy .env.example to .env, generate ONE secret,
start the server. Secrets are validated at startup; the server refuses to boot
in production mode with missing/weak secrets.
"""
from __future__ import annotations

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


SECRET_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class Config:
    def __init__(self) -> None:
        self.env_name = _get("ENVIRONMENT", "development")
        self.is_prod = self.env_name == "production"

        self.host = _get("SERVER_HOST", "127.0.0.1")
        self.port = _get_int("SERVER_PORT", 8000)

        # TLS is terminated at Cloudflare's edge — no certificates here.
        # The tunnel (cloudflared) runs on this same machine and connects to
        # us over plain HTTP on 127.0.0.1. FORCE_TLS=1 is only for the rare
        # case of running your own HTTPS reverse proxy instead of the tunnel.
        self.force_tls = _get("FORCE_TLS", "0") in ("1", "true", "yes", "on")
        self.tls_cert = Path(_get("TLS_CERT_PATH", "")) if self.force_tls else None
        self.tls_key = Path(_get("TLS_KEY_PATH", "")) if self.force_tls else None

        # Behind the tunnel every socket peer is 127.0.0.1, so the real
        # visitor IP must be read from CF-Connecting-IP. Keep this ON
        # whenever a tunnel/proxy fronts us; turn it OFF only for local dev.
        self.trust_proxy = _get("TRUST_PROXY", "1") in ("1", "true", "yes", "on")

        self.db_path = Path(_get("DB_PATH", "server/data/kalolsavam.db"))

        # Optional URL suffix for the staff dashboards, e.g. /admin-2k26.
        # Purely cosmetic obscurity (the real protection is the API auth);
        # leave empty unless you want a slightly less guessable path.
        sfx = _get("DASHBOARD_SUFFIX", "")
        self.dash_suffix = sfx if re.match(r"^[0-9a-zA-Z_-]{0,24}$", sfx) else ""

        # JWT signing secret(s): "kid:hex64,kid2:hex64". One pair is enough;
        # rotation = add a new kid in front, old tokens die out in 15 min.
        self.signing_seeds: dict[str, bytes] = {}
        raw_seeds = _get("SESSION_SIGNING_SEEDS")
        active_kid = ""
        for pair in [p.strip() for p in raw_seeds.split(",") if p.strip()]:
            kid, _, seed = pair.partition(":")
            if SECRET_RE.match(seed):
                self.signing_seeds[kid.strip()] = bytes.fromhex(seed)
                active_kid = kid.strip()
        self.active_kid = active_kid

        self.access_ttl_min = _get_int("ACCESS_TOKEN_TTL_MIN", 15)
        self.refresh_ttl_hours = _get_int("REFRESH_TOKEN_TTL_HOURS", 8)
        self.idle_lock_min = _get_int("IDLE_LOCK_MIN", 30)

        # Where the official results live. We do NOT host or publish results —
        # the public site's "Results" links redirect to this government URL.
        self.results_url = _get(
            "RESULTS_REDIRECT_URL",
            "https://kalolsavam.kerala.gov.in/")

    def validate(self) -> None:
        problems = []
        if not self.signing_seeds:
            problems.append(
                "SESSION_SIGNING_SEEDS is empty/invalid — generate one with:\n"
                "   python -c \"import secrets; print('k1:'+secrets.token_hex(32))\"")
        # No LAN access: every visitor reaches us through the Cloudflare
        # tunnel, i.e. from localhost. If TRUST_PROXY were off, all rate
        # limits would key on 127.0.0.1 and stop working — refuse to boot.
        if self.is_prod and not self.trust_proxy:
            problems.append(
                "TRUST_PROXY=0 in production — behind the Cloudflare tunnel "
                "every request arrives from localhost, so real client IPs "
                "(CF-Connecting-IP) must be trusted for rate limits to work. "
                "Set TRUST_PROXY=1.")
        if self.is_prod and not self.force_tls \
                and self.host not in ("127.0.0.1", "::1", "localhost"):
            problems.append(
                "SERVER_HOST is not loopback while TLS is off — with the "
                "Cloudflare tunnel the server must bind 127.0.0.1 (the tunnel "
                "connects locally). Set SERVER_HOST=127.0.0.1.")
        if self.force_tls and (not self.tls_cert or not self.tls_key):
            problems.append("FORCE_TLS=1 but TLS_CERT_PATH/TLS_KEY_PATH unset")
        if problems:
            raise SystemExit("Config error(s):\n - " + "\n - ".join(problems))

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def generate_seeds_example() -> str:
    return f"k1:{secrets.token_hex(32)}"
