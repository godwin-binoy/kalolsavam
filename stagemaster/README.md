# Stagemaster Dashboard — `stagemaster/`

Live run-of-show control for stage managers. **Never linked from the public
site**; served only by the on-premise server over HTTPS on the staff VLAN, and
every route requires an authenticated `role=stagemaster` session.

## Purpose
- See the current queue for your assigned stage(s).
- Control state: `WAITING → ON-STAGE → COMPLETE` (+ pause / skip / recall).
- Enter judge scores; publish results when ready.
- Push live updates to the public website via the server (SSE fan-out).

## Security posture (see `docs/SECURITY.md`)
- Login: SRP challenge–response (password never leaves the device) + optional TOTP.
- Access token held **in memory only**; refresh via HttpOnly cookie; 30-min idle lock.
- Strict CSP, `no-store`, `frame-ancestors 'none'`; all JS in external files.
- Writes are scoped server-side to stages assigned to the logged-in user.
- Offline buffering: mutations while disconnected queue in IndexedDB and flush
  on reconnect with optimistic-concurrency version checks (409 → refetch).

## Planned layout
```
stagemaster/
  index.html        # login shell (no inline scripts)
  app.html          # dashboard (post-auth)
  js/auth.js        # SRP client, token lifecycle, lock overlay
  js/api.js         # fetch wrapper w/ auto-refresh + CSRF header
  js/live.js        # SSE client + optimistic UI
  js/queue.js       # run-of-show board
  css/dashboard.css
```

## Status
Planning phase — no code yet. API contract lives in `server/README.md`.
