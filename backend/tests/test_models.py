from datetime import date, datetime, timezone
from app.models import utcnow, Animal

def test_utcnow():
    before = datetime.now(timezone.utc)
    now = utcnow()
    after = datetime.now(timezone.utc)

    assert isinstance(now, datetime)
    assert now.tzinfo is timezone.utc
    assert before <= now <= after

def test_animal_age_years():
    # Test when birth_date is None
    animal_no_birth_date = Animal()
    assert animal_no_birth_date.age_years is None

    # Test when birth_date is set
    today = date.today()

    # Has had birthday this year
    past_month = today.month - 1 if today.month > 1 else 12
    past_year = today.year - 5 if today.month > 1 else today.year - 6
    animal_had_birthday = Animal(birth_date=date(past_year, past_month, 1))
    assert animal_had_birthday.age_years == 5

    # Has not had birthday this year
    future_month = today.month + 1 if today.month < 12 else 1
    future_year = today.year - 5 if today.month < 12 else today.year - 4
    animal_not_had_birthday = Animal(birth_date=date(future_year, future_month, 28))
    assert animal_not_had_birthday.age_years == 4

    # Birthday is today
    animal_birthday_today = Animal(birth_date=date(today.year - 5, today.month, today.day))
    assert animal_birthday_today.age_years == 5
