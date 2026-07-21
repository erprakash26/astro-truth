"""Offline ISO 639-1 language lookup, backed by a bundled JSON dataset. No
network calls.

Reads app/data/languages.json once at import time (~184 languages, generated
by scripts/generate_languages.py from pycountry's ISO 639 data).
"""

import json
from pathlib import Path

from pydantic import BaseModel

DATA_PATH = Path(__file__).resolve().parent / "data" / "languages.json"


class Language(BaseModel):
    name: str
    code: str


def _load_languages() -> list[Language]:
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return [Language(**entry) for entry in raw]


LANGUAGES: list[Language] = _load_languages()


def search_languages(query: str, limit: int = 20) -> list[Language]:
    """Case-insensitive substring search over language name."""
    query = query.strip().lower()
    if not query:
        return LANGUAGES[:limit]

    matches = [lang for lang in LANGUAGES if query in lang.name.lower()]

    def sort_key(lang: Language) -> tuple[int, str]:
        starts_with = 0 if lang.name.lower().startswith(query) else 1
        return starts_with, lang.name

    matches.sort(key=sort_key)
    return matches[:limit]
