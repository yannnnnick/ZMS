import pytest
from app.schemas import clean_text, clean_required_text

def test_clean_text_none():
    assert clean_text(None) is None

def test_clean_text_empty():
    assert clean_text("") is None

def test_clean_text_whitespace():
    assert clean_text("   \t\n  ") is None

def test_clean_text_strips_whitespace():
    assert clean_text("  hello world  ") == "hello world"

def test_clean_text_escapes_html():
    assert clean_text("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

def test_clean_text_unescapes_then_escapes():
    # If the input is already escaped, unescape() will turn it back, then escape() escapes it again.
    # This prevents double escaping.
    assert clean_text("&lt;b&gt;bold&lt;/b&gt;") == "&lt;b&gt;bold&lt;/b&gt;"

def test_clean_text_mixed_html_and_text():
    assert clean_text("Hello & World") == "Hello &amp; World"

def test_clean_required_text_valid():
    assert clean_required_text("  valid text  ") == "valid text"

def test_clean_required_text_empty():
    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("")

def test_clean_required_text_whitespace():
    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("   \t\n  ")

def test_clean_required_text_none():
    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text(None)
