from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import HealthStatus, RecordType, SafetyStatus, Sex, TaskStatus, TaskType, UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1:
            raise ValueError("Enter a valid email address.")
        local_part, domain_part = normalized.split("@", maxsplit=1)
        if not local_part or not domain_part or any(character.isspace() for character in normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    display_name: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    role: UserRole
    is_active: bool


class SpeciesBase(BaseModel):
    common_name: str = Field(min_length=2, max_length=120)
    scientific_name: str | None = Field(default=None, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    conservation_status: str | None = Field(default=None, max_length=120)
    husbandry_notes: str | None = None


class SpeciesCreate(SpeciesBase):
    pass


class SpeciesRead(SpeciesBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class EnclosureBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    capacity: int = Field(ge=1, le=10000)
    safety_status: SafetyStatus = SafetyStatus.ok
    notes: str | None = None


class EnclosureCreate(EnclosureBase):
    pass


class EnclosureRead(EnclosureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AnimalBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    species_id: int
    enclosure_id: int
    birth_date: date | None = None
    sex: Sex = Sex.unknown
    health_status: HealthStatus = HealthStatus.healthy
    active: bool = True


class AnimalCreate(AnimalBase):
    pass


class AnimalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    species_id: int | None = None
    enclosure_id: int | None = None
    birth_date: date | None = None
    sex: Sex | None = None
    health_status: HealthStatus | None = None
    active: bool | None = None


class AnimalRead(AnimalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    species: SpeciesRead
    enclosure: EnclosureRead


class FeedingScheduleBase(BaseModel):
    animal_id: int
    food_type: str = Field(min_length=2, max_length=120)
    amount: str = Field(min_length=1, max_length=80)
    scheduled_time: time
    recurrence: str = Field(min_length=2, max_length=80)
    responsible_role: UserRole
    notes: str | None = None


class FeedingScheduleCreate(FeedingScheduleBase):
    pass


class FeedingScheduleRead(FeedingScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    animal: AnimalRead


class HealthRecordBase(BaseModel):
    animal_id: int
    record_type: RecordType
    description: str = Field(min_length=3)
    medication: str | None = None
    next_check_date: date | None = None


class HealthRecordCreate(HealthRecordBase):
    pass


class HealthRecordRead(HealthRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_user_id: int
    created_at: datetime
    animal: AnimalRead
    created_by: UserRead


class TaskBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = None
    task_type: TaskType
    assigned_role: UserRole
    due_at: datetime
    status: TaskStatus = TaskStatus.open
    related_animal_id: int | None = None
    related_enclosure_id: int | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = None
    task_type: TaskType | None = None
    assigned_role: UserRole | None = None
    due_at: datetime | None = None
    status: TaskStatus | None = None
    related_animal_id: int | None = None
    related_enclosure_id: int | None = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    timestamp: datetime
    ip_hash: str | None
    details: dict | None


class DashboardSummary(BaseModel):
    animals_total: int
    open_tasks: int
    due_feedings: int
    critical_health: int
    warning_enclosures: int
    recent_tasks: list[TaskRead]
    warning_animals: list[AnimalRead]
    enclosure_status: list[EnclosureRead]
