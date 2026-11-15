"""Add photo tables to core DB (moved from separate Photo server).

Revision ID: 0005_core_photos
Revises: 0004_participant_registry
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0005_core_photos"
down_revision = "0004_participant_registry"

def upgrade() -> None:
    op.create_table(
        "photo_batches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("queue_item_id", sa.Integer, nullable=False),
        sa.Column("venue_id", sa.Integer, nullable=False),
        sa.Column("workflow", sa.String, nullable=False),
        sa.Column("status", sa.String, default="queued"),
        sa.Column("created_at", sa.Float, nullable=False)
    )
    op.create_table(
        "photo_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("batch_id", sa.Integer, sa.ForeignKey("photo_batches.id"), nullable=False),
        sa.Column("kind", sa.String, nullable=False),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("uploaded_at", sa.Float, nullable=False)
    )
    op.create_table(
        "photo_asset_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("photo_asset_id", sa.Integer, sa.ForeignKey("photo_assets.id"), nullable=False),
        sa.Column("participant_entry_id", sa.Integer, nullable=False),
        sa.Column("source", sa.String, nullable=False)
    )

def downgrade() -> None:
    op.drop_table("photo_asset_entries")
    op.drop_table("photo_assets")
    op.drop_table("photo_batches")
