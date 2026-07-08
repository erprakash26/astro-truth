"""Current (gochara) transits of Jupiter and Saturn.

Sidereal (Lahiri ayanamsa), whole-sign houses — consistent with
app.engine. current_transits() takes `now` as an explicit parameter
rather than reading the system clock internally, keeping it a pure
function of its inputs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import swisseph as swe
from pydantic import BaseModel

from app.engine import CALC_FLAGS, SIGNS

TRANSIT_PLANET_CODES = {
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
}

# Coarse step for the forward scan before bisection narrows the crossing.
# Jupiter/Saturn move well under a degree in 5 days, so a single sign
# change cannot be missed between samples.
_SCAN_STEP = timedelta(days=5)
_MAX_SEARCH_HORIZON = timedelta(days=1500)  # comfortably covers Saturn's ~2.9yr transit
_BISECTION_ITERATIONS = 40


class TransitPlanet(BaseModel):
    name: str
    longitude: float
    sign: int
    sign_name: str
    degrees_in_sign: float
    house_from_lagna: int
    house_from_moon: int
    next_ingress: datetime


class Transits(BaseModel):
    computed_at: datetime
    jupiter: TransitPlanet
    saturn: TransitPlanet


def _sign_and_degrees(longitude: float) -> tuple[int, float]:
    sign = int(longitude // 30) % 12
    return sign, longitude - sign * 30


def _sidereal_longitude(dt_utc: datetime, planet_code: int) -> float:
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    jd_ut = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600,
    )
    xx, _ret = swe.calc_ut(jd_ut, planet_code, CALC_FLAGS)
    return xx[0] % 360


def _find_next_ingress(dt_utc: datetime, planet_code: int, current_sign: int) -> datetime:
    """First moment after dt_utc at which the planet's sidereal sign differs
    from current_sign, found by a coarse forward scan then bisection."""
    lo = dt_utc
    hi = dt_utc
    horizon = dt_utc + _MAX_SEARCH_HORIZON
    while hi < horizon:
        lo = hi
        hi = hi + _SCAN_STEP
        sign, _ = _sign_and_degrees(_sidereal_longitude(hi, planet_code))
        if sign != current_sign:
            break
    else:
        raise RuntimeError(
            f"No sign change found for planet code {planet_code} within "
            f"{_MAX_SEARCH_HORIZON.days} days"
        )

    for _ in range(_BISECTION_ITERATIONS):
        mid = lo + (hi - lo) / 2
        sign, _ = _sign_and_degrees(_sidereal_longitude(mid, planet_code))
        if sign == current_sign:
            lo = mid
        else:
            hi = mid
    return hi


def compute_transits(lagna_sign: int, moon_sign: int, now: datetime) -> Transits:
    """Current Jupiter/Saturn transits, houses from natal lagna and Moon.

    now must be timezone-aware. lagna_sign / moon_sign are 0-indexed
    natal sign positions (0 = Aries), matching Chart.lagna_sign and
    PlanetPosition.sign from app.engine.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)

    planets: dict[str, TransitPlanet] = {}
    for name, code in TRANSIT_PLANET_CODES.items():
        longitude = _sidereal_longitude(now, code)
        sign, degrees_in_sign = _sign_and_degrees(longitude)
        next_ingress = _find_next_ingress(now, code, sign)
        planets[name] = TransitPlanet(
            name=name,
            longitude=longitude,
            sign=sign,
            sign_name=SIGNS[sign],
            degrees_in_sign=degrees_in_sign,
            house_from_lagna=(sign - lagna_sign) % 12 + 1,
            house_from_moon=(sign - moon_sign) % 12 + 1,
            next_ingress=next_ingress,
        )

    return Transits(computed_at=now, jupiter=planets["Jupiter"], saturn=planets["Saturn"])
