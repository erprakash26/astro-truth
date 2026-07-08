"""Pure, deterministic Vimshottari dasha calculations. No I/O.

current_dasha() takes `now` as an explicit parameter rather than reading
the system clock internally, keeping it a pure function of its inputs.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel

from app.engine import NAKSHATRA_SPAN

DAYS_PER_YEAR = 365.25

LORD_ORDER = [
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury",
]

DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

TOTAL_CYCLE_YEARS = 120


class DashaPeriod(BaseModel):
    lord: str
    start: datetime
    end: datetime
    antardashas: list["DashaPeriod"] = []


def _years_to_timedelta(years: float) -> timedelta:
    return timedelta(days=years * DAYS_PER_YEAR)


def _nakshatra_lord(moon_longitude: float) -> tuple[int, str]:
    nakshatra_index = int(moon_longitude // NAKSHATRA_SPAN) % 27
    return nakshatra_index, LORD_ORDER[nakshatra_index % 9]


def _antardashas(maha_lord: str, start: datetime, maha_years: float) -> list[DashaPeriod]:
    start_index = LORD_ORDER.index(maha_lord)
    periods = []
    cursor = start
    for offset in range(9):
        antar_lord = LORD_ORDER[(start_index + offset) % 9]
        duration_years = maha_years * DASHA_YEARS[antar_lord] / TOTAL_CYCLE_YEARS
        end = cursor + _years_to_timedelta(duration_years)
        periods.append(DashaPeriod(lord=antar_lord, start=cursor, end=end))
        cursor = end
    return periods


def vimshottari(moon_longitude: float, birth_dt: datetime) -> list[DashaPeriod]:
    """Full Vimshottari mahadasha sequence (120-year cycle) from birth.

    moon_longitude is the sidereal (Lahiri) longitude in degrees.
    """
    moon_longitude %= 360
    nakshatra_index, first_lord = _nakshatra_lord(moon_longitude)

    degrees_into_nakshatra = moon_longitude - nakshatra_index * NAKSHATRA_SPAN
    fraction_elapsed = degrees_into_nakshatra / NAKSHATRA_SPAN
    first_balance_years = DASHA_YEARS[first_lord] * (1 - fraction_elapsed)

    start_index = LORD_ORDER.index(first_lord)
    periods: list[DashaPeriod] = []
    cursor = birth_dt
    for offset in range(9):
        lord = LORD_ORDER[(start_index + offset) % 9]
        maha_years = first_balance_years if offset == 0 else DASHA_YEARS[lord]
        end = cursor + _years_to_timedelta(maha_years)
        periods.append(
            DashaPeriod(
                lord=lord,
                start=cursor,
                end=end,
                antardashas=_antardashas(lord, cursor, maha_years),
            )
        )
        cursor = end
    return periods


def current_dasha(
    sequence: list[DashaPeriod], now: datetime
) -> tuple[DashaPeriod, DashaPeriod] | None:
    """Active (mahadasha, antardasha) pair for `now`, or None if out of range."""
    for maha in sequence:
        if maha.start <= now < maha.end:
            for antar in maha.antardashas:
                if antar.start <= now < antar.end:
                    return maha, antar
            return maha, maha.antardashas[-1]
    return None
