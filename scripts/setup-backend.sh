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

echo "==> Initializing SQLite database..."
HAS_EXISTING_USER="$(python - <<'PY_INIT'
from pathlib import Path
from server.config import Settings
from server.db import Database

cfg = Settings()
db = Database(Path(cfg.db_path))
has_user = db.one("SELECT id FROM users LIMIT 1") is not None
print("1" if has_user else "0")
PY_INIT
)"

if [ "$HAS_EXISTING_USER" = "0" ]; then
  echo "==> Seeding initial admin account ($ADMIN_EMAIL)..."
  python -m server.scripts.seed_admin "$ADMIN_EMAIL"
else
  echo "==> Admin/staff user already exists in DB; skipping seed_admin."
fi

echo "==> Running backend test suite..."
pytest -q server/tests

echo ""
echo "Backend setup complete!"
echo "Next steps:"
echo "  1. Verify server/.env PUBLIC_ORIGIN=https://mala-subdistrict-kalolsavam.pages.dev."
echo "  2. Run locally:        source $VENV_DIR/bin/activate && python -m server"
echo "  3. Or run via Docker:  set CLOUDFLARE_TUNNEL_TOKEN in .env, then run: docker compose up -d --build"
