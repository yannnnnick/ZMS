import datetime as dt

from app import models
from app.models import utcnow

def test_utcnow():
    before = dt.datetime.now(dt.timezone.utc)
    now = utcnow()
    after = dt.datetime.now(dt.timezone.utc)

    assert isinstance(now, dt.datetime)
    assert now.tzinfo is dt.timezone.utc
    assert before <= now <= after


class MockDate(dt.date):
    @classmethod
    def today(cls) -> dt.date:
        return cls(2023, 6, 15)


def test_animal_age_years(monkeypatch):
    monkeypatch.setattr(models, "date", MockDate)

    animal_no_birth_date = models.Animal()
    assert animal_no_birth_date.age_years is None

    animal_birthday_today = models.Animal(birth_date=dt.date(2020, 6, 15))
    assert animal_birthday_today.age_years == 3

    animal_birthday_passed = models.Animal(birth_date=dt.date(2020, 6, 14))
    assert animal_birthday_passed.age_years == 3

    animal_birthday_future = models.Animal(birth_date=dt.date(2020, 6, 16))
    assert animal_birthday_future.age_years == 2
