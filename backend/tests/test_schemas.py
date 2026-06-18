import pytest
from pydantic import BaseModel, field_validator
from datetime import datetime, timezone, timedelta

from app.schemas import clean_text, clean_required_text
from app.schemas import (
    SpeciesBase, HealthRecordUpdate, EnclosureBase, TaskBase,
    FeedingScheduleBase, AnimalBase, MedicalReportCreate,
    AnimalConditionReportCreate, VetTaskBase, CareTaskBase
)

class DummySanitizeModel(BaseModel):
    text_field1: str | None = None
    text_field2: str | None = None

    @field_validator("text_field1", "text_field2")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        return clean_text(value)

def test_sanitize_text_fields():
    model = DummySanitizeModel(text_field1=None, text_field2=None)
    assert model.text_field1 is None
    assert model.text_field2 is None

    model = DummySanitizeModel(text_field1="  hello world  ")
    assert model.text_field1 == "hello world"

    model = DummySanitizeModel(text_field1="   ")
    assert model.text_field1 is None

    model = DummySanitizeModel(text_field1="<script>alert(1)</script>")
    assert model.text_field1 == "&lt;script&gt;alert(1)&lt;/script&gt;"

    model = DummySanitizeModel(text_field1="&lt;div&gt;test&lt;/div&gt;")
    assert model.text_field1 == "&lt;div&gt;test&lt;/div&gt;"

    model = DummySanitizeModel(text_field1=" <p>1</p> ", text_field2=" <p>2</p> ")
    assert model.text_field1 == "&lt;p&gt;1&lt;/p&gt;"
    assert model.text_field2 == "&lt;p&gt;2&lt;/p&gt;"

def test_clean_required_text():
    assert clean_required_text("  hello  ") == "hello"
    assert clean_required_text("<hello>") == "&lt;hello&gt;"
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
    model = DummyHealthRecord(description=None, medication=None)
    assert model.description is None
    assert model.medication is None

    model = DummyHealthRecord(description="  some description  ", medication="  aspirin  ")
    assert model.description == "some description"
    assert model.medication == "aspirin"

    model = DummyHealthRecord(description="   ", medication="   ")
    assert model.description is None
    assert model.medication is None

    model = DummyHealthRecord(description="<script>alert(1)</script>", medication="<script>alert(2)</script>")
    assert model.description == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert model.medication == "&lt;script&gt;alert(2)&lt;/script&gt;"

def test_actual_schemas_sanitize_text_fields():
    # Test SpeciesBase
    species = SpeciesBase(
        common_name="  Lion  ",
        scientific_name="Panthera leo",
        category=" Mammal ",
        conservation_status="VU ",
        husbandry_notes="<p>Test</p>"
    )
    assert species.common_name == "Lion"
    assert species.category == "Mammal"
    assert species.conservation_status == "VU"
    assert species.husbandry_notes == "&lt;p&gt;Test&lt;/p&gt;"

    # Test HealthRecordUpdate
    hr = HealthRecordUpdate(
        description="  Checkup  ",
        medication=" Aspirin "
    )
    assert hr.description == "Checkup"
    assert hr.medication == "Aspirin"

    # Test EnclosureBase
    enclosure = EnclosureBase(
        name="  Savanna  ",
        location=" North ",
        public_name="  The Great Savanna  ",
        capacity=10
    )
    assert enclosure.name == "Savanna"
    assert enclosure.location == "North"
    assert enclosure.public_name == "The Great Savanna"

    # Test TaskBase
    future_date = datetime.now(timezone.utc) + timedelta(days=1)
    task = TaskBase(
        title="  Clean Enclosure  ",
        description="<script>alert('test')</script>",
        task_type="cleaning",
        assigned_role="keeper",
        due_at=future_date
    )
    assert task.title == "Clean Enclosure"
    assert task.description == "&lt;script&gt;alert(&#x27;test&#x27;)&lt;/script&gt;"


def test_remaining_schemas_sanitize_text_fields():
    # Test FeedingScheduleBase
    from datetime import time
    fs = FeedingScheduleBase(animal_id=1, scheduled_time=time(10, 0),
        food_type="  Meat  ",
        amount="  5kg  ",
        recurrence="  Daily  ",
        responsible_role="keeper",
        notes="  <p>Fresh</p>  "
    )
    assert fs.food_type == "Meat"
    assert fs.amount == "5kg"
    assert fs.recurrence == "Daily"
    assert fs.notes == "&lt;p&gt;Fresh&lt;/p&gt;"

    # Test MedicalReportCreate
    mr = MedicalReportCreate(
        animal_id=1,
        diagnosis="  Flu  ",
        treatment="  Rest  ",
        medication="  None  ",
        notes="  <script>alert</script>  "
    )
    assert mr.diagnosis == "Flu"
    assert mr.treatment == "Rest"
    assert mr.medication == "None"
    assert mr.notes == "&lt;script&gt;alert&lt;/script&gt;"

    # Test AnimalConditionReportCreate
    from app.models import Mood, Appetite, Movement
    acr = AnimalConditionReportCreate(
        animal_id=1,
        mood=Mood.normal,
        appetite=Appetite.normal,
        movement=Movement.normal,
        notes="  Checkup  "
    )
    assert acr.notes == "Checkup"

    # Test VetTaskBase
    from datetime import date
    vt = VetTaskBase(
        title="  Vaccination  ",
        description="  Annual  ",
        animal_id=1,
        assigned_to_user_id=2,
        due_date=date.today()
    )
    assert vt.title == "Vaccination"
    assert vt.description == "Annual"

    # Test CareTaskBase
    ct = CareTaskBase(
        title="  Clean  ",
        description="  Weekly  ",
        assigned_to_user_id=1,
        task_type="cleaning",
        due_date=date.today()
    )
    assert ct.title == "Clean"
    assert ct.description == "Weekly"


