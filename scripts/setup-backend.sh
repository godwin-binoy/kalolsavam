#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@kalolsavam.example.com}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN not found. Install Python 3.11+ first."
  exit 1
fi

echo "==> Setting up virtual environment in $VENV_DIR..."
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Installing Python dependencies..."
python -m pip install --upgrade pip >/dev/null
pip install -r requirements-dev.txt

echo "==> Ensuring environment files..."
if [ ! -f "server/.env" ]; then
  cp server/.env.example server/.env
  python - <<'PY_ENV'
import secrets
from pathlib import Path

p = Path("server/.env")
txt = p.read_text(encoding="utf-8")
txt = txt.replace("SECRET_KEY=", f"SECRET_KEY={secrets.token_urlsafe(48)}", 1)
p.write_text(txt, encoding="utf-8")
print("Created server/.env with a generated SECRET_KEY.")
PY_ENV
else
  echo "server/.env already exists (keeping current values)."
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "Created .env from .env.example."
fi

echo "==> Initializing SQLite databases and roles..."
python - <<'PY_INIT'
import asyncio
from pathlib import Path
from sqlmodel import SQLModel, select

from server.auth import Role, User, create_auth
from server.config import Settings
from server.db import Database

cfg = Settings()
Database(Path(cfg.db_path))

async def init_auth():
    _, engine, session_maker = create_auth(cfg)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        async with session_maker() as session:
            for name in ("admin", "stagemaster"):
                existing = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
                if not existing:
                    session.add(Role(name=name))
            await session.commit()
            has_user = (await session.execute(select(User).limit(1))).scalar_one_or_none() is not None
            return has_user
    finally:
        await engine.dispose()

has_user = asyncio.run(init_auth())
print("HAS_USER=" + ("1" if has_user else "0"))
PY_INIT

HAS_EXISTING_USER="$(python - <<'PY_CHK'
import asyncio
from sqlmodel import select
from server.auth import User, create_auth
from server.config import Settings

async def check():
    _, engine, session_maker = create_auth(Settings())
    try:
        async with session_maker() as session:
            return (await session.execute(select(User).limit(1))).scalar_one_or_none() is not None
    finally:
        await engine.dispose()

print("1" if asyncio.run(check()) else "0")
PY_CHK
)"

if [ "$HAS_EXISTING_USER" = "0" ]; then
  echo "==> Seeding initial admin account ($ADMIN_EMAIL)..."
  python -m server.scripts.seed_admin "$ADMIN_EMAIL"
else
  echo "==> Admin/staff user already exists in auth DB; skipping seed_admin."
fi

echo "==> Running backend test suite..."
pytest -q server/tests

echo ""
echo "Backend setup complete!"
echo "Next steps:"
echo "  1. Edit server/.env and set PUBLIC_ORIGIN to your frontend URL (e.g. https://your-site.pages.dev)."
echo "  2. Run locally:        source $VENV_DIR/bin/activate && python -m server"
echo "  3. Or run via Docker:  set CLOUDFLARE_TUNNEL_TOKEN in .env, then run: docker compose up -d --build"
