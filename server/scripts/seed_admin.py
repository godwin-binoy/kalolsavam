"""Seed FullAuth roles + first admin. Prints a one-time password."""
from __future__ import annotations

import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from argon2 import PasswordHasher
from sqlmodel import SQLModel, select

from server.auth import Role, User, create_auth
from server.config import Settings


async def main() -> None:
    cfg = Settings()
    _, engine, session_maker = create_auth(cfg)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with session_maker() as session:
        for name in ("admin", "stagemaster"):
            existing = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
            if not existing:
                session.add(Role(name=name))
        await session.commit()

        email = (sys.argv[1] if len(sys.argv) > 1 else "admin@kalolsavam.example.com").lower()
        existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            raise SystemExit(f"user '{email}' already exists")

        password = secrets.token_urlsafe(16)
        role = (await session.execute(select(Role).where(Role.name == "admin"))).scalar_one()
        u = User(
            email=email,
            hashed_password=PasswordHasher().hash(password),
            is_active=True, is_verified=True, stages="[]",
        )
        u.roles.append(role)
        session.add(u)
        await session.commit()

    print("=" * 70)
    print(f"Admin user '{email}' created.")
    print(f"Temporary password: {password}")
    print("Sign in at /admin with your email + password.")
    print("Change the password immediately after first login.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
