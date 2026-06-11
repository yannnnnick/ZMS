"""add public map fields and paths

Revision ID: 0005_public_map
Revises: 0004_vet_tasks
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_public_map"
down_revision = "0004_vet_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("enclosures", sa.Column("map_x", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("map_y", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("map_width", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("map_height", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("public_name", sa.String(length=120), nullable=True))
    op.add_column("enclosures", sa.Column("public_description", sa.Text(), nullable=True))
    op.add_column("enclosures", sa.Column("is_public_visible", sa.Boolean(), nullable=False, server_default=sa.text("1")))

    op.create_table(
        "map_paths",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distance_meters", sa.Integer(), nullable=True),
        sa.Column("walking_time_minutes", sa.Integer(), nullable=True),
        sa.Column("path_svg_data", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("map_paths")
    op.drop_column("enclosures", "is_public_visible")
    op.drop_column("enclosures", "public_description")
    op.drop_column("enclosures", "public_name")
    op.drop_column("enclosures", "map_height")
    op.drop_column("enclosures", "map_width")
    op.drop_column("enclosures", "map_y")
    op.drop_column("enclosures", "map_x")
