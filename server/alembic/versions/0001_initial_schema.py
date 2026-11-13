"""Unified initial schema (festival + fastapi-fullauth tables).

Idempotent against pre-Alembic databases created by the old raw-SQL bootstrap.

Revision ID: 0001_initial
Revises:
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlmodel import SQLModel

import server.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    SQLModel.metadata.create_all(bind, checkfirst=True)

    # Inspect AFTER create_all so the reflection cache is not stale.
    insp = sa.inspect(bind)
    if insp.has_table("venues"):
        cols = {c["name"] for c in insp.get_columns("venues")}
        if "slug" not in cols:
            op.add_column("venues", sa.Column("slug", sa.String(length=64), nullable=True))
        idxs = {i["name"] for i in insp.get_indexes("venues")}
        if "idx_venues_slug" not in idxs:
            op.create_index(
                "idx_venues_slug",
                "venues",
                ["slug"],
                unique=True,
                sqlite_where=sa.text("slug IS NOT NULL"),
            )


def downgrade() -> None:
    pass
