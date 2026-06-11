from __future__ import annotations

from datetime import date, datetime, time, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    admin = "admin"
    keeper = "keeper"
    vet = "vet"
    viewer = "viewer"


class SafetyStatus(str, Enum):
    ok = "ok"
    warning = "warning"
    critical = "critical"


class Sex(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class HealthStatus(str, Enum):
    healthy = "healthy"
    observation = "observation"
    treatment = "treatment"
    critical = "critical"


class RecordType(str, Enum):
    checkup = "checkup"
    medication = "medication"
    incident = "incident"
    note = "note"


class TaskType(str, Enum):
    feeding = "feeding"
    cleaning = "cleaning"
    checkup = "checkup"
    maintenance = "maintenance"


class TaskStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"


class AssignmentRoleType(str, Enum):
    keeper = "keeper"
    vet = "vet"


class CareTaskType(str, Enum):
    feeding = "feeding"
    cleaning = "cleaning"
    health_check = "health_check"
    enrichment = "enrichment"
    custom = "custom"


class CareTaskStatus(str, Enum):
    open = "open"
    done = "done"
    missed = "missed"


class Mood(str, Enum):
    normal = "normal"
    nervous = "nervous"
    aggressive = "aggressive"
    tired = "tired"
    playful = "playful"


class Appetite(str, Enum):
    normal = "normal"
    low = "low"
    high = "high"
    refused = "refused"


class Movement(str, Enum):
    normal = "normal"
    limping = "limping"
    weak = "weak"
    hyperactive = "hyperactive"


class VetTaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    emergency = "emergency"


class VetTaskStatus(str, Enum):
    open = "open"
    done = "done"
    cancelled = "cancelled"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    health_records: Mapped[list["HealthRecord"]] = relationship(back_populates="created_by")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor", passive_deletes=True)
    animal_assignments: Mapped[list["AnimalAssignment"]] = relationship(
        foreign_keys="AnimalAssignment.user_id", back_populates="user", passive_deletes=True
    )
    enclosure_assignments: Mapped[list["EnclosureAssignment"]] = relationship(
        foreign_keys="EnclosureAssignment.user_id", back_populates="user", passive_deletes=True
    )
    care_tasks: Mapped[list["CareTask"]] = relationship(
        foreign_keys="CareTask.assigned_to_user_id", back_populates="assigned_to", passive_deletes=True
    )
    vet_tasks: Mapped[list["VetTask"]] = relationship(
        foreign_keys="VetTask.assigned_to_user_id", back_populates="assigned_to", passive_deletes=True
    )
    work_sessions: Mapped[list["WorkSession"]] = relationship(back_populates="user", passive_deletes=True)
    salary_profile: Mapped["SalaryProfile | None"] = relationship(back_populates="user", passive_deletes=True)


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    common_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    conservation_status: Mapped[str | None] = mapped_column(String(120))
    husbandry_notes: Mapped[str | None] = mapped_column(Text)

    animals: Mapped[list["Animal"]] = relationship(back_populates="species", passive_deletes=True)


class Enclosure(Base):
    __tablename__ = "enclosures"
    __table_args__ = (CheckConstraint("capacity >= 0", name="ck_enclosures_capacity_non_negative"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_status: Mapped[SafetyStatus] = mapped_column(SAEnum(SafetyStatus), default=SafetyStatus.ok, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    map_x: Mapped[int | None] = mapped_column(Integer)
    map_y: Mapped[int | None] = mapped_column(Integer)
    map_width: Mapped[int | None] = mapped_column(Integer)
    map_height: Mapped[int | None] = mapped_column(Integer)
    public_name: Mapped[str | None] = mapped_column(String(120))
    public_description: Mapped[str | None] = mapped_column(Text)
    is_public_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    animals: Mapped[list["Animal"]] = relationship(back_populates="enclosure", passive_deletes=True)
    tasks: Mapped[list["Task"]] = relationship(back_populates="related_enclosure", passive_deletes=True)
    assignments: Mapped[list["EnclosureAssignment"]] = relationship(back_populates="enclosure", passive_deletes=True)
    care_tasks: Mapped[list["CareTask"]] = relationship(back_populates="enclosure", passive_deletes=True)


class Animal(Base, TimestampMixin):
    __tablename__ = "animals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id", ondelete="CASCADE"), nullable=False)
    enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[Sex] = mapped_column(SAEnum(Sex), default=Sex.unknown, nullable=False)
    health_status: Mapped[HealthStatus] = mapped_column(
        SAEnum(HealthStatus), default=HealthStatus.healthy, index=True, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    species: Mapped[Species] = relationship(back_populates="animals")
    enclosure: Mapped[Enclosure] = relationship(back_populates="animals")
    feeding_schedules: Mapped[list["FeedingSchedule"]] = relationship(
        back_populates="animal", cascade="all, delete-orphan", passive_deletes=True
    )
    health_records: Mapped[list["HealthRecord"]] = relationship(
        back_populates="animal", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="related_animal", passive_deletes=True)
    assignments: Mapped[list["AnimalAssignment"]] = relationship(back_populates="animal", passive_deletes=True)
    care_tasks: Mapped[list["CareTask"]] = relationship(back_populates="animal", passive_deletes=True)
    condition_reports: Mapped[list["AnimalConditionReport"]] = relationship(back_populates="animal", passive_deletes=True)
    vet_tasks: Mapped[list["VetTask"]] = relationship(back_populates="animal", passive_deletes=True)
    medical_reports: Mapped[list["MedicalReport"]] = relationship(back_populates="animal", passive_deletes=True)

    @property
    def age_years(self) -> int | None:
        if self.birth_date is None:
            return None
        today = date.today()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years


class FeedingSchedule(Base):
    __tablename__ = "feeding_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    food_type: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[str] = mapped_column(String(80), nullable=False)
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    recurrence: Mapped[str] = mapped_column(String(80), nullable=False)
    responsible_role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    animal: Mapped[Animal] = relationship(back_populates="feeding_schedules")


class HealthRecord(Base):
    __tablename__ = "health_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    record_type: Mapped[RecordType] = mapped_column(SAEnum(RecordType), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    medication: Mapped[str | None] = mapped_column(Text)
    next_check_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal] = relationship(back_populates="health_records")
    created_by: Mapped[User] = relationship(back_populates="health_records")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    task_type: Mapped[TaskType] = mapped_column(SAEnum(TaskType), nullable=False)
    assigned_role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.open, index=True, nullable=False)
    related_animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"))
    related_enclosure_id: Mapped[int | None] = mapped_column(ForeignKey("enclosures.id", ondelete="SET NULL"))

    related_animal: Mapped[Animal | None] = relationship(back_populates="tasks")
    related_enclosure: Mapped[Enclosure | None] = relationship(back_populates="tasks")


class AnimalAssignment(Base):
    __tablename__ = "animal_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_type: Mapped[AssignmentRoleType] = mapped_column(SAEnum(AssignmentRoleType), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    animal: Mapped[Animal] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="animal_assignments")
    assigned_by_user: Mapped[User | None] = relationship(foreign_keys=[assigned_by])


class EnclosureAssignment(Base):
    __tablename__ = "enclosure_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    enclosure: Mapped[Enclosure] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="enclosure_assignments")
    assigned_by_user: Mapped[User | None] = relationship(foreign_keys=[assigned_by])


class CareTask(Base):
    __tablename__ = "care_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"))
    enclosure_id: Mapped[int | None] = mapped_column(ForeignKey("enclosures.id", ondelete="SET NULL"))
    assigned_to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_type: Mapped[CareTaskType] = mapped_column(SAEnum(CareTaskType), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_time: Mapped[time | None] = mapped_column(Time)
    status: Mapped[CareTaskStatus] = mapped_column(SAEnum(CareTaskStatus), default=CareTaskStatus.open, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal | None] = relationship(back_populates="care_tasks")
    enclosure: Mapped[Enclosure | None] = relationship(back_populates="care_tasks")
    assigned_to: Mapped[User] = relationship(foreign_keys=[assigned_to_user_id], back_populates="care_tasks")
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by])
    condition_reports: Mapped[list["AnimalConditionReport"]] = relationship(back_populates="task", passive_deletes=True)


