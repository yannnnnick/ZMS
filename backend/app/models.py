from __future__ import annotations

from datetime import date, datetime, time, timezone
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, Time
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
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="actor")


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    common_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    conservation_status: Mapped[str | None] = mapped_column(String(120))
    husbandry_notes: Mapped[str | None] = mapped_column(Text)

    animals: Mapped[list["Animal"]] = relationship(back_populates="species")


class Enclosure(Base):
    __tablename__ = "enclosures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_status: Mapped[SafetyStatus] = mapped_column(SAEnum(SafetyStatus), default=SafetyStatus.ok, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    animals: Mapped[list["Animal"]] = relationship(back_populates="enclosure")
    tasks: Mapped[list["Task"]] = relationship(back_populates="related_enclosure")


class Animal(Base, TimestampMixin):
    __tablename__ = "animals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"), nullable=False)
    enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id"), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[Sex] = mapped_column(SAEnum(Sex), default=Sex.unknown, nullable=False)
    health_status: Mapped[HealthStatus] = mapped_column(
        SAEnum(HealthStatus), default=HealthStatus.healthy, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    species: Mapped[Species] = relationship(back_populates="animals")
    enclosure: Mapped[Enclosure] = relationship(back_populates="animals")
    feeding_schedules: Mapped[list["FeedingSchedule"]] = relationship(back_populates="animal")
    health_records: Mapped[list["HealthRecord"]] = relationship(back_populates="animal")
    tasks: Mapped[list["Task"]] = relationship(back_populates="related_animal")


class FeedingSchedule(Base):
    __tablename__ = "feeding_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False)
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
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False)
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
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.open, nullable=False)
    related_animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id"))
    related_enclosure_id: Mapped[int | None] = mapped_column(ForeignKey("enclosures.id"))

    related_animal: Mapped[Animal | None] = relationship(back_populates="tasks")
    related_enclosure: Mapped[Enclosure | None] = relationship(back_populates="tasks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    details: Mapped[dict | None] = mapped_column(JSON)

    actor: Mapped[User | None] = relationship(back_populates="audit_logs")

