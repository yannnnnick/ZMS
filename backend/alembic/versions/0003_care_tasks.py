"""add care tasks and animal condition reports

Revision ID: 0003_care_tasks
Revises: 0002_assignments
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_care_tasks"
down_revision = "0002_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    care_task_type = sa.Enum("feeding", "cleaning", "health_check", "enrichment", "custom", name="caretasktype")
    care_task_status = sa.Enum("open", "done", "missed", name="caretaskstatus")
    mood = sa.Enum("normal", "nervous", "aggressive", "tired", "playful", name="mood")
    appetite = sa.Enum("normal", "low", "high", "refused", name="appetite")
    movement = sa.Enum("normal", "limping", "weak", "hyperactive", name="movement")

    op.create_table(
        "care_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", care_task_type, nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("due_time", sa.Time(), nullable=True),
        sa.Column("status", care_task_status, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_care_tasks_assigned_date", "care_tasks", ["assigned_to_user_id", "due_date", "status"])

    op.create_table(
        "animal_condition_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("care_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mood", mood, nullable=False),
        sa.Column("appetite", appetite, nullable=False),
        sa.Column("movement", movement, nullable=False),
        sa.Column("visible_injuries", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("needs_vet_check", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("animal_condition_reports")
    op.drop_index("ix_care_tasks_assigned_date", table_name="care_tasks")
    op.drop_table("care_tasks")
