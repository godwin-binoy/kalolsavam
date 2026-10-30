# Manage Dashboard — `manage/`

Server maintenance & development interface for administrators. **Never linked
from the public site**; served only by the on-premise server over HTTPS on the
staff VLAN; every route requires `role=admin` + **mandatory TOTP**.

## Purpose
- **Master data CRUD**: venues, stages, categories, events, participants.
- **CSV import/export** with dry-run preview before commit.
- **Users & sessions**: create/disable stagemaster accounts, force-revoke
  sessions, view auth audit log.
- **Server health**: CPU/disk/DB size, SSE connection count, error tail.
- **Operations**: trigger DB backup, rotate keys, rebuild + deploy the public
  site snapshot, feature flags (e.g., "results publishing open").

## Security posture (see `docs/SECURITY.md`)
- Same SRP + JWT + rotating refresh-token model as stagemaster, stricter role.
- Destructive actions (delete user, revoke all sessions, deploy) require a
  second TOTP code at action time ("step-up auth").
- All admin actions appended to an immutable audit table with actor, target,
  before/after hash chain.
- IP allowlist enforced at middleware for `/api/admin/*` (staff VLAN only).

## Planned layout
```
manage/
  index.html        # login + TOTP shell
  app.html          # tabbed dashboard
  js/auth.js        # SRP client + TOTP step-up
  js/api.js
  js/data.js        # master-data tables
  js/ops.js         # health, backups, deploy
  css/dashboard.css
```

## Status
Planning phase — no code yet. API contract lives in `server/README.md`.
