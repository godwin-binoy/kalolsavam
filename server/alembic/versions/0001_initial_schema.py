"""Unified initial schema (festival + fastapi-fullauth tables in kalolsavam.db).

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel

import server.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Create all SQLModel tables (including fastapi-fullauth User/Role/RefreshToken) if missing
    SQLModel.metadata.create_all(bind, checkfirst=True)

    # If upgrading an existing pre-Alembic kalolsavam.db without venues.slug, add it safely
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
