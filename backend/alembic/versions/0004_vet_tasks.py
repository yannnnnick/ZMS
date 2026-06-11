"""add vet tasks and medical reports

Revision ID: 0004_vet_tasks
Revises: 0003_care_tasks
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_vet_tasks"
down_revision = "0003_care_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    vet_task_priority = sa.Enum("low", "medium", "high", "emergency", name="vettaskpriority")
    vet_task_status = sa.Enum("open", "done", "cancelled", name="vettaskstatus")

    op.create_table(
        "vet_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", vet_task_priority, nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", vet_task_status, nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vet_tasks_assigned_date", "vet_tasks", ["assigned_to_user_id", "due_date", "status"])

    op.create_table(
        "medical_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vet_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("vet_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("medication", sa.Text(), nullable=True),
        sa.Column("follow_up_required", sa.Boolean(), nullable=False),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("medical_reports")
    op.drop_index("ix_vet_tasks_assigned_date", table_name="vet_tasks")
    op.drop_table("vet_tasks")
