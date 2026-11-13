"""Retire dead pre-FullAuth tables and the raw-migration bookkeeping table.

`users` / `sessions` came from the old 0003_auth.sql and are referenced by no
code path (auth lives in fullauth_users). They are RENAMED, not dropped, so any
historical rows remain recoverable.

Revision ID: 0002_legacy_cleanup
Revises: 0001_initial
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_legacy_cleanup"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

_RENAMES = (("users", "_deprecated_users"), ("sessions", "_deprecated_sessions"))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    for old, new in _RENAMES:
        if old in tables and new not in tables:
            op.rename_table(old, new)
    if "_meta" in tables:
        op.drop_table("_meta")


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    for old, new in reversed(_RENAMES):
        if new in tables and old not in tables:
            op.rename_table(new, old)
