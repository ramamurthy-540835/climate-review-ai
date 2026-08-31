from services.pdf_processor import _normalize_text


def test_normalize_text_repairs_wrapping_and_preserves_paragraphs():
    raw = "Climate pro-\njections are impor-\nTant.\n\nSecond paragraph.\n"

    normalized = _normalize_text(raw)

    assert "projections" in normalized
    assert "impor- Tant" in normalized
    assert "\n\nSecond paragraph." in normalized


def test_normalize_text_removes_soft_hyphens():
    assert _normalize_text("cli\u00admate") == "climate"
