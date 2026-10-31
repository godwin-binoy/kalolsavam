# Security Architecture — Staff Dashboards & APIs

## Deployment reality (read this first)

The venue's internet is unreliable, so the whole backend is published through a
**Cloudflare Tunnel** (`cloudflared` runs on the staff PC, connects out to
Cloudflare; visitors reach it over HTTPS at CF's edge). Consequences:

- **There is no LAN access.** Public *and* private APIs are reached from the
  WAN only. Nothing is bound to a venue IP; the server listens on
  `127.0.0.1` and only cloudflared talks to it locally.
- **No local CA / certificates.** TLS terminates at Cloudflare. HSTS, cipher
  policy, and mTLS-to-CF are configured in the Cloudflare dashboard, not here.
- Every request's socket peer is `127.0.0.1`, so **IP-based network gating is
  meaningless** as a security boundary. The real visitor IP comes from
  `CF-Connecting-IP` (trusted only because `TRUST_PROXY=1` and the tunnel is
  the sole ingress).
- The repo is public, so `/stagemaster` and `/admin` paths are treated as
  **known to attackers**. They are served publicly (plain static HTML/CSS/JS,
  unlinked from the festival site and disallowed in robots.txt) but are inert
  shells — all protection lives in the APIs behind them.

## Authentication: password never crosses the wire

- **SRP-6a challenge–response** login (`/api/auth/challenge` → `/verify`):
  the client derives the shared secret locally and sends only a proof `M1`;
  the server replies with `M2` (mutual auth). Argon2id verifiers are stored
  server-side — never plaintext or bare hashes.
- On success the server issues:
  - **Access token**: Ed25519 JWT, 15-min lifetime, carries
    `role: stagemaster|admin`, `sid`, `jti`. Kept **in memory only** (never
    localStorage) — CSP forbids inline scripts to shrink XSS theft surface.
  - **Refresh token**: single-use, 8-h absolute expiry, rotated on every use;
    replay of a rotated token revokes the whole token family. Delivered as an
    `HttpOnly + Secure + SameSite=Strict` cookie scoped to `/api/auth/*`.
- Session policy: 30-min idle lock, 8-h absolute cap; logout revokes the
  refresh family server-side; admin can force-revoke any session.

## Authorization & second factors

| Role | Scope | Guards |
|---|---|---|
| anonymous | `GET /api/public/*` snapshots/SSE | read-only, sanitized, rate-limited per visitor IP |
| `stagemaster` | assigned stages | SRP login (+ optional TOTP), role check + resource ownership on every mutation |
| `admin` | everything | SRP login + **mandatory TOTP**, plus `x-step-up-totp` re-verification on destructive actions (user delete, revoke-all, backup, deploy, flag writes) |

TOTP (RFC 6238, ±1 window, single-use per time step) is enrolled via QR after
first login; secrets are stored in the DB file, which is protected by OS
permissions (no field encryption any more).

## Anti-abuse (the primary controls now that IPs gate nothing)

- Per-real-IP token-bucket limits: `/api/auth/*` 10/min, other APIs 120/min.
- Per-account exponential lockout (1m → 5m → 15m) on failed logins; uniform
  fake responses prevent username enumeration.
- CSRF double-submit (`kal_csrf` cookie + `X-CSRF-Token` header) on all
  cookie-driven auth mutations; SRP challenge/verify are exempt (they run
  before cookies exist and are covered by the limits above).
- Append-only `auth_audit` table (login success/fail, TOTP fail, refresh
  reuse, lockouts) viewable in the admin dashboard.
- Optional `ADMIN_IP_ALLOWLIST` (CIDRs matched against the **real** visitor
  IP) if you want to pin `/api/admin/*` to known static IPs. Empty by default
  — do not add LAN ranges; they cannot work through the tunnel.

## Transport & headers

- Cloudflare edge: enable "Always Use HTTPS" and set HSTS there.
- Response headers from the app on every API/dashboard response:
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, COOP/CORP same-origin, and on dashboard
  pages `Content-Security-Policy: default-src 'self'; … frame-ancestors
  'none'` plus `Cache-Control: no-store` on authenticated responses.
- Results are **not hosted here**: the public site redirects "Results" links
  to the government URL (`RESULTS_REDIRECT_URL`, domain-allowlisted by the
  admin endpoint that edits it). No result data enters our database.

## Secrets & config handling

- `.env` holds `SESSION_SIGNING_SEEDS` (Ed25519 kid:seed pairs; rotate by
  adding a kid, invalidate old tokens by removing it). It is gitignored and
  must never be committed.
- First-run bootstrap: `python -m server.scripts.bootstrap_admin` creates the
  admin with a random one-time password and forces TOTP enrollment on first
  login.
- Production startup refuses to boot unless the server binds loopback without
  `FORCE_TLS`, and unless `TRUST_PROXY=1` (see `config.validate()`).

## What the public site sees

Only `GET /api/public/*` — pre-rendered, cached, sanitized snapshots and SSE
produced from live data. No PII, no drafts, no internal IDs beyond what is
intentionally published. Dashboard HTML is reachable by URL but contains no
data until a staff member authenticates against the guarded APIs.
