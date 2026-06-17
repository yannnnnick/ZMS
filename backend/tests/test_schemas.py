import pytest
from app.schemas import clean_required_text, clean_text

def test_clean_required_text_valid():
    assert clean_required_text("  hello  ") == "hello"

def test_clean_required_text_error_path():
    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text(None)

    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("")

    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("   ")

def test_clean_text_valid():
    assert clean_text("  hello  ") == "hello"

def test_clean_text_empty():
    assert clean_text(None) is None
    assert clean_text("") is None
    assert clean_text("   ") is None
