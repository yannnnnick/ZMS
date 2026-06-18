from datetime import date, datetime, time, timedelta, timezone

import pytest
from pydantic import BaseModel, field_validator

from app.models import Appetite, CareTaskType, Movement, Mood, RecordType, Sex, TaskType, UserRole
from app.schemas import (
    AnimalBase,
    AnimalConditionReportCreate,
    CareTaskBase,
    EnclosureBase,
    FeedingScheduleBase,
    HealthRecordBase,
    HealthRecordUpdate,
    LoginRequest,
    MedicalReportCreate,
    SpeciesBase,
    SpeciesUpdate,
    TaskBase,
    TaskUpdate,
    VetTaskBase,
    clean_required_text,
    clean_text,
)


def test_clean_text_edge_cases():
    assert clean_text(None) is None
    assert clean_text("") is None
    assert clean_text("   \t\n  ") is None
    assert clean_text("  hello world  ") == "hello world"
    assert clean_text("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    assert clean_text("&lt;b&gt;bold&lt;/b&gt;") == "&lt;b&gt;bold&lt;/b&gt;"
    assert clean_text("Hello & World") == "Hello &amp; World"


def test_clean_required_text_edge_cases():
    assert clean_required_text("  valid text  ") == "valid text"

    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text(None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("")

    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("   \t\n  ")


def test_actual_schema_text_sanitizers():
    species = SpeciesBase(
        common_name="  Lion  ",
        scientific_name=" Panthera leo ",
        category=" Mammal ",
        conservation_status=" VU ",
        husbandry_notes="<p>Test</p>",
    )
    assert species.common_name == "Lion"
    assert species.scientific_name == "Panthera leo"
    assert species.category == "Mammal"
    assert species.conservation_status == "VU"
    assert species.husbandry_notes == "&lt;p&gt;Test&lt;/p&gt;"

    species_update = SpeciesUpdate(common_name="  Bear  ", husbandry_notes="  <div>Big</div>  ")
    assert species_update.common_name == "Bear"
    assert species_update.husbandry_notes == "&lt;div&gt;Big&lt;/div&gt;"

    enclosure = EnclosureBase(
        name="  Savanna  ",
        location=" North ",
        capacity=10,
        notes=" <b>Safe</b> ",
        public_name="  The Great Savanna  ",
        public_description="  <i>Open area</i>  ",
    )
    assert enclosure.name == "Savanna"
    assert enclosure.location == "North"
    assert enclosure.notes == "&lt;b&gt;Safe&lt;/b&gt;"
    assert enclosure.public_name == "The Great Savanna"
    assert enclosure.public_description == "&lt;i&gt;Open area&lt;/i&gt;"

    animal = AnimalBase(name="  <Leo>  ", species_id=1, enclosure_id=1, sex=Sex.male)
    assert animal.name == "&lt;Leo&gt;"

    feeding = FeedingScheduleBase(
        animal_id=1,
        food_type="  Meat  ",
        amount="  5kg  ",
        scheduled_time=time(10, 0),
        recurrence="  Daily  ",
        responsible_role=UserRole.keeper,
        notes="  <p>Fresh</p>  ",
    )
    assert feeding.food_type == "Meat"
    assert feeding.amount == "5kg"
    assert feeding.recurrence == "Daily"
    assert feeding.notes == "&lt;p&gt;Fresh&lt;/p&gt;"

    health_record = HealthRecordBase(
        animal_id=1,
        record_type=RecordType.checkup,
        description="  Checkup  ",
        medication=" <b>Aspirin</b> ",
        next_check_date=date.today(),
    )
    assert health_record.description == "Checkup"
    assert health_record.medication == "&lt;b&gt;Aspirin&lt;/b&gt;"

    task = TaskBase(
        title="  Clean Enclosure  ",
        description="<script>alert('test')</script>",
        task_type=TaskType.cleaning,
        assigned_role=UserRole.keeper,
        due_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert task.title == "Clean Enclosure"
    assert task.description == "&lt;script&gt;alert(&#x27;test&#x27;)&lt;/script&gt;"


def test_care_vet_and_report_schema_text_sanitizers():
    care_task = CareTaskBase(
        title="  Clean  ",
        description="  Weekly  ",
        assigned_to_user_id=1,
        task_type=CareTaskType.cleaning,
        due_date=date.today(),
    )
    assert care_task.title == "Clean"
    assert care_task.description == "Weekly"

    condition_report = AnimalConditionReportCreate(
        animal_id=1,
        mood=Mood.normal,
        appetite=Appetite.normal,
        movement=Movement.normal,
        notes="  <p>Checkup</p>  ",
    )
    assert condition_report.notes == "&lt;p&gt;Checkup&lt;/p&gt;"

    vet_task = VetTaskBase(
        title="  Vaccination  ",
        description="  Annual  ",
        animal_id=1,
        assigned_to_user_id=2,
        due_date=date.today(),
    )
    assert vet_task.title == "Vaccination"
    assert vet_task.description == "Annual"

    medical_report = MedicalReportCreate(
        animal_id=1,
        diagnosis="  Flu  ",
        treatment="  Rest  ",
        medication="  None  ",
        notes="  <script>alert</script>  ",
    )
    assert medical_report.diagnosis == "Flu"
    assert medical_report.treatment == "Rest"
    assert medical_report.medication == "None"
    assert medical_report.notes == "&lt;script&gt;alert&lt;/script&gt;"


def test_schema_date_and_login_validators():
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(ValueError, match="Next check date must not be in the past."):
        HealthRecordBase(
            animal_id=1,
            record_type=RecordType.checkup,
            description="Checkup",
            next_check_date=yesterday,
        )

    with pytest.raises(ValueError, match="Next check date must not be in the past."):
        HealthRecordUpdate(next_check_date=yesterday)

    past_due_at = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValueError, match="Due date must not be in the past."):
        TaskBase(
            title="Clean",
            task_type=TaskType.cleaning,
            assigned_role=UserRole.keeper,
            due_at=past_due_at,
        )

    with pytest.raises(ValueError, match="Due date must not be in the past."):
        TaskUpdate(due_at=past_due_at)

    with pytest.raises(ValueError, match="Enter a valid email address."):
        LoginRequest(email="invalid", password="StrongPassword123!")

    with pytest.raises(ValueError, match="Enter a valid email address."):
        LoginRequest(email="test@ example.com", password="StrongPassword123!")

    login = LoginRequest(email=" TEST@example.com ", password="StrongPassword123!")
    assert login.email == "test@example.com"


class DummySanitizeModel(BaseModel):
    text_field1: str | None = None
    text_field2: str | None = None

    @field_validator("text_field1", "text_field2")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)

def test_sanitize_text_fields():
    # Test None value
    model = DummySanitizeModel(text_field1=None, text_field2=None)
    assert model.text_field1 is None
    assert model.text_field2 is None

    # Test stripping whitespace
    model = DummySanitizeModel(text_field1="  hello world  ")
    assert model.text_field1 == "hello world"

    # Test empty string after stripping
    model = DummySanitizeModel(text_field1="   ")
    assert model.text_field1 is None

    # Test HTML escaping
    model = DummySanitizeModel(text_field1="<script>alert(1)</script>")
    assert model.text_field1 == "&lt;script&gt;alert(1)&lt;/script&gt;"

    # Test HTML unescaping before escaping
    model = DummySanitizeModel(text_field1="&lt;div&gt;test&lt;/div&gt;")
    assert model.text_field1 == "&lt;div&gt;test&lt;/div&gt;"

    # Test multiple fields
    model = DummySanitizeModel(text_field1=" <p>1</p> ", text_field2=" <p>2</p> ")
    assert model.text_field1 == "&lt;p&gt;1&lt;/p&gt;"
    assert model.text_field2 == "&lt;p&gt;2&lt;/p&gt;"

def test_clean_required_text():
    # Valid string
    assert clean_required_text("  hello  ") == "hello"

    # HTML escaping
    assert clean_required_text("<hello>") == "&lt;hello&gt;"

    # Empty string raises ValueError
    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("   ")


class DummyHealthRecord(BaseModel):
    description: str | None = None
    medication: str | None = None

    @field_validator("description", "medication")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)

