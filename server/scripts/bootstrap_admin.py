#!/usr/bin/env python3
"""First-run: create the initial admin account.

Generates a random one-time password, prints it ONCE, and stores only its
PBKDF2 hash (never the password itself). The admin logs in at /admin/,
enrolls TOTP when prompted (mandatory for admins), and rotates the password
from the dashboard immediately.

Usage:  python -m server.scripts.bootstrap_admin [username]
"""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.config import Config            # noqa: E402
from server.db import Database              # noqa: E402
from server.auth import make_password_hash  # noqa: E402


def main() -> None:
    cfg = Config()
    cfg.ensure_dirs()
    db = Database(cfg.db_path)
    name = (sys.argv[1] if len(sys.argv) > 1 else "admin").lower()
    if db.one("SELECT id FROM users WHERE username=?", (name,)):
        raise SystemExit(f"user '{name}' already exists")
    pw = "Kal-" + secrets.token_urlsafe(12)
    salt_hex, hash_hex = make_password_hash(pw)
    db.execute(
        "INSERT INTO users(username,role,pwd_salt_hex,pwd_hash_hex,stages,"
        "totp_required,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (name, "admin", salt_hex, hash_hex, "[]", 1, db.now(), db.now()))
    dash = "/admin" + cfg.dash_suffix
    print("=" * 60)
    print(f"Admin created: {name}")
    print(f"One-time password (print once, deliver securely): {pw}")
    print("Next steps:")
    print(f" 1. Open https://<your-domain>{dash}/ and sign in")
    print(" 2. Enroll TOTP when prompted (mandatory for admins)")
    print(" 3. Change this password from the dashboard")
    print("=" * 60)


if __name__ == "__main__":
    main()
