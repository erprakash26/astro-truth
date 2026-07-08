"""Offline city lookup, backed by a bundled JSON dataset. No network calls.

Reads app/data/cities.json once at import time (~200 cities: all 77 Nepal
district headquarters plus major US/world cities).
"""

import json
from pathlib import Path

from pydantic import BaseModel

DATA_PATH = Path(__file__).resolve().parent / "data" / "cities.json"


class City(BaseModel):
    id: str
    name: str
    admin: str | None = None
    country: str
    lat: float
    lon: float
    timezone: str


def _load_cities() -> list[City]:
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return [City(**entry) for entry in raw]


CITIES: list[City] = _load_cities()
_CITIES_BY_ID: dict[str, City] = {city.id: city for city in CITIES}


def get_city(city_id: str) -> City | None:
    return _CITIES_BY_ID.get(city_id)


def search_cities(query: str, limit: int = 20) -> list[City]:
    """Case-insensitive substring search over city name, admin, and country."""
    query = query.strip().lower()
    if not query:
        return CITIES[:limit]

    matches = [
        city
        for city in CITIES
        if query in city.name.lower()
        or query in city.country.lower()
        or (city.admin is not None and query in city.admin.lower())
    ]

    def sort_key(city: City) -> tuple[int, str]:
        starts_with = 0 if city.name.lower().startswith(query) else 1
        return starts_with, city.name

    matches.sort(key=sort_key)
    return matches[:limit]
