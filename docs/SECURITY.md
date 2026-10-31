# Security — how this system defends itself

One page, plain words. The rule we follow: **simple mechanisms, correctly
implemented, beat clever ones nobody can maintain.**

## Deployment reality (read this first)

The venue internet is unreliable, so everything — public site APIs and staff
dashboards alike — is published through a single **Cloudflare Tunnel**.
`cloudflared` runs on the staff PC and connects *out* to Cloudflare; visitors
reach us over HTTPS at Cloudflare's edge. There is **no LAN access**, no
port-forwarding, and **no local CA or certificates** on our machines.

Consequences we design around:

- The server binds `127.0.0.1` only; the tunnel is the sole ingress.
- Every request arrives from localhost, so socket-IP allowlists are useless.
  The real visitor IP comes from `CF-Connecting-IP` (trusted only because
  `TRUST_PROXY=1` and the tunnel is the only way in). Rate limits key on it.
- TLS/HSTS are configured in the Cloudflare dashboard, not here.
- The dashboard URLs (`/admin`, `/stagemaster`) are treated as **known to
  attackers**. They are served publicly but unlinked from the festival site
  and disallowed in robots.txt — they are inert shells. All protection lives
  in the APIs behind them.

## Login & sessions (kept deliberately simple)

- **One endpoint**: `POST /api/auth/login {username, password, totp?}`.
- Passwords are hashed with **PBKDF2-HMAC-SHA256, 240k iterations, per-user
  random salt**. Only the hash is stored — never the password. In transit the
  password is protected by ordinary HTTPS (terminated at Cloudflare).
- **Access token**: short-lived (15 min) HMAC-signed JWT (HS256), kept in
  browser memory only — never localStorage. Algorithm is pinned; signatures
  are compared in constant time.
- **Refresh token**: single-use random string in an `HttpOnly + Secure +
  SameSite=Strict` cookie scoped to `/api/auth`. Rotated on every refresh;
  replaying an old one revokes the whole token family (stolen-token detection).
- Sessions idle-lock after 30 min; logout revokes server-side; admins can
  force-revoke any session.
- **TOTP (RFC 6238)** second factor, mandatory for admins, enrolled via a
  first-run wizard. Secrets live in the DB file, protected by OS permissions.

## Brute force & enumeration

- Per-visitor-IP token bucket: `/api/auth/*` 10/min, other APIs 120/min.
- Per-account escalating lockout (1 → 5 → 15 min) after failed logins.
- Unknown user and wrong password return the **same** generic error, so
  usernames cannot be enumerated.

## CSRF, XSS, clickjacking

- **CSRF**: double-submit check (`kal_csrf` cookie must match the
  `X-CSRF-Token` header) on every cookie-driven auth mutation. Login is
  exempt (it runs before cookies exist and is covered by rate limits).
- **XSS**: dashboards use strict CSP (`default-src 'self'`, no inline
  scripts), all DOM updates go through `textContent` (never `innerHTML` with
  server data), and tokens are never in storage an injected script can read.
- **Clickjacking**: `X-Frame-Options: DENY` + `frame-ancestors 'none'`.
- Also always set: `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  no-referrer`, COOP/CORP same-origin. API docs/OpenAPI are disabled.

## SQL injection — impossible by construction

Every database statement in the project is a **fixed string with `?`
placeholders and a params tuple** (see `db.py`). No user input is ever
concatenated into SQL. On top of that: SQLite foreign keys are ON, CHECK
constraints guard enums (roles, queue statuses), and Pydantic validates and
length-bounds every request body before it reaches the query layer.

## Authorization

| Role | Scope | Guards |
|---|---|---|
| anonymous | `GET /api/public/*` | read-only, sanitized fields only, rate-limited |
| stagemaster | assigned stages | login + role check + stage ownership on every mutation |
| admin | everything | login + **mandatory TOTP** + `x-step-up-totp` re-verification on destructive actions |

Writes carry optimistic-concurrency versions (conflicts are rejected, not
silently overwritten) and idempotency keys where retries matter.

## Data we deliberately do NOT hold

Results are **not hosted here**. The public site's "Results" links redirect
to the official government URL (`RESULTS_REDIRECT_URL`, restricted to an
allowlisted domain when edited by admins). Fewer sensitive data = smaller
blast radius.

## Audit & integrity

- Append-only `auth_audit` table: logins, failures, lockouts, TOTP misses,
  refresh reuse — visible in the admin dashboard.
- Hash-linked `audit_chain` for admin actions (each row embeds the previous
  row's SHA-256, so tampering is detectable; verify with
  `Database.verify_chain()`).

## Secrets handling

- `.env` holds exactly one secret: `SESSION_SIGNING_SEEDS` (one 32-byte hex
  key is enough; rotate by adding a new kid in front — old tokens die in
  15 min). It is gitignored and must never be committed.
- Production startup **refuses to boot** unless the bind is loopback without
  `FORCE_TLS` and `TRUST_PROXY=1` (see `config.validate()`).
- The DB file relies on OS file permissions (not encryption) — losing a key
  can never lock us out of our own festival data.

## Small dependency surface

Three Python packages (`fastapi`, `uvicorn`, `pydantic`); hashing, JWT
signing, TOTP and TLS all come from the standard library. Fewer third-party
libraries means fewer supply-chain risks and easier installs on venue laptops.

## Nice-to-have extra (optional)

Cloudflare Access can put an additional edge-layer gate (e.g. email OTP) in
front of `/admin` and `/stagemaster`. It costs nothing and shrinks the bot
surface further, but the app's own auth above is what we actually rely on.
