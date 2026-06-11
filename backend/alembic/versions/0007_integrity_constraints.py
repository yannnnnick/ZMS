"""add integrity constraints and server defaults

Revision ID: 0007_integrity_constraints
Revises: 0006_economy
Create Date: 2026-06-12

Adds the uniqueness/value constraints that were previously only enforced at the
application layer (or not at all) and backfills ``server_default`` values for
NOT NULL columns that only had ORM-side defaults, so that raw SQL inserts and
fresh migrations stay consistent with the models.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_integrity_constraints"
down_revision = "0006_economy"
branch_labels = None
depends_on = None


# Columns that are NOT NULL with an ORM-level default but no server_default.
# (column, server_default expression)
_BOOL_SERVER_DEFAULTS: dict[str, list[tuple[str, str]]] = {
    "users": [("is_active", "1")],
    "animals": [("active", "1")],
    "animal_assignments": [("active", "1")],
    "enclosure_assignments": [("active", "1")],
    "salary_profiles": [("active", "1")],
    "feeding_plans": [("is_optimized", "0")],
    "animal_condition_reports": [("visible_injuries", "0"), ("needs_vet_check", "0")],
    "medical_reports": [("follow_up_required", "0")],
}

_ENUM_SERVER_DEFAULTS: list[tuple[str, str, str]] = [
    ("animals", "sex", "unknown"),
    ("animals", "health_status", "healthy"),
    ("enclosures", "safety_status", "ok"),
    ("tasks", "status", "open"),
    ("care_tasks", "status", "open"),
    ("vet_tasks", "status", "open"),
    ("work_sessions", "source", "login"),
]


def upgrade() -> None:
    for table, columns in _BOOL_SERVER_DEFAULTS.items():
        with op.batch_alter_table(table) as batch_op:
            for column, default in columns:
                batch_op.alter_column(column, server_default=sa.text(default))

    for table, column, default in _ENUM_SERVER_DEFAULTS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(column, server_default=sa.text(f"'{default}'"))

    with op.batch_alter_table("enclosures") as batch_op:
        batch_op.create_check_constraint("ck_enclosures_capacity_non_negative", "capacity >= 0")

    with op.batch_alter_table("map_paths") as batch_op:
        batch_op.create_unique_constraint("uq_map_paths_route", ["from_enclosure_id", "to_enclosure_id"])
        batch_op.create_check_constraint(
            "ck_map_paths_distinct_endpoints", "from_enclosure_id <> to_enclosure_id"
        )

    with op.batch_alter_table("food_items") as batch_op:
        batch_op.create_unique_constraint("uq_food_items_name", ["name"])
        batch_op.create_check_constraint("ck_food_items_cost_non_negative", "cost_per_unit >= 0")
        batch_op.create_check_constraint("ck_food_items_calories_non_negative", "calories_per_unit >= 0")
        batch_op.create_check_constraint("ck_food_items_protein_non_negative", "protein_per_unit >= 0")
        batch_op.create_check_constraint("ck_food_items_quantity_non_negative", "available_quantity >= 0")

    with op.batch_alter_table("animal_nutrition_requirements") as batch_op:
        batch_op.create_unique_constraint("uq_nutrition_requirement_species", ["species_id"])
        batch_op.create_check_constraint("ck_nutrition_min_calories_non_negative", "min_calories >= 0")
        batch_op.create_check_constraint("ck_nutrition_min_protein_non_negative", "min_protein >= 0")

    with op.batch_alter_table("salary_profiles") as batch_op:
        batch_op.create_check_constraint("ck_salary_hourly_rate_non_negative", "hourly_rate >= 0")
        batch_op.create_check_constraint(
            "ck_salary_tax_rate_range",
            "tax_rate_percent IS NULL OR (tax_rate_percent >= 0 AND tax_rate_percent <= 100)",
        )

    with op.batch_alter_table("visitor_stats") as batch_op:
        batch_op.create_check_constraint("ck_visitor_stats_count_non_negative", "visitor_count >= 0")
        batch_op.create_check_constraint("ck_visitor_stats_revenue_non_negative", "ticket_revenue >= 0")


def downgrade() -> None:
    with op.batch_alter_table("visitor_stats") as batch_op:
        batch_op.drop_constraint("ck_visitor_stats_revenue_non_negative", type_="check")
        batch_op.drop_constraint("ck_visitor_stats_count_non_negative", type_="check")

    with op.batch_alter_table("salary_profiles") as batch_op:
        batch_op.drop_constraint("ck_salary_tax_rate_range", type_="check")
        batch_op.drop_constraint("ck_salary_hourly_rate_non_negative", type_="check")

    with op.batch_alter_table("animal_nutrition_requirements") as batch_op:
        batch_op.drop_constraint("ck_nutrition_min_protein_non_negative", type_="check")
        batch_op.drop_constraint("ck_nutrition_min_calories_non_negative", type_="check")
        batch_op.drop_constraint("uq_nutrition_requirement_species", type_="unique")

    with op.batch_alter_table("food_items") as batch_op:
        batch_op.drop_constraint("ck_food_items_quantity_non_negative", type_="check")
        batch_op.drop_constraint("ck_food_items_protein_non_negative", type_="check")
        batch_op.drop_constraint("ck_food_items_calories_non_negative", type_="check")
        batch_op.drop_constraint("ck_food_items_cost_non_negative", type_="check")
        batch_op.drop_constraint("uq_food_items_name", type_="unique")

    with op.batch_alter_table("map_paths") as batch_op:
        batch_op.drop_constraint("ck_map_paths_distinct_endpoints", type_="check")
        batch_op.drop_constraint("uq_map_paths_route", type_="unique")

    with op.batch_alter_table("enclosures") as batch_op:
        batch_op.drop_constraint("ck_enclosures_capacity_non_negative", type_="check")

    for table, columns in _BOOL_SERVER_DEFAULTS.items():
        with op.batch_alter_table(table) as batch_op:
            for column, _default in columns:
                batch_op.alter_column(column, server_default=None)

    for table, column, _default in _ENUM_SERVER_DEFAULTS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(column, server_default=None)