class AnimalConditionReport(Base):
    __tablename__ = "animal_condition_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("care_tasks.id", ondelete="SET NULL"))
    mood: Mapped[Mood] = mapped_column(SAEnum(Mood), nullable=False)
    appetite: Mapped[Appetite] = mapped_column(SAEnum(Appetite), nullable=False)
    movement: Mapped[Movement] = mapped_column(SAEnum(Movement), nullable=False)
    visible_injuries: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    needs_vet_check: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal] = relationship(back_populates="condition_reports")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_user_id])
    task: Mapped[CareTask | None] = relationship(back_populates="condition_reports")


class VetTask(Base):
    __tablename__ = "vet_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    assigned_to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    priority: Mapped[VetTaskPriority] = mapped_column(SAEnum(VetTaskPriority), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[VetTaskStatus] = mapped_column(SAEnum(VetTaskStatus), default=VetTaskStatus.open, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal] = relationship(back_populates="vet_tasks")
    assigned_to: Mapped[User] = relationship(foreign_keys=[assigned_to_user_id], back_populates="vet_tasks")
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by])
    medical_reports: Mapped[list["MedicalReport"]] = relationship(back_populates="task", passive_deletes=True)


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    vet_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("vet_tasks.id", ondelete="SET NULL"))
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    treatment: Mapped[str | None] = mapped_column(Text)
    medication: Mapped[str | None] = mapped_column(Text)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal] = relationship(back_populates="medical_reports")
    vet: Mapped[User] = relationship(foreign_keys=[vet_user_id])
    task: Mapped[VetTask | None] = relationship(back_populates="medical_reports")


