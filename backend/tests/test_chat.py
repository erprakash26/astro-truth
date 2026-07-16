from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app import chat
from app.chat_tools import get_dasha_at, get_transit
from app.dasha import current_dasha, vimshottari
from app.engine import compute_chart, local_time_to_utc
from app.transits import compute_transits


def _build_reference_stored() -> dict:
    dt_utc = local_time_to_utc(datetime(2000, 1, 1, 12, 0, 0), "Europe/London")
    chart = compute_chart(dt_utc, lat=51.5074, lon=-0.1278)
    dasha_sequence = vimshottari(chart.planets["Moon"].longitude, dt_utc)
    now = datetime.now(timezone.utc)
    current = current_dasha(dasha_sequence, now)
    transits = compute_transits(chart.lagna_sign, chart.planets["Moon"].sign, now)
    return {
        "name": None,
        "chart": chart.model_dump(mode="json"),
        "dasha_timeline": [period.model_dump(mode="json") for period in dasha_sequence],
        "current_dasha": (
            {
                "mahadasha": current[0].model_dump(mode="json"),
                "antardasha": current[1].model_dump(mode="json"),
            }
            if current is not None
            else None
        ),
        "transits": transits.model_dump(mode="json"),
    }


@pytest.fixture(scope="module")
def reference_stored() -> dict:
    return _build_reference_stored()


# --- mock-mode pattern matcher: at least 4 distinct question shapes -----


def test_mock_chat_planet_question(reference_stored):
    reply = chat.chat_reply(reference_stored, "What sign is my Moon in?")
    assert "Moon" in reply
    assert "Libra" in reply


def test_mock_chat_yoga_question(reference_stored):
    reply = chat.chat_reply(reference_stored, "Any yogas in my chart?")
    assert "Budhaditya Yoga" in reply


def test_mock_chat_dasha_question(reference_stored):
    first_antar = reference_stored["dasha_timeline"][0]["antardashas"][0]
    start = datetime.fromisoformat(first_antar["start"])
    end = datetime.fromisoformat(first_antar["end"])
    midpoint = start + (end - start) / 2
    expected = get_dasha_at(reference_stored, midpoint.date().isoformat())

    reply = chat.chat_reply(reference_stored, f"What's my dasha on {midpoint.date().isoformat()}?")
    assert expected["mahadasha"] in reply
    assert expected["antardasha"] in reply


def test_mock_chat_transit_question(reference_stored):
    expected = get_transit(reference_stored, "Jupiter")
    reply = chat.chat_reply(reference_stored, "What's the current transit for Jupiter?")
    assert expected["sign"] in reply


def test_mock_chat_unrecognized_question_names_live_mode(reference_stored):
    reply = chat.chat_reply(reference_stored, "Will I get rich next year?")
    assert "live mode" in reply


def test_mock_chat_planet_outside_tracked_set_falls_back_to_unrecognized(reference_stored):
    # "Pluto" isn't one of the nine tracked planets, so the regex simply
    # doesn't match it — this chart's tool functions never see the name,
    # and the reply is the same "I don't understand" fallback as any
    # other unrecognized question, not a tool error.
    reply = chat.chat_reply(reference_stored, "What sign is my Pluto in?")
    assert "live mode" in reply


# --- real-mode wiring: present, doesn't crash without an API key --------


def test_tools_schema_matches_chat_tools_functions():
    names = {tool["name"] for tool in chat.TOOLS}
    assert names == {"get_planet", "get_dasha_at", "get_transit", "get_yogas"}


def test_real_mode_without_api_key_raises_clear_error(monkeypatch, reference_stored):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        chat.chat_reply(reference_stored, "What sign is my Moon in?")
