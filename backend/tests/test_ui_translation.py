from __future__ import annotations

import pytest

from app import ui_translation
from app.ui_translation import UI_STRINGS, translate_ui


def test_mock_mode_returns_unavailable_with_note():
    result = translate_ui("Spanish")
    assert result["available"] is False
    assert result["translations"] is None
    assert result["language"] == "Spanish"
    assert "requires live mode" in result["note"]
    assert "Spanish" in result["note"]


def test_mock_mode_note_mentions_content_translation_is_unaffected():
    result = translate_ui("Spanish")
    assert "content translation" in result["note"].lower()


def test_tool_schema_covers_every_ui_string_key():
    schema = ui_translation._translate_tool_schema()
    props = schema["input_schema"]["properties"]["translations"]["properties"]
    required = schema["input_schema"]["properties"]["translations"]["required"]
    assert set(props.keys()) == set(UI_STRINGS.keys())
    assert set(required) == set(UI_STRINGS.keys())


def test_real_mode_without_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        translate_ui("Spanish")


def test_real_translate_ui_applies_returned_translations(monkeypatch):
    # Confirms the translated-string JSON, when present, actually gets
    # mapped onto every UI_STRINGS key -- the data-layer half of "gets
    # applied to swap UI text" (the frontend half, DICT.other + t(),
    # is covered by frontend/src/i18n.test.js).
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    fake_translations = {key: f"[es] {value}" for key, value in UI_STRINGS.items()}

    class FakeToolUseBlock:
        type = "tool_use"
        input = {"translations": fake_translations}

    class FakeResponse:
        content = [FakeToolUseBlock()]

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["tool_choice"] == {"type": "tool", "name": "submit_ui_translation"}
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)

    result = translate_ui("Spanish")
    assert result["available"] is True
    assert result["translations"] == fake_translations
    assert set(result["translations"].keys()) == set(UI_STRINGS.keys())


def test_real_translate_ui_falls_back_to_english_for_missing_keys(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Model drops one key -- shouldn't leave a hole in the returned dict.
    partial = {key: f"[es] {value}" for key, value in UI_STRINGS.items() if key != "appName"}

    class FakeToolUseBlock:
        type = "tool_use"
        input = {"translations": partial}

    class FakeResponse:
        content = [FakeToolUseBlock()]

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            self.messages = FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)

    result = translate_ui("Spanish")
    assert result["translations"]["appName"] == UI_STRINGS["appName"]
