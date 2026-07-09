"""Golden-file regression tests for app.engine.compute_chart().

Locks in the known-correct values for our three verified reference charts
so a future change to the engine (ayanamsa mode, house formula, dignity
logic, etc.) can't silently alter results that have already been checked.

Chart 1 (London) is the original Stage-1 reference chart, independently
cross-checked against pyswisseph directly (see tests/test_engine.py).
Charts 2 and 3 were computed with the same verified engine and spot-checked
for internal consistency before being locked in here: correct
exaltation/debilitation pairs (opposite signs, 6 houses apart), Rahu/Ketu
exactly 180 degrees apart, and vimshottari's first mahadasha lord matching
the moon nakshatra-lord formula independently.
"""

from datetime import datetime

import pytest

from app.engine import compute_chart, local_time_to_utc

TOLERANCE_DEG = 0.2


def _build(dt: datetime, tz: str, lat: float, lon: float):
    dt_utc = local_time_to_utc(dt, tz)
    return compute_chart(dt_utc, lat=lat, lon=lon)


GOLDEN_CHARTS = {
    "london_2000_01_01": {
        "input": dict(dt=datetime(2000, 1, 1, 12, 0, 0), tz="Europe/London", lat=51.5074, lon=-0.1278),
        "lagna": ("Aries", 0.16, "Ashwini", 1),
        "planets": {
            "Sun": ("Sagittarius", 16.52, 9, "Purva Ashadha", 1, {}),
            "Moon": ("Libra", 19.47, 7, "Swati", 4, {}),
            "Mars": ("Aquarius", 4.11, 11, "Dhanishta", 4, {}),
            "Mercury": ("Sagittarius", 8.04, 9, "Mula", 3, {}),
            "Jupiter": ("Aries", 1.40, 1, "Ashwini", 1, {}),
            "Venus": ("Scorpio", 7.71, 8, "Anuradha", 2, {}),
            "Saturn": ("Aries", 16.54, 1, "Bharani", 1, {"debilitated": True}),
            "Rahu": ("Cancer", 11.19, 4, "Pushya", 3, {}),
            "Ketu": ("Capricorn", 11.19, 10, "Shravana", 1, {}),
        },
    },
    "kathmandu_1995_05_15": {
        # UTC+5:45 fractional-hour timezone offset (Asia/Kathmandu).
        "input": dict(dt=datetime(1995, 5, 15, 6, 30, 0), tz="Asia/Kathmandu", lat=27.7129, lon=85.3228),
        "lagna": ("Taurus", 18.97, "Rohini", 3),
        "planets": {
            "Sun": ("Aries", 29.95, 12, "Krittika", 1, {"exalted": True}),
            "Moon": ("Scorpio", 2.28, 7, "Vishakha", 4, {"debilitated": True}),
            "Mars": ("Leo", 1.63, 4, "Magha", 1, {}),
            "Mercury": ("Taurus", 21.08, 1, "Rohini", 4, {}),
            "Jupiter": ("Scorpio", 18.86, 7, "Jyeshtha", 1, {}),
            "Venus": ("Aries", 3.85, 12, "Ashwini", 2, {}),
            "Saturn": ("Aquarius", 28.78, 10, "Purva Bhadrapada", 3, {"own_sign": True}),
            "Rahu": ("Libra", 10.87, 6, "Swati", 2, {}),
            "Ketu": ("Aries", 10.87, 12, "Ashwini", 4, {}),
        },
    },
    "new_york_1985_11_02": {
        "input": dict(dt=datetime(1985, 11, 2, 14, 15, 0), tz="America/New_York", lat=40.7128, lon=-74.006),
        "lagna": ("Aquarius", 13.74, "Shatabhisha", 3),
        "planets": {
            "Sun": ("Libra", 16.66, 9, "Swati", 3, {"debilitated": True}),
            "Moon": ("Gemini", 11.75, 5, "Ardra", 2, {}),
            "Mars": ("Virgo", 10.21, 8, "Hasta", 1, {}),
            "Mercury": ("Scorpio", 8.97, 10, "Anuradha", 2, {}),
            "Jupiter": ("Capricorn", 14.96, 12, "Shravana", 2, {"debilitated": True}),
            "Venus": ("Virgo", 27.81, 8, "Chitra", 2, {"debilitated": True}),
            "Saturn": ("Scorpio", 4.67, 10, "Anuradha", 1, {}),
            "Rahu": ("Aries", 15.30, 3, "Bharani", 1, {}),
            "Ketu": ("Libra", 15.30, 9, "Swati", 3, {}),
        },
    },
}


@pytest.fixture(scope="module", params=list(GOLDEN_CHARTS.items()), ids=list(GOLDEN_CHARTS.keys()))
def golden(request):
    name, spec = request.param
    chart = _build(**spec["input"])
    return name, chart, spec


def test_lagna_matches_golden_value(golden):
    _name, chart, spec = golden
    sign_name, degrees, nakshatra, pada = spec["lagna"]
    assert chart.lagna_sign_name == sign_name
    assert abs(chart.lagna_degrees_in_sign - degrees) <= TOLERANCE_DEG
    assert chart.lagna_nakshatra == nakshatra
    assert chart.lagna_pada == pada


def test_every_planet_matches_golden_value(golden):
    _name, chart, spec = golden
    for planet_name, (sign_name, degrees, house, nakshatra, pada, flags) in spec["planets"].items():
        position = chart.planets[planet_name]
        assert position.sign_name == sign_name, f"{planet_name} sign"
        assert abs(position.degrees_in_sign - degrees) <= TOLERANCE_DEG, f"{planet_name} degrees"
        assert position.house == house, f"{planet_name} house"
        assert position.nakshatra == nakshatra, f"{planet_name} nakshatra"
        assert position.pada == pada, f"{planet_name} pada"
        assert position.exalted == flags.get("exalted", False), f"{planet_name} exalted"
        assert position.own_sign == flags.get("own_sign", False), f"{planet_name} own_sign"
        assert position.debilitated == flags.get("debilitated", False), f"{planet_name} debilitated"
        assert position.moolatrikona == flags.get("moolatrikona", False), f"{planet_name} moolatrikona"


def test_rahu_ketu_are_exactly_opposite(golden):
    _name, chart, _spec = golden
    rahu = chart.planets["Rahu"].longitude
    ketu = chart.planets["Ketu"].longitude
    assert abs((rahu - ketu) % 360 - 180) < 1e-6
