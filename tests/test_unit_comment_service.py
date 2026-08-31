import json
from types import SimpleNamespace

from services import comment_service


def test_suggest_comment_returns_human_review_flags(monkeypatch):
    payload = {
        "issue": "The uncertainty qualifier is missing.",
        "evidence": "The passage makes an unqualified claim.",
        "proposed_comment": "Please calibrate the uncertainty language.",
        "proposed_resolution": "Add an assessed confidence qualifier.",
        "confidence": "high",
    }
    captured = {}

    def fake_generate_content(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(text=json.dumps(payload))

    monkeypatch.setattr(
        comment_service.client.models,
        "generate_content",
        fake_generate_content,
    )

    result = comment_service.suggest_comment(
        document_name="chapter.pdf",
        category="Uncertainty language",
        page=12,
        from_line=4,
        to_line=6,
        selected_text="A selected finding.",
        context="Nearby evidence.",
        reviewer_note="Check calibration.",
    )

    assert result["demo_only"] is True
    assert result["requires_human_review"] is True
    assert result["proposed_comment"] == payload["proposed_comment"]
    assert captured["model"] == comment_service.GEMINI_MODEL


def test_suggest_comment_rejects_incomplete_model_output(monkeypatch):
    monkeypatch.setattr(
        comment_service.client.models,
        "generate_content",
        lambda **_: SimpleNamespace(text='{"issue": "Incomplete"}'),
    )

    try:
        comment_service.suggest_comment(
            document_name="chapter.pdf",
            category="Completeness",
            page=1,
            from_line=0,
            to_line=0,
            selected_text="Text",
            context="Context",
        )
    except ValueError as exc:
        assert "missing required" in str(exc)
    else:
        raise AssertionError("Expected incomplete output to be rejected")
