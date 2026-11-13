#!/usr/bin/env bash
set -euo pipefail

log() { echo "[entrypoint] $*"; }

log "Kalolsavam backend starting..."

DB_DIR="$(dirname "${DB_PATH:-/app/deployment/kalolsavam.db}")"
mkdir -p "$DB_DIR"

log "Applying database migrations..."
python -m server migrate

if [ -n "${ADMIN_EMAIL:-}" ]; then
  log "Seeding admin user: $ADMIN_EMAIL"
  if [ -n "${ADMIN_PASSWORD:-}" ]; then
    python -m server seed-admin --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD"
  else
    python -m server seed-admin --email "$ADMIN_EMAIL"
  fi
else
  log "ADMIN_EMAIL not set - skipping admin seed."
fi

log "Seeding stages..."
python -m server seed-stages

log "Launching server on ${SERVER_HOST:-0.0.0.0}:${SERVER_PORT:-8000}"
exec python -m server serve --host "${SERVER_HOST:-0.0.0.0}" --port "${SERVER_PORT:-8000}"
