# Backend Server — `server/`

On-premise backend for the Mala Kalolsavam festival, published to the internet
through a **Cloudflare Tunnel** (unreliable venue ISP → cloudflared connects
out; no port-forwarding, no local CA/certs — TLS ends at Cloudflare's edge).
There is **no LAN access**: all traffic, public and staff, arrives from the WAN.

Hosts:

1. **Public API** (`/api/public/*`) — sanitized live status snapshots + SSE,
   consumed by the public website. No auth required (cacheable), rate-limited
   per real visitor IP (`CF-Connecting-IP`).
2. **Stagemaster API** (`/api/live/*`) — run-of-show control, score entry.
   Requires `role=stagemaster` session (SRP login → short-lived Ed25519 JWT).
3. **Admin API** (`/api/admin/*`) — master data CRUD, users, sessions, backups.
   Requires `role=admin` session + mandatory TOTP (+ step-up TOTP on
   destructive actions). Optional `ADMIN_IP_ALLOWLIST` pins it to known static
   *WAN* IPs (matched against the real visitor IP, never the tunnel peer).
4. **Dashboard static hosting** — serves `server/stagemaster/` and
   `server/admin/` as plain static files. They are reachable by anyone who
   types the URL (deliberately unlinked from the public site and disallowed in
   robots.txt) but are inert shells: security comes entirely from the guarded
   APIs behind them.
5. **Results** are not hosted here — links redirect to the government site
   (`RESULTS_REDIRECT_URL`, domain-allowlisted).

## Security model (summary — full spec in `docs/SECURITY.md`)
- SRP-6a challenge–response login (password never crosses the wire) → Argon2id
  verifiers → Ed25519 JWT access tokens (memory-only) + rotating single-use
  refresh tokens (HttpOnly/SameSite=Strict cookie).
- Mandatory TOTP for admins; per-account lockout + per-real-IP rate limits.
  Network-level gating is gone — behind the tunnel every socket peer is
  localhost, so auth + anti-abuse are the only meaningful controls.
- Strict CSP/no-store headers on dashboards; CSRF double-submit on cookie
  auth mutations.
- `.env` (signing seeds) is gitignored; the DB file is protected by OS
  permissions (not encrypted).

## Layout
```
server/
  app.py              # FastAPI factory + middleware (headers, CSRF, rate-limit)
  auth.py             # SRP-6a, JWT issue/verify, refresh rotation, TOTP
  db.py               # SQLite (WAL) access layer + schema
  routes_public.py    # /api/public/*
  routes_auth.py      # /api/auth/*        (login, refresh, TOTP enroll)
  routes_live.py      # /api/live/*        (stagemaster)
  routes_admin.py     # /api/admin/*       (admin console)
  stagemaster/        # staff dashboard (static SPA, served at /stagemaster)
  admin/              # admin dashboard  (static SPA, served at /admin)
  static/gate.html    # neutral landing page at /
  scripts/
    run.py            # host script: uvicorn on 127.0.0.1 (tunnel connects locally)
    bootstrap_admin.py# first-run admin creation (random one-time password)
    backup.py         # snapshot DB to server/backups/ (rotating)
    seed.py           # demo/master data seeding
.env.example          # template ONLY — real values go in untracked .env
```

## Quick start (dev)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r server/requirements.txt
cp .env.example .env                 # then EDIT — never commit
python -m server.scripts.bootstrap_admin
python -m server.scripts.run --dev   # http://127.0.0.1:8000
```

## Production hosting (behind Cloudflare Tunnel)
```bash
# on the staff PC, once the tunnel is created in the CF Zero Trust dashboard:
cloudflared tunnel --url http://127.0.0.1:8443   # quick tunnel, or
cloudflared ingress-dns / configured tunnel with ingress rules for your domain
ENVIRONMENT=production python -m server.scripts.run
```
- Keep `SERVER_HOST=127.0.0.1` — startup refuses a non-loopback bind without
  `FORCE_TLS`, and refuses `TRUST_PROXY=0` in production.
- In Cloudflare: enable "Always Use HTTPS" + HSTS; add Access policies if you
  want an extra edge-layer gate in front of `/admin` and `/stagemaster`.
- Public website (GitHub Pages) calls these APIs over HTTPS via your tunnel
  hostname; nothing else needs to be exposed.
