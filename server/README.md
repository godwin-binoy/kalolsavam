# Backend Server — `server/`

On-premise backend for the Mala Kalolsavam festival. Hosts:

1. **Public API** (`/api/public/*`) — sanitized live status snapshots + SSE,
   consumed by the public website. No auth required (cacheable).
2. **Stagemaster API** (`/api/live/*`) — run-of-show control, score entry.
   Requires `role=stagemaster` session.
3. **Manage API** (`/api/admin/*`) — master data CRUD, users, backups, deploy.
   Requires `role=admin` session (+ TOTP).
4. **Dashboard static hosting** — serves `stagemaster/` and `manage/` HTML
   over HTTPS on the venue LAN only. These routes are *not* linked from the
   public site and always demand authentication at the application layer.

## Security model (summary — full spec in `docs/SECURITY.md`)
- SRP challenge–response login (password never crosses the wire) → Argon2id
  verifiers server-side → short-lived Ed25519 JWT access tokens (memory-only)
  + rotating single-use refresh tokens (HttpOnly/SameSite=Strict cookie).
- Mandatory TOTP for admins; per-account lockout + per-IP rate limits.
- TLS with locally generated CA; strict CSP/no-store headers on dashboards.
- `.env` (signing seeds, DB key) is gitignored; a pre-commit secret scan guards it.

## Layout
```
server/
  app.py              # FastAPI application factory + middleware (headers, CSRF, rate-limit)
  auth.py             # SRP-6a, JWT issue/verify, refresh rotation, TOTP
  db.py               # SQLite (WAL) access layer
  models.py           # schema + migrations
  routes_public.py    # /api/public/*
  routes_live.py      # /api/live/*        (stagemaster)
  routes_admin.py     # /api/admin/*       (manage)
  scripts/
    run.py            # host script: uvicorn w/ TLS, LAN bind
    bootstrap_admin.py# first-run admin creation (random one-time password)
    init_tls.py       # local CA + server cert generation
    backup.py         # snapshot DB to server/backups/ (rotating)
    seed.py           # demo/master data seeding
  .env.example        # template ONLY — real values go in untracked .env
```

## Quick start (dev)
```bash
python -m venv .venv && . .venv/bin/activate
pip install fastapi "uvicorn[standard]" argon2-cffi pyjwt pynacl cryptography qrcode
cp server/.env.example server/.env   # then EDIT — never commit
python -m server.scripts.init_tls
python -m server.scripts.bootstrap_admin
python -m server.scripts.run
```

## Production hosting (venue)
- Bind `--host <LAN_IP>` (never `0.0.0.0` unless behind the reverse proxy with
  firewall rules below).
- Firewall: allow 443 from WAN **only** for `/api/public/*` via proxy path
  filtering; dashboard + admin paths restricted to staff VLAN.
- systemd unit example in `scripts/` (see `festival-server.service`).
