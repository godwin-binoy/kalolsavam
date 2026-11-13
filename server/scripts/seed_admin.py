"""Seed initial admin into kalolsavam.db. Prints a one-time password."""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.auth import hash_password
from server.config import Settings
from server.db import Database


def main() -> None:
    cfg = Settings()
    db = Database(Path(cfg.db_path))

    email = (sys.argv[1] if len(sys.argv) > 1 else "admin@kalolsavam.example.com").strip().lower()
    if db.one("SELECT id FROM users WHERE email = ?", (email,)):
        raise SystemExit(f"user '{email}' already exists")

    password = secrets.token_urlsafe(16)
    now = db.now()
    with db.transaction():
        db.ex(
            "INSERT INTO users(email, password_hash, role, stages, is_active, created_at, updated_at) "
            "VALUES (?,?,?,?,1,?,?)",
            (email, hash_password(password), "admin", "[]", now, now),
        )

    print("=" * 70)
    print(f"Admin user '{email}' created.")
    print(f"Temporary password: {password}")
    print("Sign in at /admin with your email + password.")
    print("Change the password immediately after first login.")
    print("=" * 70)


if __name__ == "__main__":
    main()
