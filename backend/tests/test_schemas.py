import pytest
from pydantic import BaseModel, field_validator

from app.schemas import clean_text, clean_required_text

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
