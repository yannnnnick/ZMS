"""add economy and nutrition tables

Revision ID: 0006_economy
Revises: 0005_public_map
Create Date: 2026-06-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_economy"
down_revision = "0005_public_map"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visitor_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("visitor_count", sa.Integer(), nullable=False),
        sa.Column("ticket_revenue", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_visitor_stats_date"), "visitor_stats", ["date"])

    op.create_table(
        "work_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("logout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
    )
    op.create_index("ix_work_sessions_user", "work_sessions", ["user_id", "login_at"])

    op.create_table(
        "salary_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("hourly_rate", sa.Integer(), nullable=False),
        sa.Column("monthly_base_salary", sa.Integer(), nullable=True),
        sa.Column("tax_rate_percent", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "food_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("cost_per_unit", sa.Integer(), nullable=False),
        sa.Column("calories_per_unit", sa.Integer(), nullable=False),
        sa.Column("protein_per_unit", sa.Integer(), nullable=False),
        sa.Column("fat_per_unit", sa.Integer(), nullable=True),
        sa.Column("available_quantity", sa.Integer(), nullable=False),
    )

    op.create_table(
        "animal_nutrition_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("species_id", sa.Integer(), sa.ForeignKey("species.id", ondelete="CASCADE"), nullable=False),
        sa.Column("min_calories", sa.Integer(), nullable=False),
        sa.Column("min_protein", sa.Integer(), nullable=False),
        sa.Column("max_fat", sa.Integer(), nullable=True),
        sa.Column("food_category", sa.String(length=80), nullable=True),
    )

    op.create_table(
        "feeding_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("food_item_id", sa.Integer(), sa.ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_optimized", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("feeding_plans")
    op.drop_table("animal_nutrition_requirements")
    op.drop_table("food_items")
    op.drop_table("salary_profiles")
    op.drop_index("ix_work_sessions_user", table_name="work_sessions")
    op.drop_table("work_sessions")
    op.drop_index(op.f("ix_visitor_stats_date"), table_name="visitor_stats")
    op.drop_table("visitor_stats")
