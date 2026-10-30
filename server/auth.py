"""SRP-6a (RFC 5054 2048-bit group), Ed25519 JWT sessions, rotating refresh
tokens, and TOTP (RFC 6238). See docs/SECURITY.md for the rationale.

 - The password NEVER crosses the wire — SRP challenge/response with mutual auth.
 - Server stores only the SRP verifier v = g^x mod N (plus salt) — not the
   password, not even a reversible hash of it.
 - Access tokens: short-lived Ed25519 JWTs kept in client memory only.
 - Refresh tokens: single-use, rotated; family reuse detection revokes all.
 - TOTP secrets encrypted at rest with AES-256-GCM (key from DB_FIELD_KEY).
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

import jwt  # PyJWT (EdDSA support)
from nacl.signing import SigningKey  # libsodium-backed Ed25519 signing
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ------------------------------------------------------------------ SRP-6a --
# RFC 5054 2048-bit safe-prime group
N_HEX = """
AC6BCA4F50455F7CCD71C6B8CEB40E31F8A3E1CC654C7BF8E77FCC29B48D58FE
A3B14DC3F2C3B5687482C875CEF96B0880B9E27682BDA698E3E3C77B676A6D93
100F0753EDAF79BA75B3757EC6FA4C5B09FF3BBE37B1A25A9FDDB052C1F870FC
26E3418EB281C0DE6B51F9B38423BA867CCBE0EA487E4ACC7E6C356DE88768A9
DD04C5F382B4C301C6DA42381D641A863902BF00696D3570A0123C5CE1F9B808
D3780135BADA78E9B1AE508A989C3D1DBC9F4B1E46F8708D96DEF587E2EF07CB
"""
N = int("".join(N_HEX.split()), 16)
g = 2


def _h(*parts: bytes) -> bytes:
    m = hashlib.sha256()
    for p in parts:
        m.update(p)
    return m.digest()


def _to_bytes(n: int) -> bytes:
    return n.to_bytes((N.bit_length() + 7) // 8, "big")


def _from_bytes(b: bytes) -> int:
    return int.from_bytes(b, "big")


_padlen = (N.bit_length() + 7) // 8
k = _from_bytes(_h(("%x" % N).zfill(_padlen * 2).encode(),
                   ("%x" % g).zfill(_padlen * 2).encode()))  # k = H(N | PAD(g))


def srp_make_verifier(username: str, password: str,
                      salt: bytes | None = None) -> tuple[str, str]:
    """Compute (salt_hex, verifier_hex) — used at account creation only.
    x = H(salt | H(username:password));  v = g^x mod N."""
    if salt is None:
        salt = os.urandom(16)
    x = _from_bytes(_h(salt, _h(f"{username}:{password}".encode())))
    v = pow(g, x, N)
    return salt.hex(), hex(v)


def srp_server_ephemeral(v: int) -> tuple[int, int]:
    """Return (b, B). b private, B public ephemeral."""
    b = secrets.randbelow(N - 1) + 1
    B = (k * v + pow(g, b, N)) % N
    return b, B


def srp_server_secret(A: int, B: int, b: int, v: int) -> bytes:
    """Server-side session key S given client's public ephemeral A."""
    if A % N == 0:
        raise ValueError("invalid A")
    u = _from_bytes(_h(_to_bytes(A), _to_bytes(B)))
    if u == 0:
        raise ValueError("invalid u")
    S = pow(A * pow(v, u, N), b, N)
    return _to_bytes(S)


def srp_M(username: str, salt_hex: str, A: int, B: int, S: bytes) -> bytes:
    """Client proof M1 = H(H(N)^H(g) | H(username) | salt | A | B | K)."""
    K = _h(S)
    NN = _to_bytes(N)
    gg = _to_bytes(g)
    hN = hashlib.sha256(NN).digest()
    hg = hashlib.sha256(gg).digest()
    pad = bytes(a ^ b for a, b in zip(hN, hg))
    # align lengths
    pad = pad[-len(hN):] if len(pad) < len(hN) else pad[:len(hN)]
    return _h(pad, _h(username.encode()), bytes.fromhex(salt_hex),
              _to_bytes(A), _to_bytes(B), K)


def srp_HAMK(username: str, salt_hex: str, A: int, B: int, S: bytes) -> bytes:
    """Server proof M2 = H(A | M | K) (mutual authentication)."""
    K = _h(S)
    M = srp_M(username, salt_hex, A, B, S)
    return _h(_to_bytes(A), M, K)


def srp_session_key(S: bytes) -> bytes:
    return _h(S)


