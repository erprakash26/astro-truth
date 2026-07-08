from datetime import datetime, timedelta, timezone

import pytest

from app.dasha import current_dasha, vimshottari

MOON_LONGITUDE = 199.4706  # Libra, Swati - reference chart from Stage 1
BIRTH_DT = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

TOLERANCE = timedelta(days=2)


def assert_close(actual: datetime, expected: datetime):
    assert abs(actual - expected) <= TOLERANCE, f"{actual} not within 2 days of {expected}"


@pytest.fixture(scope="module")
def sequence():
    return vimshottari(MOON_LONGITUDE, BIRTH_DT)


def test_moons_nakshatra_lord_is_rahu_and_starts_the_sequence(sequence):
    assert sequence[0].lord == "Rahu"
    assert sequence[0].start == BIRTH_DT


def test_rahu_mahadasha_balance(sequence):
    rahu = sequence[0]
    assert_close(rahu.end, datetime(2000, 9, 18, tzinfo=timezone.utc))
    balance_years = (rahu.end - rahu.start).days / 365.25
    assert abs(balance_years - 0.71) <= 0.02


def test_jupiter_mahadasha(sequence):
    jupiter = sequence[1]
    assert jupiter.lord == "Jupiter"
    assert_close(jupiter.start, datetime(2000, 9, 18, tzinfo=timezone.utc))
    assert_close(jupiter.end, datetime(2016, 9, 18, tzinfo=timezone.utc))


def test_saturn_mahadasha(sequence):
    saturn = sequence[2]
    assert saturn.lord == "Saturn"
    assert_close(saturn.start, datetime(2016, 9, 18, tzinfo=timezone.utc))
    assert_close(saturn.end, datetime(2035, 9, 19, tzinfo=timezone.utc))


def test_jupiter_antardasha_boundaries(sequence):
    jupiter = sequence[1]
    antardashas = {a.lord: a for a in jupiter.antardashas}

    assert list(antardashas.keys())[:5] == ["Jupiter", "Saturn", "Mercury", "Ketu", "Venus"]

    assert_close(antardashas["Jupiter"].end, datetime(2002, 11, 6, tzinfo=timezone.utc))
    assert_close(antardashas["Saturn"].end, datetime(2005, 5, 19, tzinfo=timezone.utc))
    assert_close(antardashas["Venus"].end, datetime(2011, 4, 1, tzinfo=timezone.utc))

    rahu_antardasha = jupiter.antardashas[-1]
    assert rahu_antardasha.lord == "Rahu"
    assert_close(rahu_antardasha.end, datetime(2016, 9, 17, tzinfo=timezone.utc))
    assert rahu_antardasha.end == jupiter.end


def test_antardashas_sum_to_mahadasha_span(sequence):
    microsecond = timedelta(microseconds=1)
    for maha in sequence:
        assert maha.antardashas[0].start == maha.start
        assert abs(maha.antardashas[-1].end - maha.end) <= microsecond
        for a, b in zip(maha.antardashas, maha.antardashas[1:]):
            assert a.end == b.start


def test_current_dasha_inside_jupiter_saturn_antardasha(sequence):
    now = datetime(2003, 6, 1, tzinfo=timezone.utc)
    result = current_dasha(sequence, now)
    assert result is not None
    maha, antar = result
    assert maha.lord == "Jupiter"
    assert antar.lord == "Saturn"


def test_current_dasha_none_outside_sequence(sequence):
    before_birth = datetime(1999, 1, 1, tzinfo=timezone.utc)
    assert current_dasha(sequence, before_birth) is None
