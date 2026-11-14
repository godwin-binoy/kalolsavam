"""Drop the scores table (results tracking retired).

Revision ID: 0003_drop_scores
Revises: 0002_legacy_cleanup

Results are published exclusively by the official government portal. This
removes the scores table and the storage of any judged values. Downgrade
recreates an empty table for schema validity; historical rows are gone.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_drop_scores"
down_revision = "0002_legacy_cleanup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "scores" in insp.get_table_names():
        op.drop_table("scores")


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "scores" in insp.get_table_names():
        return
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "queue_item_id",
            sa.Integer,
            sa.ForeignKey("queue_items.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("judge_no", sa.Integer, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("entered_by", sa.String, nullable=False),
        sa.Column("entered_at", sa.Float, nullable=False),
        sa.UniqueConstraint("queue_item_id", "judge_no", name="uq_scores_item_judge"),
    )
