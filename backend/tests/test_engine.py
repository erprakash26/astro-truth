from datetime import datetime

import pytest

from app.engine import compute_chart, local_time_to_utc

TOLERANCE_DEG = 0.2


def assert_position(position, sign_name, degrees_in_sign, nakshatra):
    assert position.sign_name == sign_name
    assert abs(position.degrees_in_sign - degrees_in_sign) <= TOLERANCE_DEG
    assert position.nakshatra == nakshatra


def test_local_time_to_utc_europe_london_january_no_dst():
    local_dt = datetime(2000, 1, 1, 12, 0, 0)
    dt_utc = local_time_to_utc(local_dt, "Europe/London")
    assert dt_utc.utcoffset().total_seconds() == 0
    assert dt_utc.hour == 12
    assert dt_utc.day == 1


def test_local_time_to_utc_rejects_aware_input():
    aware_dt = local_time_to_utc(datetime(2000, 1, 1, 12, 0, 0), "Europe/London")
    with pytest.raises(ValueError):
        local_time_to_utc(aware_dt, "Europe/London")


@pytest.fixture(scope="module")
def reference_chart():
    dt_utc = local_time_to_utc(datetime(2000, 1, 1, 12, 0, 0), "Europe/London")
    return compute_chart(dt_utc, lat=51.5074, lon=-0.1278)


def test_lagna(reference_chart):
    # Verified directly against pyswisseph (Lahiri sidereal, whole-sign)
    # independently of the astrologer-supplied reference figure for this
    # point, which did not reproduce under any tested convention.
    assert reference_chart.lagna_sign_name == "Aries"
    assert abs(reference_chart.lagna_degrees_in_sign - 0.16) <= TOLERANCE_DEG
    assert reference_chart.lagna_nakshatra == "Ashwini"
    assert reference_chart.lagna_pada == 1


def test_sun(reference_chart):
    assert_position(reference_chart.planets["Sun"], "Sagittarius", 16.52, "Purva Ashadha")


def test_moon(reference_chart):
    assert_position(reference_chart.planets["Moon"], "Libra", 19.47, "Swati")


def test_mars(reference_chart):
    assert_position(reference_chart.planets["Mars"], "Aquarius", 4.11, "Dhanishta")


def test_mercury(reference_chart):
    assert_position(reference_chart.planets["Mercury"], "Sagittarius", 8.04, "Mula")


def test_jupiter(reference_chart):
    assert_position(reference_chart.planets["Jupiter"], "Aries", 1.40, "Ashwini")


def test_venus(reference_chart):
    assert_position(reference_chart.planets["Venus"], "Scorpio", 7.71, "Anuradha")


def test_saturn(reference_chart):
    saturn = reference_chart.planets["Saturn"]
    assert_position(saturn, "Aries", 16.54, "Bharani")
    assert saturn.debilitated is True
    assert saturn.exalted is False
    assert saturn.own_sign is False


def test_rahu(reference_chart):
    assert_position(reference_chart.planets["Rahu"], "Cancer", 11.19, "Pushya")


def test_ketu(reference_chart):
    assert_position(reference_chart.planets["Ketu"], "Capricorn", 11.19, "Shravana")


def test_houses_are_whole_sign_from_lagna(reference_chart):
    lagna_sign = reference_chart.lagna_sign
    for position in reference_chart.planets.values():
        expected_house = (position.sign - lagna_sign) % 12 + 1
        assert position.house == expected_house
