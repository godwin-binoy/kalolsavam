"""Hashing, session IDs, IP hashing, TOTP (all stdlib)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LEN = 32

IP_SALT = secrets.token_bytes(8)


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_LEN,
    )
    return salt.hex(), dk.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    dk = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_LEN,
    )
    return hmac.compare_digest(dk.hex(), (hash_hex or "").lower())


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def hash_ip(ip: str) -> str:
    return hashlib.sha256(IP_SALT + ip.encode("utf-8")).hexdigest()[:16]


def totp_provision() -> bytes:
    return secrets.token_bytes(20)


def totp_now(secret: bytes, t: float | None = None, step: int = 30, digits: int = 6) -> str:
    counter = int((t if t is not None else time.time()) // step)
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def totp_verify(secret: bytes, code: str, window: int = 1) -> bool:
    try:
        c = int(code)
    except (ValueError, TypeError):
        return False
    if not 0 <= c < 1_000_000:
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
