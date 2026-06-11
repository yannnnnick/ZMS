"""add animal and enclosure assignments

Revision ID: 0002_assignments
Revises: 0001_initial
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_assignments"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    assignment_role_type = sa.Enum("keeper", "vet", name="assignmentroletype")
    op.create_table(
        "animal_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_type", assignment_role_type, nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_animal_assignments_user", "animal_assignments", ["user_id", "active"])
    op.create_index("ix_animal_assignments_animal", "animal_assignments", ["animal_id", "active"])

    op.create_table(
        "enclosure_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_enclosure_assignments_user", "enclosure_assignments", ["user_id", "active"])


def downgrade() -> None:
    op.drop_index("ix_enclosure_assignments_user", table_name="enclosure_assignments")
    op.drop_table("enclosure_assignments")
    op.drop_index("ix_animal_assignments_animal", table_name="animal_assignments")
    op.drop_index("ix_animal_assignments_user", table_name="animal_assignments")
    op.drop_table("animal_assignments")
