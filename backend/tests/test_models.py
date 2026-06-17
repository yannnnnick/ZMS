from datetime import datetime, timezone
from app.models import utcnow

def test_utcnow():
    now = utcnow()
    assert isinstance(now, datetime)
    assert now.tzinfo is timezone.utc
