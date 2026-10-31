# Backend Server — `server/`

On-premise backend for the Mala Kalolsavam, published to the internet through
a **Cloudflare Tunnel** (the venue ISP is unreliable; cloudflared connects out
to Cloudflare, TLS ends at CF's edge). No port-forwarding, no local CA, no
certificates on our machines. There is **no LAN access**: everything — public
APIs and staff dashboards — arrives from the WAN through the tunnel.

## What it hosts

1. **Public API** (`/api/public/*`) — sanitized live status + SSE for the
   festival website. No auth (cacheable), rate-limited per real visitor IP
   (`CF-Connecting-IP`).
2. **Stagemaster API** (`/api/live/*`) — run-of-show control. Requires a
   `role=stagemaster` session (password login → short-lived HS256 JWT).
3. **Admin API** (`/api/admin/*`) — master data, users, sessions, audit.
   Requires `role=admin` + **mandatory TOTP** (+ step-up TOTP on destructive
   actions).
4. **Dashboards** — `server/stagemaster/` and `server/admin/` are served as
   plain static files at `/stagemaster` and `/admin`. Anyone can load them,
   but they are inert shells: unlinked from the public site, disallowed in
   robots.txt, and every piece of data behind a login. Security comes from
   the APIs, not from hiding the pages.
5. **Results are not hosted here** — the site links out to the government
   URL (`RESULTS_REDIRECT_URL`).

Login is one simple step: `POST /api/auth/login {username, password, totp?}`
→ PBKDF2 hash check → 15-min JWT (memory-only) + rotating HttpOnly refresh
cookie. Full rationale in `docs/SECURITY.md`.

## Layout
```
server/
  app.py              # FastAPI factory + middleware (headers, CSRF, rate-limit)
  auth.py             # PBKDF2 hashing, HS256 JWT, refresh rotation, TOTP
  db.py               # SQLite (WAL) layer + schema — '?' placeholders only
  routes_public.py    # /api/public/*
  routes_auth.py      # /api/auth/*        (login, refresh, logout, TOTP enroll)
  routes_live.py      # /api/live/*        (stagemaster)
  routes_admin.py     # /api/admin/*       (admin console)
  stagemaster/        # staff dashboard (static SPA, served at /stagemaster)
  admin/              # admin dashboard  (static SPA, served at /admin)
  static/gate.html    # neutral landing page at /
  scripts/
    run.py            # uvicorn on 127.0.0.1 (the tunnel connects locally)
    bootstrap_admin.py# first-run admin (random one-time password)
    backup.py         # snapshot DB to server/backups/ (rotating)
    seed.py           # demo/master data seeding
.env.example          # template ONLY — real values go in untracked .env
```

## Quick start (dev)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r server/requirements.txt
cp server/.env.example server/.env         # then set SESSION_SIGNING_SEEDS:
python -c "import secrets; print('k1:'+secrets.token_hex(32))"   # paste into .env
python -m server.scripts.bootstrap_admin   # prints a one-time admin password
python -m server.scripts.run --dev         # http://127.0.0.1:8000
```

## Production (behind Cloudflare Tunnel)
```bash
ENVIRONMENT=production python -m server.scripts.run &
cloudflared tunnel --url http://127.0.0.1:8000   # or a named/configured tunnel
```
- Keep `SERVER_HOST=127.0.0.1`; startup refuses a non-loopback bind without
  `FORCE_TLS`, and refuses `TRUST_PROXY=0` in production.
- In the Cloudflare dashboard: enable "Always Use HTTPS" + HSTS. Optionally
  add a Cloudflare Access policy in front of `/admin` and `/stagemaster`.
- Staff open `https://<your-domain>/admin/` and `/stagemaster/` directly —
  nothing on the public site links to them.
