"""Create the first admin account + seed venues/categories. Prints a one-time password."""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.config import Settings
from server.db import Database
from server.security import hash_password


def main() -> None:
    cfg = Settings()
    db = Database(Path(cfg.db_path))

    username = (sys.argv[1] if len(sys.argv) > 1 else "admin").lower()

    if db.one("SELECT id FROM users WHERE username = ?", (username,)):
        raise SystemExit(f"user '{username}' already exists — refusing to overwrite")

    if db.one("SELECT id FROM users LIMIT 1"):
        raise SystemExit("users already exist — create additional admins from the /admin UI")

    if not db.one("SELECT id FROM venues LIMIT 1"):
        for name in ("Stage 1 - Main Hall", "Stage 2 - Open Air",
                     "Stage 3 - Dining Hall", "Stage 4 - Annex Hall"):
            db.ex("INSERT INTO venues(name, kind, active) VALUES (?, 'stage', 1)", (name,))

    if not db.one("SELECT id FROM categories LIMIT 1"):
        for name, grp in [("HS General", "HS"), ("HSS General", "HSS"),
                          ("HS Arabic", "HS"), ("HS Sanskrit", "HS")]:
            db.ex("INSERT INTO categories(name, grp) VALUES (?,?)", (name, grp))

    password = secrets.token_urlsafe(16)
    salt, phash = hash_password(password)
    db.ex(
        "INSERT INTO users(username, role, pwd_salt, pwd_hash, totp_required, "
        " stages, created_at, updated_at) "
        "VALUES (?, 'admin', ?, ?, 1, '[]', ?, ?)",
        (username, salt, phash, db.now(), db.now()),
    )

    print("=" * 70)
    print(f"Admin user '{username}' created.")
    print(f"Temporary password: {password}")
    print()
    print("Next steps:")
    print("  1. python -m server")
    print("  2. Open http://127.0.0.1:8000/admin in a browser")
    print("  3. Sign in with the password above (TOTP setup will be prompted)")
    print("  4. Change the password immediately after enrolling TOTP")
    print("=" * 70)


if __name__ == "__main__":
    main()
