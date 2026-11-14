"""Participant registry: participants + participant_entries; queue chest_no.

The legacy `participants` table (event-scoped: school/student_name/roll) is
renamed to `_deprecated_participants` per the project retirement pattern.
SQLite 3.25+ propagates the FK rename to `queue_items.participant_id`.

New tables:
  * participants          — one row per student, soft-deletable, 5-digit register
  * participant_entries   — up to 7 rows per student (item/venue/date), soft-deletable

New queue columns:
  * chest_no              — set live by stagemaster at run time
  * participant_entry_id  — modern link; legacy participant_id kept for compat

Revision ID: 0004_participant_registry
Revises: 0003_drop_scores
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_participant_registry"
down_revision = "0003_drop_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "participants" in tables and "_deprecated_participants" not in tables:
        op.rename_table("participants", "_deprecated_participants")

    if "participants" not in tables:
        op.create_table(
            "participants",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("register_no", sa.String(5), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("school_name", sa.String(200), nullable=False),
            sa.Column("school_code", sa.String(6), nullable=False),
            sa.Column("student_class", sa.Integer, nullable=False),
            sa.Column("created_at", sa.Float, nullable=False),
            sa.Column("updated_at", sa.Float, nullable=False),
            sa.Column("deleted_at", sa.Float, nullable=True),
        )
        op.create_index(
            "uq_participants_register_no",
            "participants",
            ["register_no"],
            unique=True,
            sqlite_where=sa.text("deleted_at IS NULL"),
        )
        op.create_index("idx_participants_school_code", "participants", ["school_code"])

    if "participant_entries" not in tables:
        op.create_table(
            "participant_entries",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "participant_id",
                sa.Integer,
                sa.ForeignKey("participants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("item_code", sa.String(32), nullable=False),
            sa.Column("venue_id", sa.Integer, nullable=False),
            sa.Column("venue_name", sa.String(120), nullable=False),
            sa.Column("perf_date", sa.String(10), nullable=False),
            sa.Column("created_at", sa.Float, nullable=False),
            sa.Column("updated_at", sa.Float, nullable=False),
            sa.Column("deleted_at", sa.Float, nullable=True),
        )
        op.create_index(
            "uq_participant_entries_item",
            "participant_entries",
            ["participant_id", "item_code"],
            unique=True,
            sqlite_where=sa.text("deleted_at IS NULL"),
        )
        op.create_index("idx_entries_item", "participant_entries", ["item_code"])
        op.create_index("idx_entries_venue_date", "participant_entries", ["venue_id", "perf_date"])

    insp = sa.inspect(bind)
    if "queue_items" in insp.get_table_names():
        qi_cols = {c["name"] for c in insp.get_columns("queue_items")}
        if "chest_no" not in qi_cols:
            op.add_column("queue_items", sa.Column("chest_no", sa.String(16), nullable=True))
        if "participant_entry_id" not in qi_cols:
            op.add_column(
                "queue_items",
                sa.Column("participant_entry_id", sa.Integer, nullable=True),
            )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    for name in ("participant_entries", "participants"):
        if name in tables:
            op.drop_table(name)
    if "_deprecated_participants" in tables and "participants" not in tables:
        op.rename_table("_deprecated_participants", "participants")
