import pytest

from app.schemas import clean_text, clean_required_text, SpeciesBase, HealthRecordUpdate


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


def test_species_base_sanitize_text_fields():
    # SpeciesBase requires common_name and category. Let's test the other fields too.

    # Test stripping whitespace
    model = SpeciesBase(
        common_name="  Lion  ",
        category="  Mammal  ",
        husbandry_notes="  Requires large space  ",
        scientific_name="  Panthera leo  ",
        conservation_status="  Vulnerable  "
    )
    assert model.common_name == "Lion"
    assert model.category == "Mammal"
    assert model.husbandry_notes == "Requires large space"
    assert model.scientific_name == "Panthera leo"
    assert model.conservation_status == "Vulnerable"

    # Test HTML escaping
    model = SpeciesBase(
        common_name="<script>alert(1)</script>",
        category="Cat",
    )
    assert model.common_name == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert model.category == "Cat"

    # Test empty string resolution to None for optional fields (scientific_name, conservation_status, husbandry_notes)
    # Required fields (common_name, category) should not be None, but clean_text might return None. Pydantic handles requiredness.
    # Note: clean_text on empty string returns None. For required str fields this might cause validation error if not properly handled,
    # but the current schema uses clean_text which returns None. We'll test optional fields here.
    model = SpeciesBase(
        common_name="Tiger",
        category="Mammal",
        scientific_name="   ",
        conservation_status="   ",
        husbandry_notes="   "
    )
    assert model.common_name == "Tiger"
    assert model.category == "Mammal"
    assert model.scientific_name is None
    assert model.conservation_status is None
    assert model.husbandry_notes is None

def test_clean_required_text():
    # Valid string
    assert clean_required_text("  hello  ") == "hello"

    # HTML escaping
    assert clean_required_text("<hello>") == "&lt;hello&gt;"

    # Empty string raises ValueError
    with pytest.raises(ValueError, match="Value must not be empty."):
        clean_required_text("   ")


def test_health_record_update_sanitize_text_fields():
    # Test None values
    model = HealthRecordUpdate(description=None, medication=None)
    assert model.description is None
    assert model.medication is None

    # Test whitespace stripping
    model = HealthRecordUpdate(description="  some description  ", medication="  aspirin  ")
    assert model.description == "some description"
    assert model.medication == "aspirin"

    # Test empty string resolution to None
    model = HealthRecordUpdate(description="   ", medication="   ")
    assert model.description is None
    assert model.medication is None

    # Test HTML escaping
    model = HealthRecordUpdate(description="<script>alert(1)</script>", medication="<script>alert(2)</script>")
    assert model.description == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert model.medication == "&lt;script&gt;alert(2)&lt;/script&gt;"

    # Test HTML unescaping before escaping
    model = HealthRecordUpdate(description="&lt;div&gt;test&lt;/div&gt;", medication="&lt;div&gt;test2&lt;/div&gt;")
    assert model.description == "&lt;div&gt;test&lt;/div&gt;"
    assert model.medication == "&lt;div&gt;test2&lt;/div&gt;"

    # Test multiple fields with mixed scenarios
    model = HealthRecordUpdate(description=" <p>desc</p> ", medication="  ")
    assert model.description == "&lt;p&gt;desc&lt;/p&gt;"
    assert model.medication is None
