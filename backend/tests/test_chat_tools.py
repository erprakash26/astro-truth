from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.chat_tools import ChartToolError, get_dasha_at, get_planet, get_transit, get_yogas
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


# --- get_planet -------------------------------------------------------


def test_get_planet_known_reference_values(reference_stored):
    info = get_planet(reference_stored, "Moon")
    assert info["planet"] == "Moon"
    assert info["sign"] == "Libra"
    assert info["nakshatra"] == "Swati"
    assert info["house"] == reference_stored["chart"]["planets"]["Moon"]["house"]


def test_get_planet_is_case_insensitive(reference_stored):
    info = get_planet(reference_stored, "mOOn")
    assert info["planet"] == "Moon"


def test_get_planet_reports_dignity(reference_stored):
    # Saturn is debilitated in the reference chart (per interpret.py's
    # hand-authored mock text for this exact chart).
    info = get_planet(reference_stored, "Saturn")
    assert info["dignity"] == "debilitated"


def test_get_planet_unknown_planet_raises():
    stored = _build_reference_stored()
    with pytest.raises(ChartToolError):
        get_planet(stored, "Pluto")


# --- get_dasha_at -------------------------------------------------------


def test_get_dasha_at_matches_first_antardasha(reference_stored):
    first_maha = reference_stored["dasha_timeline"][0]
    first_antar = first_maha["antardashas"][0]
    start = datetime.fromisoformat(first_antar["start"])
    end = datetime.fromisoformat(first_antar["end"])
    midpoint = start + (end - start) / 2

    result = get_dasha_at(reference_stored, midpoint.isoformat())
    assert result["mahadasha"] == first_maha["lord"]
    assert result["antardasha"] == first_antar["lord"]


def test_get_dasha_at_out_of_range_raises(reference_stored):
    with pytest.raises(ChartToolError):
        get_dasha_at(reference_stored, "1900-01-01")


def test_get_dasha_at_unparseable_date_raises(reference_stored):
    with pytest.raises(ChartToolError):
        get_dasha_at(reference_stored, "not-a-date")


# --- get_transit -------------------------------------------------------


def test_get_transit_jupiter_matches_stored(reference_stored):
    info = get_transit(reference_stored, "jupiter")
    stored_jupiter = reference_stored["transits"]["jupiter"]
    assert info["planet"] == "Jupiter"
    assert info["sign"] == stored_jupiter["sign_name"]
    assert info["house_from_lagna"] == stored_jupiter["house_from_lagna"]


def test_get_transit_unsupported_planet_raises(reference_stored):
    with pytest.raises(ChartToolError):
        get_transit(reference_stored, "Mars")


# --- get_yogas -------------------------------------------------------


def test_get_yogas_reference_chart_has_budhaditya_only(reference_stored):
    yogas = get_yogas(reference_stored)
    names = {y["name"] for y in yogas}
    assert names == {"Budhaditya Yoga"}
    budhaditya = next(y for y in yogas if y["name"] == "Budhaditya Yoga")
    assert set(budhaditya["planets"]) == {"Sun", "Mercury"}
