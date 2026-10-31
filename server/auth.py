"""Authentication core — deliberately small and boring, because students run
this system and security must survive real-world handling.

How it works:
 - Passwords are verified with PBKDF2-HMAC-SHA256 (240k iterations, per-user
   random salt). Only the derived hash is stored — never the password.
   Transport safety comes from HTTPS at Cloudflare's edge (the tunnel);
   brute-force safety comes from rate limits + per-account lockouts.
 - Sessions are short-lived HMAC-SHA256 (HS256) JWTs kept in memory only.
 - Refresh tokens are single-use random strings rotated on every refresh;
   replaying an old one revokes the whole token family.
 - TOTP (RFC 6238) second factor, mandatory for admins. Secrets are stored
   as plain bytes in the DB file — the database is NEVER encrypted, so a
   lost key can never lock us out of our own data. File permissions protect it.

SQL injection is impossible by construction: every statement in this project
is a fixed string with '?' placeholders and a params tuple (see db.py).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time

# ------------------------------------------------------------- passwords ----
PBKDF2_ITERS = 240_000


def make_password_hash(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for storage."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt,
                             PBKDF2_ITERS)
    return salt.hex(), dk.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt,
                             PBKDF2_ITERS)
    return hmac.compare_digest(dk.hex(), (hash_hex or "").lower())


# ------------------------------------------------------------------- JWT ----
def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class TokenIssuer:
    """HS256 JWT issuer/verifier (constant-time comparison, strict alg check).

    `seeds` maps key-id -> secret bytes; multiple kids exist only so a
    rotation can keep old tokens verifiable until they expire (15 min).
    """

    def __init__(self, seeds: dict[str, bytes], active_kid: str,
                 access_ttl_min: int):
        if not seeds or not active_kid or active_kid not in seeds:
            raise ValueError("missing signing key")
        self.seeds = seeds
        self.active_kid = active_kid
        self.access_ttl = access_ttl_min * 60

    def issue_access(self, *, user_id: int, username: str, role: str,
                     sid: str, stages: list[int], enroll: bool = False) -> str:
        now = int(time.time())
        payload = {
            "sub": str(user_id), "usr": username, "role": role, "sid": sid,
            "stages": stages, "iat": now, "exp": now + self.access_ttl,
            "jti": secrets.token_hex(12), "iss": "kalolsavam-api",
        }
        if enroll:  # TOTP-enrollment-scoped token (see routes_auth /verify)
            payload["scope"] = "enroll"
            payload["exp"] = now + 300
        header = {"alg": "HS256", "typ": "JWT", "kid": self.active_kid}
        seg_h = _b64u(json.dumps(header, separators=(",", ":")).encode())
        seg_p = _b64u(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{seg_h}.{seg_p}".encode()
        sig = hmac.new(self.seeds[self.active_kid], signing_input,
                       hashlib.sha256).digest()
        return f"{seg_h}.{seg_p}.{_b64u(sig)}"

    def verify_access(self, token: str) -> dict:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed token")
        try:
            header = json.loads(_b64u_decode(parts[0]))
            payload = json.loads(_b64u_decode(parts[1]))
            sig = _b64u_decode(parts[2])
        except Exception:
            raise ValueError("malformed token")
        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise ValueError("malformed token")
        # alg must be EXACTLY HS256 — rejects "none" and any confusion attack
        if header.get("alg") != "HS256":
            raise ValueError("bad algorithm")
        if header.get("typ", "JWT") != "JWT":
            raise ValueError("bad type")
        kid = header.get("kid")
        key = self.seeds.get(kid)
        if key is None:
            raise ValueError("unknown kid")
        expected = hmac.new(key, f"{parts[0]}.{parts[1]}".encode(),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("bad signature")
        now = time.time()
        if payload.get("exp", 0) < now - 5:
            raise ValueError("token expired")
        if payload.get("iss") != "kalolsavam-api":
            raise ValueError("bad issuer")
        if not payload.get("sub") or not payload.get("sid"):
            raise ValueError("token missing claims")
        return payload


# ------------------------------------------------------- refresh rotation ---
def new_refresh(db, user_id: int, family: str | None, parent_jti: str | None,
                sid: str, ttl_hours: int) -> tuple[str, float]:
    jti = secrets.token_urlsafe(32)
    exp = db.now() + ttl_hours * 3600
    db.execute(
        "INSERT INTO refresh_tokens(jti,user_id,family,parent_jti,expires_at,created_at)"
        " VALUES(?,?,?,?,?,?)",
        (jti, user_id, family or secrets.token_hex(8), parent_jti, exp, db.now()),
    )
    db.execute(
        "UPDATE sessions SET current_jti=?, last_seen=? WHERE sid=?", (jti, db.now(), sid)
    )
    return jti, exp


def consume_refresh(db, jti: str) -> dict | None:
    """Atomically mark used; returns {user_id, family} or None. Reuse of an
    already-used token revokes the entire family (stolen-token detection)."""
    row = db.one("SELECT * FROM refresh_tokens WHERE jti=?", (jti,))
    if not row or row["revoked"] or row["expires_at"] < db.now():
        return None
    if row["used"]:
        # Reuse detected: revoke the whole family AND every session still
        # pointing at one of its tokens.
        db.execute("UPDATE refresh_tokens SET revoked=1 WHERE family=?",
                   (row["family"],))
        db.execute("UPDATE sessions SET revoked=1 WHERE current_jti IN "
                   "(SELECT jti FROM refresh_tokens WHERE family=?)",
                   (row["family"],))
        return {"reuse": True, "user_id": row["user_id"], "family": row["family"]}
    # Conditional UPDATE = compare-and-swap: two concurrent refreshes of the
    # same token can never both succeed (prevents a double-issued session).
    cur = db.execute("UPDATE refresh_tokens SET used=1 WHERE jti=? AND used=0",
                     (jti,))
    if cur.rowcount == 0:
        return None
    return {"reuse": False, "user_id": row["user_id"], "family": row["family"],
            "parent_jti": jti}


def revoke_all_for_user(db, user_id: int) -> None:
    db.execute("UPDATE refresh_tokens SET revoked=1 WHERE user_id=?", (user_id,))
    db.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (user_id,))


# ------------------------------------------------------------------ TOTP ----
def totp_provision() -> bytes:
    return os.urandom(20)  # 160-bit secret, RFC 4226 recommendation


def _totp_code(secret: bytes, counter: int, digits: int = 6) -> str:
    msg = struct.pack(">Q", counter)
    digest = hmac.new(secret, msg, hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def totp_now(secret: bytes, t: float | None = None, step: int = 30,
             digits: int = 6) -> str:
    return _totp_code(secret, int((t if t is not None else time.time()) // step),
                      digits)


def totp_verify(secret: bytes, code: str, window: int = 1) -> bool:
    """Constant-time compare across the ±window skew.

    Each code may be consumed only ONCE per time-step per secret: a replayed
    code inside its validity window is rejected (guards against an attacker
    sniffing/reshowing one live code)."""
    try:
        c = int(code)
    except ValueError:
        return False
    if not (0 <= c < 1_000_000):
        return False
    target = str(c).zfill(6)
    now = time.time()
    matched_step = None
    for skew in range(-window, window + 1):
        step_no = int((now + skew * 30) // 30)
        if hmac.compare_digest(_totp_code(secret, step_no), target):
            matched_step = step_no
            break
    if matched_step is None:
        return False
    # Single-use enforcement keyed by the SECRET VALUE (not id(): rows are
    # re-read from SQLite every call, so id() would differ and let replays
    # through). Server runs as ONE process, so this in-memory map is enough.
    used = getattr(totp_verify, "_used", None)
    if used is None:
        used = {}
        totp_verify._used = used
    key = (secret[:], matched_step)
    if used.get(key) == target:
        return False
    used[key] = target
    if len(used) > 512:                    # keep the map bounded
        cutoff = int(now // 30) - 2 * (window + 1)
        for k in [k for k in used if k[1] < cutoff]:
            used.pop(k, None)
    return True


def totp_uri(secret: bytes, username: str, issuer: str = "Kalolsavam") -> str:
    b32 = base64.b32encode(secret).decode().rstrip("=")
    return (f"otpauth://totp/{issuer}:{username}?secret={b32}"
            f"&issuer={issuer}&algorithm=SHA1&digits=6&period=30")