def test_more_schemas_sanitize_text_fields():
    # SpeciesUpdate
    from app.schemas import SpeciesUpdate
    su = SpeciesUpdate(
        common_name="  Bear  ",
        husbandry_notes="  <div>Big</div>  "
    )
    assert su.common_name == "Bear"
    assert su.husbandry_notes == "&lt;div&gt;Big&lt;/div&gt;"

    # EnclosureUpdate
    from app.schemas import EnclosureUpdate
    eu = EnclosureUpdate(
        name="  Cave  ",
        public_description="  <b>Dark</b>  "
    )
    assert eu.name == "Cave"
    assert eu.public_description == "&lt;b&gt;Dark&lt;/b&gt;"

    # AnimalBase
    from app.schemas import AnimalBase
    from app.models import Sex
    from datetime import date
    ab = AnimalBase(
        species_id=1,
        enclosure_id=1,
        name="  Baloo  ",
        sex=Sex.male,
        birth_date=date.today(),

    )
    assert ab.name == "Baloo"

    # FeedingScheduleUpdate
    from app.schemas import FeedingScheduleUpdate
    fsu = FeedingScheduleUpdate(
        food_type="  Salmon  ",
        notes="  Fresh  "
    )
    assert fsu.food_type == "Salmon"
    assert fsu.notes == "Fresh"

    # HealthRecordBase
    from app.schemas import HealthRecordBase
    from app.models import RecordType
    hrb = HealthRecordBase(
        animal_id=1,
        record_type=RecordType.checkup,
        description="  Seen  ",
        medication="  None  "
    )
    assert hrb.description == "Seen"
    assert hrb.medication == "None"

    # TaskUpdate
    from app.schemas import TaskUpdate
    tu = TaskUpdate(
        title="  Feed  ",
        description="  Now  "
    )
    assert tu.title == "Feed"
    assert tu.description == "Now"

    # CareTaskUpdate
    from app.schemas import CareTaskUpdate
    ctu = CareTaskUpdate(
        title="  Clean  ",
        description="  Water  "
    )
    assert ctu.title == "Clean"
    assert ctu.description == "Water"

    # VetTaskUpdate
    from app.schemas import VetTaskUpdate
    vtu = VetTaskUpdate(
        title="  Surgery  ",
        description="  Leg  "
    )
    assert vtu.title == "Surgery"
    assert vtu.description == "Leg"


def test_dates_and_times_schemas():
    from app.schemas import HealthRecordBase, TaskUpdate, HealthRecordUpdate
    from datetime import date, timedelta

    # Test HealthRecordBase next_check_date
    yesterday = date.today() - timedelta(days=1)

    with pytest.raises(ValueError, match="Next check date must not be in the past."):
        HealthRecordBase(
            animal_id=1,
            record_type="checkup",
            next_check_date=yesterday
        )

    with pytest.raises(ValueError, match="Next check date must not be in the past."):
        HealthRecordUpdate(
            next_check_date=yesterday
        )

    from app.schemas import TaskUpdate
    from datetime import datetime, timezone

    past_dt = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValueError, match="Due date must not be in the past."):
        TaskUpdate(due_at=past_dt)


def test_task_base_due_at_no_tz():
    from app.schemas import TaskBase, TaskUpdate
    from datetime import datetime, timedelta

    # Test TaskBase due_at without timezone (should be comparable to utc)
    future_dt = datetime.now() + timedelta(days=1)

    task = TaskBase(
        title="Test",
        task_type="cleaning",
        assigned_role="keeper",
        due_at=future_dt
    )
    assert task.due_at is not None

    tu = TaskUpdate(due_at=future_dt)
    assert tu.due_at is not None

    # Test TaskUpdate due_at=None
    tu2 = TaskUpdate(due_at=None)
    assert tu2.due_at is None


def test_dates_valid_dates():
    from app.schemas import HealthRecordBase, HealthRecordUpdate
    from datetime import date

    # Test valid next_check_date
    today = date.today()
    hr = HealthRecordBase(
        animal_id=1,
        record_type="checkup",
        description="Test",
        next_check_date=today
    )
    assert hr.next_check_date == today

    hru = HealthRecordUpdate(
        next_check_date=today
    )
    assert hru.next_check_date == today

def test_login_request_validators():
    from app.schemas import LoginRequest

    with pytest.raises(ValueError, match="Enter a valid email address."):
        LoginRequest(email="invalid", password="StrongPassword123!")

    with pytest.raises(ValueError, match="Enter a valid email address."):
        LoginRequest(email="test@ example.com", password="StrongPassword123!")



    with pytest.raises(ValueError, match="Enter a valid email address."):
        LoginRequest(email="@test.com", password="StrongPassword123!")

    lr = LoginRequest(email=" TEST@example.com ", password="StrongPassword123!")
    assert lr.email == "test@example.com"

def test_task_base_past_date():
    from app.schemas import TaskBase
    from datetime import datetime, timedelta, timezone

    past_dt = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValueError, match="Due date must not be in the past."):
        TaskBase(
            title="Test",
            task_type="cleaning",
            assigned_role="keeper",
            due_at=past_dt
        )
