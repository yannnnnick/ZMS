from __future__ import annotations

from html import escape, unescape
from datetime import date, datetime, time, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    Appetite,
    AssignmentRoleType,
    CareTaskStatus,
    CareTaskType,
    HealthStatus,
    Mood,
    Movement,
    RecordType,
    SafetyStatus,
    Sex,
    TaskStatus,
    TaskType,
    UserRole,
    VetTaskPriority,
    VetTaskStatus,
)
from .security import validate_password_strength


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return escape(unescape(stripped)) if stripped else None


def clean_required_text(value: str) -> str:
    cleaned = clean_text(value)
    if cleaned is None:
        raise ValueError("Value must not be empty.")
    return cleaned


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

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class SessionResponse(BaseModel):
    role: UserRole
    display_name: str
    csrf_token: str


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
    husbandry_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("common_name", "scientific_name", "category", "conservation_status", "husbandry_notes")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class SpeciesCreate(SpeciesBase):
    pass


class SpeciesUpdate(BaseModel):
    common_name: str | None = Field(default=None, min_length=2, max_length=120)
    scientific_name: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    conservation_status: str | None = Field(default=None, max_length=120)
    husbandry_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("common_name", "scientific_name", "category", "conservation_status", "husbandry_notes")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class SpeciesRead(SpeciesBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class EnclosureBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    capacity: int = Field(ge=1, le=10000)
    safety_status: SafetyStatus = SafetyStatus.ok
    notes: str | None = Field(default=None, max_length=5000)
    map_x: int | None = Field(default=None, ge=0, le=1000)
    map_y: int | None = Field(default=None, ge=0, le=1000)
    map_width: int | None = Field(default=None, ge=1, le=1000)
    map_height: int | None = Field(default=None, ge=1, le=1000)
    public_name: str | None = Field(default=None, max_length=120)
    public_description: str | None = Field(default=None, max_length=5000)
    is_public_visible: bool = True

    @field_validator("name", "location", "notes", "public_name", "public_description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class EnclosureCreate(EnclosureBase):
    pass


class EnclosureUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    location: str | None = Field(default=None, min_length=2, max_length=120)
    capacity: int | None = Field(default=None, ge=1, le=10000)
    safety_status: SafetyStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)
    map_x: int | None = Field(default=None, ge=0, le=1000)
    map_y: int | None = Field(default=None, ge=0, le=1000)
    map_width: int | None = Field(default=None, ge=1, le=1000)
    map_height: int | None = Field(default=None, ge=1, le=1000)
    public_name: str | None = Field(default=None, max_length=120)
    public_description: str | None = Field(default=None, max_length=5000)
    is_public_visible: bool | None = None

    @field_validator("name", "location", "notes", "public_name", "public_description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


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

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        return clean_required_text(value)


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
    age_years: int | None = None
    species: SpeciesRead
    enclosure: EnclosureRead


class FeedingScheduleBase(BaseModel):
    animal_id: int
    food_type: str = Field(min_length=2, max_length=120)
    amount: str = Field(min_length=1, max_length=80)
    scheduled_time: time
    recurrence: str = Field(min_length=2, max_length=80)
    responsible_role: UserRole
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("food_type", "amount", "recurrence", "notes")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class FeedingScheduleCreate(FeedingScheduleBase):
    pass


class FeedingScheduleUpdate(BaseModel):
    food_type: str | None = Field(default=None, min_length=2, max_length=120)
    amount: str | None = Field(default=None, min_length=1, max_length=80)
    scheduled_time: time | None = None
    recurrence: str | None = Field(default=None, min_length=2, max_length=80)
    responsible_role: UserRole | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("food_type", "amount", "recurrence", "notes")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class FeedingScheduleRead(FeedingScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    animal: AnimalRead


class HealthRecordBase(BaseModel):
    animal_id: int
    record_type: RecordType
    description: str = Field(min_length=3, max_length=10000)
    medication: str | None = Field(default=None, max_length=5000)
    next_check_date: date | None = None

    @field_validator("description", "medication")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)

    @field_validator("next_check_date")
    @classmethod
    def validate_next_check_date(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("Next check date must not be in the past.")
        return value


class HealthRecordCreate(HealthRecordBase):
    pass


class HealthRecordUpdate(BaseModel):
    record_type: RecordType | None = None
    description: str | None = Field(default=None, min_length=3, max_length=10000)
    medication: str | None = Field(default=None, max_length=5000)
    next_check_date: date | None = None

    @field_validator("description", "medication")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)

    @field_validator("next_check_date")
    @classmethod
    def validate_next_check_date(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("Next check date must not be in the past.")
        return value


class HealthRecordRead(HealthRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_user_id: int
    created_at: datetime
    animal: AnimalRead
    created_by: UserRead


class TaskBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    task_type: TaskType
    assigned_role: UserRole
    due_at: datetime
    status: TaskStatus = TaskStatus.open
    related_animal_id: int | None = None
    related_enclosure_id: int | None = None

    @field_validator("title", "description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime) -> datetime:
        comparable = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if comparable < datetime.now(timezone.utc):
            raise ValueError("Due date must not be in the past.")
        return value


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    task_type: TaskType | None = None
    assigned_role: UserRole | None = None
    due_at: datetime | None = None
    status: TaskStatus | None = None
    related_animal_id: int | None = None
    related_enclosure_id: int | None = None

    @field_validator("title", "description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        comparable = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if comparable < datetime.now(timezone.utc):
            raise ValueError("Due date must not be in the past.")
        return value


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
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


class AnimalAssignmentCreate(BaseModel):
    animal_id: int
    user_id: int
    role_type: AssignmentRoleType


class AnimalAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    animal_id: int
    user_id: int
    role_type: AssignmentRoleType
    created_at: datetime
    active: bool
    animal: AnimalRead
    user: UserRead


class EnclosureAssignmentCreate(BaseModel):
    enclosure_id: int
    user_id: int


class EnclosureAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    enclosure_id: int
    user_id: int
    created_at: datetime
    active: bool
    enclosure: EnclosureRead
    user: UserRead


class CareTaskBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    animal_id: int | None = None
    enclosure_id: int | None = None
    assigned_to_user_id: int
    task_type: CareTaskType
    due_date: date
    due_time: time | None = None
    status: CareTaskStatus = CareTaskStatus.open

    @field_validator("title", "description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class CareTaskCreate(CareTaskBase):
    pass


class CareTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to_user_id: int | None = None
    task_type: CareTaskType | None = None
    due_date: date | None = None
    due_time: time | None = None
    status: CareTaskStatus | None = None

    @field_validator("title", "description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class CareTaskRead(CareTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    completed_at: datetime | None
    created_by: int
    created_at: datetime
    animal: AnimalRead | None
    enclosure: EnclosureRead | None
    assigned_to: UserRead


class AnimalConditionReportCreate(BaseModel):
    animal_id: int
    task_id: int | None = None
    mood: Mood
    appetite: Appetite
    movement: Movement
    visible_injuries: bool = False
    notes: str | None = Field(default=None, max_length=5000)
    needs_vet_check: bool = False

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, value: str | None) -> str | None:
        return clean_text(value)


class AnimalConditionReportRead(AnimalConditionReportCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_user_id: int
    created_at: datetime
    animal: AnimalRead
    created_by: UserRead


class VetTaskBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    animal_id: int
    assigned_to_user_id: int
    priority: VetTaskPriority = VetTaskPriority.medium
    due_date: date
    status: VetTaskStatus = VetTaskStatus.open

    @field_validator("title", "description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class VetTaskCreate(VetTaskBase):
    pass


class VetTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to_user_id: int | None = None
    priority: VetTaskPriority | None = None
    due_date: date | None = None
    status: VetTaskStatus | None = None

    @field_validator("title", "description")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class VetTaskRead(VetTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by: int
    created_at: datetime
    animal: AnimalRead
    assigned_to: UserRead


class MedicalReportCreate(BaseModel):
    animal_id: int
    task_id: int | None = None
    diagnosis: str = Field(min_length=3, max_length=10000)
    treatment: str | None = Field(default=None, max_length=5000)
    medication: str | None = Field(default=None, max_length=5000)
    follow_up_required: bool = False
    follow_up_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("diagnosis", "treatment", "medication", "notes")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)


class MedicalReportRead(MedicalReportCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vet_user_id: int
    created_at: datetime
    animal: AnimalRead
    vet: UserRead


class PublicAnimalRead(BaseModel):
    name: str
    species: str
    sex: Sex
    age_years: int | None


class PublicEnclosureRead(BaseModel):
    public_name: str
    public_description: str | None
    location: str
    map_x: int
    map_y: int
    map_width: int
    map_height: int
    animals: list[PublicAnimalRead]


class PublicMapPathRead(BaseModel):
    from_enclosure: str
    to_enclosure: str
    distance_meters: int | None
    walking_time_minutes: int | None
    path_svg_data: str | None


class PublicZooMapRead(BaseModel):
    enclosures: list[PublicEnclosureRead]
    paths: list[PublicMapPathRead]


class VisitorStatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    visitor_count: int
    ticket_revenue: int


class EconomySummary(BaseModel):
    visitors_today: int
    visitors_week: int
    ticket_revenue_week: int
    estimated_payroll_month: int
    food_inventory_value: int
    open_tasks: int
    open_vet_cases: int
    visitor_stats: list[VisitorStatRead]


class SalarySimulationRequest(BaseModel):
    user_id: int
    start_date: date
    end_date: date


class SalarySimulationResponse(BaseModel):
    user: UserRead
    hours: float
    hourly_rate: int
    gross_pay: int
    estimated_deductions: int
    estimated_net: int
    is_simulation: bool = True


class FeedingOptimizationRequest(BaseModel):
    animal_id: int


class FeedingOptimizationItem(BaseModel):
    food_item_id: int
    food_name: str
    quantity: int
    unit: str
    cost: int


class FeedingOptimizationResponse(BaseModel):
    success: bool
    message: str
    total_cost: int = 0
    feeding_plan: list[FeedingOptimizationItem] = []
    method: str