def test_dummy_health_record_sanitize_text_fields():
    # Test None values
    model = DummyHealthRecord(description=None, medication=None)
    assert model.description is None
    assert model.medication is None

    # Test whitespace stripping
    model = DummyHealthRecord(description="  some description  ", medication="  aspirin  ")
    assert model.description == "some description"
    assert model.medication == "aspirin"

    # Test empty string resolution to None
    model = DummyHealthRecord(description="   ", medication="   ")
    assert model.description is None
    assert model.medication is None

    # Test HTML escaping
    model = DummyHealthRecord(description="<script>alert(1)</script>", medication="<script>alert(2)</script>")
    assert model.description == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert model.medication == "&lt;script&gt;alert(2)&lt;/script&gt;"

    # Test HTML unescaping before escaping
    model = DummyHealthRecord(description="&lt;div&gt;test&lt;/div&gt;", medication="&lt;div&gt;test2&lt;/div&gt;")
    assert model.description == "&lt;div&gt;test&lt;/div&gt;"
    assert model.medication == "&lt;div&gt;test2&lt;/div&gt;"

    # Test multiple fields with mixed scenarios
    model = DummyHealthRecord(description=" <p>desc</p> ", medication="  ")
    assert model.description == "&lt;p&gt;desc&lt;/p&gt;"
    assert model.medication is None
