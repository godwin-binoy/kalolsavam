"""Add direct stagemaster fields to live_state; allow null queue_item_id on photo_batches.

Revision ID: 0007_stagemaster_direct_control
Revises: 0006_simplify_and_harden
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_stagemaster_direct_control"
down_revision = "0006_simplify_and_harden"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "live_state" in tables:
        cols = {c["name"] for c in insp.get_columns("live_state")}
        if "current_item" not in cols:
            op.add_column("live_state", sa.Column("current_item", sa.String(200), nullable=True))
        if "current_chest" not in cols:
            op.add_column("live_state", sa.Column("current_chest", sa.String(32), nullable=True))
        if "upcoming_chests" not in cols:
            op.add_column("live_state", sa.Column("upcoming_chests", sa.String(280), nullable=True))

    if "photo_batches" in tables:
        cols = {c["name"]: c for c in insp.get_columns("photo_batches")}
        qcol = cols.get("queue_item_id")
        if qcol and not qcol.get("nullable", True):
            with op.batch_alter_table("photo_batches") as batch_op:
                batch_op.alter_column("queue_item_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    pass