class MapPath(Base):
    __tablename__ = "map_paths"
    __table_args__ = (
        UniqueConstraint("from_enclosure_id", "to_enclosure_id", name="uq_map_paths_route"),
        CheckConstraint("from_enclosure_id <> to_enclosure_id", name="ck_map_paths_distinct_endpoints"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False)
    to_enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False)
    distance_meters: Mapped[int | None] = mapped_column(Integer)
    walking_time_minutes: Mapped[int | None] = mapped_column(Integer)
    path_svg_data: Mapped[str | None] = mapped_column(Text)

    from_enclosure: Mapped[Enclosure] = relationship(foreign_keys=[from_enclosure_id])
    to_enclosure: Mapped[Enclosure] = relationship(foreign_keys=[to_enclosure_id])


class VisitorStat(Base):
    __tablename__ = "visitor_stats"
    __table_args__ = (
        CheckConstraint("visitor_count >= 0", name="ck_visitor_stats_count_non_negative"),
        CheckConstraint("ticket_revenue >= 0", name="ck_visitor_stats_revenue_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    visitor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ticket_revenue: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WorkSession(Base):
    __tablename__ = "work_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="login", nullable=False)

    user: Mapped[User] = relationship(back_populates="work_sessions")


class SalaryProfile(Base):
    __tablename__ = "salary_profiles"
    __table_args__ = (
        CheckConstraint("hourly_rate >= 0", name="ck_salary_hourly_rate_non_negative"),
        CheckConstraint(
            "tax_rate_percent IS NULL OR (tax_rate_percent >= 0 AND tax_rate_percent <= 100)",
            name="ck_salary_tax_rate_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    hourly_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_base_salary: Mapped[int | None] = mapped_column(Integer)
    tax_rate_percent: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="salary_profile")


class FoodItem(Base):
    __tablename__ = "food_items"
    __table_args__ = (
        UniqueConstraint("name", name="uq_food_items_name"),
        CheckConstraint("cost_per_unit >= 0", name="ck_food_items_cost_non_negative"),
        CheckConstraint("calories_per_unit >= 0", name="ck_food_items_calories_non_negative"),
        CheckConstraint("protein_per_unit >= 0", name="ck_food_items_protein_non_negative"),
        CheckConstraint("available_quantity >= 0", name="ck_food_items_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    cost_per_unit: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_per_unit: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_per_unit: Mapped[int] = mapped_column(Integer, nullable=False)
    fat_per_unit: Mapped[int | None] = mapped_column(Integer)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    feeding_plans: Mapped[list["FeedingPlan"]] = relationship(back_populates="food_item", passive_deletes=True)


class AnimalNutritionRequirement(Base):
    __tablename__ = "animal_nutrition_requirements"
    __table_args__ = (
        UniqueConstraint("species_id", name="uq_nutrition_requirement_species"),
        CheckConstraint("min_calories >= 0", name="ck_nutrition_min_calories_non_negative"),
        CheckConstraint("min_protein >= 0", name="ck_nutrition_min_protein_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id", ondelete="CASCADE"), nullable=False)
    min_calories: Mapped[int] = mapped_column(Integer, nullable=False)
    min_protein: Mapped[int] = mapped_column(Integer, nullable=False)
    max_fat: Mapped[int | None] = mapped_column(Integer)
    food_category: Mapped[str | None] = mapped_column(String(80))

    species: Mapped[Species] = relationship()


class FeedingPlan(Base):
    __tablename__ = "feeding_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    food_item_id: Mapped[int] = mapped_column(ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_optimized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    animal: Mapped[Animal] = relationship()
    food_item: Mapped[FoodItem] = relationship(back_populates="feeding_plans")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    details: Mapped[dict | None] = mapped_column(JSON)

    actor: Mapped[User | None] = relationship(back_populates="audit_logs")


Index("ix_animals_active_health_status", Animal.active, Animal.health_status)
Index("ix_enclosures_safety_status", Enclosure.safety_status)
Index("ix_animal_assignments_user", AnimalAssignment.user_id, AnimalAssignment.active)
Index("ix_animal_assignments_animal", AnimalAssignment.animal_id, AnimalAssignment.active)
Index("ix_enclosure_assignments_user", EnclosureAssignment.user_id, EnclosureAssignment.active)
Index("ix_care_tasks_assigned_date", CareTask.assigned_to_user_id, CareTask.due_date, CareTask.status)
Index("ix_vet_tasks_assigned_date", VetTask.assigned_to_user_id, VetTask.due_date, VetTask.status)
Index("ix_work_sessions_user", WorkSession.user_id, WorkSession.login_at)
