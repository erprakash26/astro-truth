"""UI chrome translation for the "Other" custom language selector.

Distinct from app.interpret, which translates chart CONTENT on every
interpretation request: this translates the app's static UI strings
(button labels, headings, form labels -- everything in the frontend's
i18n.js DICT.en) ONCE per language selection, in a single Anthropic API
call, and the frontend caches the result. Same USE_MOCK_LLM-gated modes
as app.interpret and app.chat:

- Mock mode (default): no UI translation available -- returns a
  structured "requires live mode" response so the frontend can fall
  back to English UI chrome cleanly.
- Real mode: one Anthropic API call with a forced tool call, so the
  reply is guaranteed to be a {key: translated_string} object for every
  canonical key -- not free text that has to be parsed loosely.

UI_STRINGS below mirrors frontend/src/i18n.js's DICT.en exactly (same
keys, same English source text). There's no shared build step between
the Python backend and the Vite frontend, so -- same as
interpret.LANGUAGE_NAMES / SIGN_NAME_NE duplicating small bits of
knowledge already present elsewhere -- this list is kept in sync by
hand. If you add or rename a key in DICT.en, mirror it here.
"""

from __future__ import annotations

import json

from app.interpret import MAX_TOKENS, MODEL, is_mock_mode, require_api_key

UI_STRINGS: dict[str, str] = {
    "appName": "AstroTruth",
    "tagline": "Your Vedic birth chart, precisely computed.",
    "name": "Name (optional)",
    "namePlaceholder": "e.g. Priya",
    "calendar": "Calendar",
    "ad": "AD",
    "bs": "BS",
    "date": "Date",
    "year": "Year",
    "month": "Month",
    "day": "Day",
    "time": "Time",
    "birthPlace": "Birth place",
    "birthPlacePlaceholder": "Search for a city…",
    "submit": "Generate chart",
    "submitting": "Computing chart…",
    "newChart": "New chart",
    "lagna": "Lagna",
    "chart": "Kundali chart",
    "planets": "Planets",
    "graha": "Graha",
    "sign": "Sign",
    "degree": "Degree",
    "nakshatraPada": "Nakshatra / Pada",
    "house": "House",
    "dignity": "Dignity",
    "exalted": "Exalted",
    "ownSign": "Own sign",
    "debilitated": "Debilitated",
    "moolatrikona": "Moolatrikona",
    "dashaTimeline": "Vimshottari dasha timeline",
    "mahadasha": "Mahadasha",
    "antardasha": "Antardasha",
    "current": "Current",
    "errorRequired": "Please fill in all fields.",
    "errorCity": "Please choose a city from the list.",
    "errorGeneric": "Something went wrong. Please try again.",
    "noCityResults": "No matching cities",
    "noLanguageResults": "No matching languages",
    "interpret": "Interpret my chart",
    "interpreting": "Interpreting…",
    "mockBadge": "mock",
    "interpretError": "Could not generate an interpretation. Please try again.",
    "transits": "Current transits",
    "fromLagna": "from your Lagna",
    "fromMoon": "from your Moon",
    "nextIngress": "Next sign change",
    "downloadPdf": "Download PDF",
    "downloadingPdf": "Generating PDF…",
    "downloadError": "Could not generate the PDF. Please try again.",
    "langOther": "Other",
    "langOtherPlaceholder": "Search for a language…",
    "chatTitle": "Ask about your chart",
    "chatMockNote": (
        "Mock mode only understands a few question patterns — try one of the examples "
        "below. Full conversational chat requires live mode."
    ),
    "chatPlaceholder": "Ask a question about your chart…",
    "chatPlaceholderMock": (
        'Try: "What sign is my Moon in?" / "Any yogas?" / "What\'s my dasha on 2030-01-01?"'
    ),
    "chatSend": "Send",
    "chatSending": "Sending…",
    "chatError": "Could not get a reply. Please try again.",
}

_TOOL_NAME = "submit_ui_translation"

_SYSTEM_PROMPT = """You translate short UI strings (button labels, headings, form labels,
status messages) for a Vedic astrology app called AstroTruth.

Keep the product name "AstroTruth" untranslated wherever it appears.
Keep every translation concise and natural for UI chrome, not prose --
match the register and length of the English source. Preserve any
placeholder punctuation (ellipses, slashes, quotes) where it makes sense
in the target language.

Call the submit_ui_translation tool exactly once, with one translated
string per key, translating every value into the requested language."""


def _translate_tool_schema() -> dict:
    return {
        "name": _TOOL_NAME,
        "description": "Submit the translated UI strings, one entry per key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "translations": {
                    "type": "object",
                    "description": "Maps each UI string key to its translation.",
                    "properties": {key: {"type": "string"} for key in UI_STRINGS},
                    "required": list(UI_STRINGS.keys()),
                },
            },
            "required": ["translations"],
        },
    }


def _log_mock_mode() -> None:
    print(
        "MOCK MODE: translate_ui is returning a 'requires live mode' response "
        "(USE_MOCK_LLM=true, no Anthropic API call made)."
    )


def _real_translate_ui(language: str) -> dict[str, str]:
    import anthropic

    client = anthropic.Anthropic(api_key=require_api_key())
    tool = _translate_tool_schema()

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Translate each of these UI strings into {language}. Keys are "
                    "identifiers, not to be translated -- only translate the values.\n\n"
                    f"{json.dumps(UI_STRINGS, indent=2, ensure_ascii=False)}"
                ),
            }
        ],
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    translated = tool_use.input.get("translations", {})
    # Any key the model dropped falls back to its English source rather than
    # leaving a hole the frontend would render as an empty string.
    return {key: translated.get(key) or UI_STRINGS[key] for key in UI_STRINGS}


def translate_ui(language: str) -> dict:
    """Translate the full UI_STRINGS set into `language` in one call.

    Returns {"available": bool, "language": str, "translations": dict | None,
    "note": str | None}. In mock mode, or if the caller wants a uniform shape
    to check before applying translations, "available" tells you whether
    "translations" is usable.
    """
    if is_mock_mode():
        _log_mock_mode()
        return {
            "available": False,
            "language": language,
            "translations": None,
            "note": (
                f"UI translation into {language} requires live mode — mock mode doesn't "
                "call the Anthropic API. Set USE_MOCK_LLM=false with a configured "
                "Anthropic API key to get translated UI chrome. Chart content translation "
                "is unaffected and continues to work independently."
            ),
        }

    translations = _real_translate_ui(language)
    return {"available": True, "language": language, "translations": translations, "note": None}
