"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("admin", "keeper", "vet", "viewer", name="userrole")
    safety_status = sa.Enum("ok", "warning", "critical", name="safetystatus")
    sex = sa.Enum("male", "female", "unknown", name="sex")
    health_status = sa.Enum("healthy", "observation", "treatment", "critical", name="healthstatus")
    record_type = sa.Enum("checkup", "medication", "incident", "note", name="recordtype")
    task_type = sa.Enum("feeding", "cleaning", "checkup", "maintenance", name="tasktype")
    task_status = sa.Enum("open", "in_progress", "done", name="taskstatus")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "species",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("common_name", sa.String(length=120), nullable=False),
        sa.Column("scientific_name", sa.String(length=160), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("conservation_status", sa.String(length=120), nullable=True),
        sa.Column("husbandry_notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("common_name"),
    )

    op.create_table(
        "enclosures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("safety_status", safety_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "animals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("species_id", sa.Integer(), sa.ForeignKey("species.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("sex", sex, nullable=False),
        sa.Column("health_status", health_status, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "feeding_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("food_type", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.String(length=80), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=False),
        sa.Column("recurrence", sa.String(length=80), nullable=False),
        sa.Column("responsible_role", user_role, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "health_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("record_type", record_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("medication", sa.Text(), nullable=True),
        sa.Column("next_check_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", task_type, nullable=False),
        sa.Column("assigned_role", user_role, nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("related_animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("related_enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
    )
    op.create_index("ix_animals_active", "animals", ["active"])
    op.create_index("ix_animals_health_status", "animals", ["health_status"])
    op.create_index("ix_animals_active_health_status", "animals", ["active", "health_status"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_enclosures_safety_status", "enclosures", ["safety_status"])


def downgrade() -> None:
    op.drop_index("ix_enclosures_safety_status", table_name="enclosures")
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_animals_active_health_status", table_name="animals")
    op.drop_index("ix_animals_health_status", table_name="animals")
    op.drop_index("ix_animals_active", table_name="animals")
    op.drop_table("audit_logs")
    op.drop_table("tasks")
    op.drop_table("health_records")
    op.drop_table("feeding_schedules")
    op.drop_table("animals")
    op.drop_table("enclosures")
    op.drop_table("species")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
