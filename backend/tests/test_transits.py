from datetime import datetime, timedelta, timezone

import swisseph as swe

from app.engine import CALC_FLAGS
from app.transits import compute_transits

TOLERANCE_DEG = 0.01

# Reference chart: AD 2000-01-01 12:00 Europe/London -> Aries lagna, Libra Moon.
LAGNA_SIGN = 0  # Aries
MOON_SIGN = 6  # Libra


def _independent_sidereal_longitude(dt_utc: datetime, planet_code: int) -> float:
    """Fresh, independent pyswisseph sidereal calculation for `dt_utc`.

    Deliberately re-implemented here (not imported from app.transits) so
    this test verifies against an independent computation, not the same
    code path it is testing.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    jd_ut = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600,
    )
    xx, _ret = swe.calc_ut(jd_ut, planet_code, CALC_FLAGS)
    return xx[0] % 360


def test_jupiter_and_saturn_sign_matches_independent_calculation():
    now = datetime.now(timezone.utc)
    transits = compute_transits(LAGNA_SIGN, MOON_SIGN, now)

    expected_jupiter = _independent_sidereal_longitude(now, swe.JUPITER)
    expected_saturn = _independent_sidereal_longitude(now, swe.SATURN)

    assert abs(transits.jupiter.longitude - expected_jupiter) <= TOLERANCE_DEG
    assert abs(transits.saturn.longitude - expected_saturn) <= TOLERANCE_DEG
    assert transits.jupiter.sign == int(expected_jupiter // 30) % 12
    assert transits.saturn.sign == int(expected_saturn // 30) % 12


def test_houses_from_lagna_and_moon_are_valid_whole_sign_houses():
    now = datetime.now(timezone.utc)
    transits = compute_transits(LAGNA_SIGN, MOON_SIGN, now)

    for planet in (transits.jupiter, transits.saturn):
        assert isinstance(planet.house_from_lagna, int)
        assert isinstance(planet.house_from_moon, int)
        assert 1 <= planet.house_from_lagna <= 12
        assert 1 <= planet.house_from_moon <= 12


def test_next_ingress_is_in_the_future():
    now = datetime.now(timezone.utc)
    transits = compute_transits(LAGNA_SIGN, MOON_SIGN, now)

    assert transits.jupiter.next_ingress > now
    assert transits.saturn.next_ingress > now

    # Sanity bound: the search horizon in app.transits caps at 1500 days,
    # so a returned ingress must fall within that window.
    assert transits.jupiter.next_ingress - now < timedelta(days=1500)
    assert transits.saturn.next_ingress - now < timedelta(days=1500)


# Point-in-time sanity check (not a hard assertion — ephemeris models can
# drift very slightly, and "now" is different every time this suite runs):
# as of 2026-07-08, for our reference chart (Aries lagna, Libra Moon),
# Jupiter is in Cancer (~7.64 degrees in sign), 4th house from lagna and
# 10th house from Moon; Saturn is in Pisces (~20.25 degrees in sign), 12th
# house from lagna and 6th house from Moon.
