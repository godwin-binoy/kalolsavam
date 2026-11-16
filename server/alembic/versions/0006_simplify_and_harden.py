"""Decouple photo worker processing from human batch status; add perf_date.

Revision ID: 0006_simplify_and_harden
Revises: 0005_core_photos
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_simplify_and_harden"
down_revision = "0005_core_photos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "photo_batches" in tables:
        cols = {c["name"] for c in insp.get_columns("photo_batches")}
        if "perf_date" not in cols:
            op.add_column("photo_batches", sa.Column("perf_date", sa.String(10), nullable=True))

    if "photo_assets" in tables:
        cols = {c["name"] for c in insp.get_columns("photo_assets")}
        if "processed" not in cols:
            op.add_column(
                "photo_assets",
                sa.Column("processed", sa.Integer, nullable=False, server_default="0"),
            )
        if "processed_at" not in cols:
            op.add_column("photo_assets", sa.Column("processed_at", sa.Float, nullable=True))
        idxs = {i["name"] for i in insp.get_indexes("photo_assets")}
        if "idx_photo_assets_processed" not in idxs:
            op.create_index("idx_photo_assets_processed", "photo_assets", ["processed", "kind"])


def downgrade() -> None:
    pass
