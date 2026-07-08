"""Pure, deterministic Vedic chart computation. No I/O, no LLM calls.

Sidereal zodiac (Lahiri ayanamsa), whole-sign houses, mean lunar node.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import swisseph as swe
from pydantic import BaseModel

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0

PLANET_CODES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}

# Classical (BPHS) sign-level dignities. Rahu/Ketu are excluded: their
# exaltation/debilitation signs are not agreed upon across traditions.
EXALTATION_SIGN = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6,
}
OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
}
# (sign_index, degree_start, degree_end) within the sign.
MOOLATRIKONA = {
    "Sun": (4, 0.0, 20.0),
    "Moon": (1, 4.0, 20.0),
    "Mars": (0, 0.0, 12.0),
    "Mercury": (5, 16.0, 20.0),
    "Jupiter": (8, 0.0, 10.0),
    "Venus": (6, 0.0, 15.0),
    "Saturn": (10, 0.0, 20.0),
}

CALC_FLAGS = swe.FLG_SIDEREAL | swe.FLG_MOSEPH


class PlanetPosition(BaseModel):
    name: str
    longitude: float
    sign: int
    sign_name: str
    degrees_in_sign: float
    nakshatra: str
    nakshatra_index: int
    pada: int
    house: int
    exalted: bool = False
    debilitated: bool = False
    own_sign: bool = False
    moolatrikona: bool = False


class Chart(BaseModel):
    datetime_utc: datetime
    lat: float
    lon: float
    ayanamsa: float
    lagna_longitude: float
    lagna_sign: int
    lagna_sign_name: str
    lagna_degrees_in_sign: float
    lagna_nakshatra: str
    lagna_nakshatra_index: int
    lagna_pada: int
    planets: dict[str, PlanetPosition]


def local_time_to_utc(local_dt: datetime, tz_name: str) -> datetime:
    """Convert a naive local birth datetime + IANA timezone name to aware UTC.

    Uses zoneinfo so fractional-hour offsets (e.g. Asia/Kathmandu, UTC+5:45)
    and DST transitions resolve correctly for the given date.
    """
    if local_dt.tzinfo is not None:
        raise ValueError("local_dt must be naive; timezone is supplied via tz_name")
    return local_dt.replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc)


def _sign_and_degrees(longitude: float) -> tuple[int, float]:
    sign = int(longitude // 30) % 12
    return sign, longitude - sign * 30


def _nakshatra_and_pada(longitude: float) -> tuple[int, int]:
    nakshatra_index = int(longitude // NAKSHATRA_SPAN) % 27
    degrees_into_nakshatra = longitude - nakshatra_index * NAKSHATRA_SPAN
    pada = int(degrees_into_nakshatra // PADA_SPAN) + 1
    return nakshatra_index, pada


def _dignity_flags(name: str, sign: int, degrees_in_sign: float) -> dict[str, bool]:
    exalted = EXALTATION_SIGN.get(name) == sign
    debilitated = EXALTATION_SIGN.get(name) is not None and (EXALTATION_SIGN[name] + 6) % 12 == sign
    own_sign = sign in OWN_SIGNS.get(name, [])
    moolatrikona = False
    moola = MOOLATRIKONA.get(name)
    if moola is not None:
        moola_sign, start, end = moola
        moolatrikona = sign == moola_sign and start <= degrees_in_sign < end
    return {
        "exalted": exalted,
        "debilitated": debilitated,
        "own_sign": own_sign,
        "moolatrikona": moolatrikona,
    }


def _build_planet(name: str, longitude: float, lagna_sign: int) -> PlanetPosition:
    longitude %= 360
    sign, degrees_in_sign = _sign_and_degrees(longitude)
    nakshatra_index, pada = _nakshatra_and_pada(longitude)
    house = (sign - lagna_sign) % 12 + 1
    return PlanetPosition(
        name=name,
        longitude=longitude,
        sign=sign,
        sign_name=SIGNS[sign],
        degrees_in_sign=degrees_in_sign,
        nakshatra=NAKSHATRAS[nakshatra_index],
        nakshatra_index=nakshatra_index,
        pada=pada,
        house=house,
        **_dignity_flags(name, sign, degrees_in_sign),
    )


def compute_chart(dt_utc: datetime, lat: float, lon: float) -> Chart:
    """Compute a full sidereal (Lahiri) chart, whole-sign houses, mean node.

    dt_utc must be timezone-aware. Use local_time_to_utc to convert a local
    birth time first.
    """
    if dt_utc.tzinfo is None:
        raise ValueError("dt_utc must be timezone-aware")
    dt_utc = dt_utc.astimezone(timezone.utc)

    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    jd_ut = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600,
    )

    ayanamsa = swe.get_ayanamsa_ut(jd_ut)

    _cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b"W", CALC_FLAGS)
    lagna_longitude = ascmc[0] % 360
    lagna_sign, lagna_degrees_in_sign = _sign_and_degrees(lagna_longitude)
    lagna_nakshatra_index, lagna_pada = _nakshatra_and_pada(lagna_longitude)

    planets: dict[str, PlanetPosition] = {}
    for name, code in PLANET_CODES.items():
        xx, _ret = swe.calc_ut(jd_ut, code, CALC_FLAGS)
        planets[name] = _build_planet(name, xx[0], lagna_sign)

    rahu_xx, _ret = swe.calc_ut(jd_ut, swe.MEAN_NODE, CALC_FLAGS)
    rahu_longitude = rahu_xx[0] % 360
    planets["Rahu"] = _build_planet("Rahu", rahu_longitude, lagna_sign)
    planets["Ketu"] = _build_planet("Ketu", rahu_longitude + 180, lagna_sign)

    return Chart(
        datetime_utc=dt_utc,
        lat=lat,
        lon=lon,
        ayanamsa=ayanamsa,
        lagna_longitude=lagna_longitude,
        lagna_sign=lagna_sign,
        lagna_sign_name=SIGNS[lagna_sign],
        lagna_degrees_in_sign=lagna_degrees_in_sign,
        lagna_nakshatra=NAKSHATRAS[lagna_nakshatra_index],
        lagna_nakshatra_index=lagna_nakshatra_index,
        lagna_pada=lagna_pada,
        planets=planets,
    )
