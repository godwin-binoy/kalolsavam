#!/usr/bin/env python3
"""First-run: create the initial admin account.

Generates a random one-time password, prints it ONCE, stores only the SRP
verifier. The admin must log in, enroll TOTP (/api/auth/totp/start), and
rotate the password via manage dashboard immediately.
"""
from __future__ import annotations

import getpass
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.config import Config   # noqa: E402
from server.db import Database     # noqa: E402
from server.auth import srp_make_verifier  # noqa: E402


def main() -> None:
    cfg = Config()
    cfg.ensure_dirs()
    db = Database(cfg.db_path)
    name = sys.argv[1] if len(sys.argv) > 1 else "admin"
    if db.one("SELECT id FROM users WHERE username=?", (name,)):
        raise SystemExit(f"user '{name}' already exists")
    pw = os_pw()
    salt_hex, v_hex = srp_make_verifier(name, pw)
    db.execute(
        "INSERT INTO users(username,role,srp_salt_hex,srp_verifier_hex,stages,"
        "totp_required,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (name, "admin", salt_hex, v_hex, "[]", 1, db.now(), db.now()))
    print("=" * 60)
    print(f"Admin created: {name}")
    print(f"One-time password (print once, deliver securely): {pw}")
    print("Next steps:")
    print(" 1. Log in at https://<host>:<port>/manage/")
    print(" 2. Enroll TOTP when prompted (mandatory for admins)")
    print(" 3. Rotate this password via the dashboard")
    print("=" * 60)


def os_pw() -> str:
    return "Kal-" + secrets.token_urlsafe(12)


if __name__ == "__main__":
    main()