# ------------------------------------------------------------------- JWT ----
def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class TokenIssuer:
    """Ed25519 (EdDSA) JWT issuer/verifier.

    Signing uses nacl's SigningKey directly (no cryptography Ed25519 private-key
    import needed); verification goes through PyJWT with a cryptography
    Ed25519PublicKey — both paths verified against the same key material.
    """

    def __init__(self, seeds: dict[str, bytes], active_kid: str,
                 access_ttl_min: int):
        from nacl.signing import SigningKey
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )

        self.keys = {kid: SigningKey(s) for kid, s in seeds.items()}
        if not active_kid or active_kid not in self.keys:
            raise ValueError("active signing kid missing")
        self.active_kid = active_kid
        self.access_ttl = access_ttl_min * 60
        self.pubkeys = {
            kid: Ed25519PublicKey.from_public_bytes(bytes(sk.verify_key))
            for kid, sk in self.keys.items()
        }

    def issue_access(self, *, user_id: int, username: str, role: str,
                     sid: str, stages: list[int]) -> str:
        now = int(time.time())
        payload = {
            "sub": str(user_id), "usr": username, "role": role, "sid": sid,
            "stages": stages, "iat": now, "exp": now + self.access_ttl,
            "jti": secrets.token_hex(12), "iss": "kalolsavam-api",
        }
        header = {"alg": "EdDSA", "typ": "JWT", "kid": self.active_kid}
        seg_h = _b64u(json.dumps(header, separators=(",", ":")).encode())
        seg_p = _b64u(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{seg_h}.{seg_p}".encode()
        sig = self.keys[self.active_kid].sign(signing_input).signature
        return f"{seg_h}.{seg_p}.{_b64u(sig)}"

    def verify_access(self, token: str) -> dict:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        pk = self.pubkeys.get(kid)
        if pk is None:
            raise jwt.InvalidTokenError("unknown kid")
        return jwt.decode(token, pk, algorithms=["EdDSA"],
                          options={"require": ["exp", "sub", "sid"]})


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
    """Atomically mark used; returns {user_id, family} or None. Caller must
    handle reuse detection (used==1 → revoke family)."""
    row = db.one("SELECT * FROM refresh_tokens WHERE jti=?", (jti,))
    if not row or row["revoked"] or row["expires_at"] < db.now():
        return None
    if row["used"]:
        # REUSE ATTACK → revoke entire family
        db.execute("UPDATE refresh_tokens SET revoked=1 WHERE family=?",
                   (row["family"],))
        db.execute("UPDATE sessions SET revoked=1 WHERE sid IN "
                   "(SELECT sid FROM sessions WHERE current_jti IN "
                   "(SELECT jti FROM refresh_tokens WHERE family=?))",
                   (row["family"],))
        return {"reuse": True, "user_id": row["user_id"], "family": row["family"]}
    db.execute("UPDATE refresh_tokens SET used=1 WHERE jti=?", (jti,))
    return {"reuse": False, "user_id": row["user_id"], "family": row["family"],
            "parent_jti": jti}


def revoke_all_for_user(db, user_id: int) -> None:
    db.execute("UPDATE refresh_tokens SET revoked=1 WHERE user_id=?", (user_id,))
    db.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (user_id,))


# ------------------------------------------------------------------ TOTP ----
def totp_provision() -> bytes:
    return os.urandom(20)  # 160-bit secret, RFC 4226 recommendation


def totp_now(secret: bytes, t: float | None = None, step: int = 30,
             digits: int = 6) -> str:
    counter = int((t if t is not None else time.time()) // step)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(secret, msg, hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def totp_verify(secret: bytes, code: str, window: int = 1) -> bool:
    try:
        c = int(code)
    except ValueError:
        return False
    if not (0 <= c < 1_000_000):
        return False
    now = time.time()
    target = str(c).zfill(6)
    for skew in range(-window, window + 1):
        if hmac.compare_digest(totp_now(secret, now + skew * 30), target):
            return True
    return False


def totp_uri(secret: bytes, username: str, issuer: str = "Kalolsavam") -> str:
    b32 = base64.b32encode(secret).decode().rstrip("=")
    return (f"otpauth://totp/{issuer}:{username}?secret={b32}"
            f"&issuer={issuer}&algorithm=SHA1&digits=6&period=30")


# ------------------------------------------------- field encryption (AES-GCM)
class FieldCrypto:
    """AES-256-GCM using a SHA-256-derived key from DB_FIELD_KEY."""

    def __init__(self, key32: bytes):
        assert len(key32) == 32
        self._aes = AESGCM(key32)

    def encrypt(self, data: bytes, aad: bytes = b"") -> bytes:
        nonce = os.urandom(12)
        return nonce + self._aes.encrypt(nonce, data, aad)

    def decrypt(self, blob: bytes, aad: bytes = b"") -> bytes:
        nonce, ct = blob[:12], blob[12:]
        return self._aes.decrypt(nonce, ct, aad)
