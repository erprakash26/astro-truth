"""Tool functions over an ALREADY-COMPUTED chart JSON, for follow-up chat.

Every function here is a pure lookup or filter on data app.engine,
app.dasha, and app.transits have already computed and stored — none of
them perform any new astronomical computation. This is what lets the
chat LLM (app.chat) answer questions via tool use instead of free-
inventing facts: it can only ever report what's already in the chart.

`stored` throughout is the same dict shape returned by POST /api/chart
and consumed by app.pdf / app.interpret: {chart, dasha_timeline,
current_dasha, transits, ...}.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.interpret import detect_yogas

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DIGNITY_FLAGS = ("exalted", "own_sign", "moolatrikona", "debilitated")
TRANSIT_PLANETS = ("Jupiter", "Saturn")


class ChartToolError(ValueError):
    """A tool was asked about something this chart doesn't have (unknown
    planet, out-of-range date, untracked transit planet, ...). Callers
    (mock pattern matcher, real tool-use loop) turn this into a plain
    message rather than a crash."""


def _normalize_planet_name(chart: dict, planet_name: str) -> str:
    for name in chart["planets"]:
        if name.lower() == planet_name.strip().lower():
            return name
    raise ChartToolError(
        f'Unknown planet "{planet_name}". This chart has: {", ".join(PLANET_ORDER)}.'
    )


def get_planet(stored: dict, planet_name: str) -> dict:
    """Sign, degree, house, dignity, and nakshatra for one planet."""
    chart = stored["chart"]
    name = _normalize_planet_name(chart, planet_name)
    planet = chart["planets"][name]
    dignity = next((flag for flag in DIGNITY_FLAGS if planet.get(flag)), None)
    return {
        "planet": name,
        "sign": planet["sign_name"],
        "degrees_in_sign": planet["degrees_in_sign"],
        "house": planet["house"],
        "dignity": dignity,
        "nakshatra": planet["nakshatra"],
        "pada": planet["pada"],
    }


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_dasha_at(stored: dict, on_date: str) -> dict:
    """Active mahadasha/antardasha lords for a calendar date, looked up
    from this chart's already-computed Vimshottari dasha timeline."""
    try:
        target = _parse_iso(on_date)
    except ValueError as exc:
        raise ChartToolError(
            f'Could not parse "{on_date}" as a date; use YYYY-MM-DD.'
        ) from exc

    for maha in stored["dasha_timeline"]:
        maha_start, maha_end = _parse_iso(maha["start"]), _parse_iso(maha["end"])
        if not (maha_start <= target < maha_end):
            continue
        antar_match = next(
            (
                antar
                for antar in maha["antardashas"]
                if _parse_iso(antar["start"]) <= target < _parse_iso(antar["end"])
            ),
            maha["antardashas"][-1],
        )
        return {
            "date": on_date,
            "mahadasha": maha["lord"],
            "mahadasha_start": maha["start"],
            "mahadasha_end": maha["end"],
            "antardasha": antar_match["lord"],
            "antardasha_start": antar_match["start"],
            "antardasha_end": antar_match["end"],
        }
    raise ChartToolError(f'"{on_date}" falls outside this chart\'s computed dasha timeline.')


def get_transit(stored: dict, planet_name: str) -> dict:
    """Current transit (gochara) position for Jupiter or Saturn — the only
    two planets this app tracks in transit."""
    transits = stored.get("transits")
    if not transits:
        raise ChartToolError("No transit data is available for this chart.")

    key = planet_name.strip().lower()
    if key not in ("jupiter", "saturn"):
        raise ChartToolError(
            f'Transit tracking is only available for Jupiter and Saturn, not "{planet_name}".'
        )
    t = transits[key]
    return {
        "planet": t["name"],
        "sign": t["sign_name"],
        "degrees_in_sign": t["degrees_in_sign"],
        "house_from_lagna": t["house_from_lagna"],
        "house_from_moon": t["house_from_moon"],
        "next_ingress": t["next_ingress"],
    }


def get_yogas(stored: dict) -> list[dict]:
    """Yogas present in this chart — same detection app.interpret uses for
    the mock/real interpretation, so chat answers never disagree with it."""
    return detect_yogas(stored["chart"])
