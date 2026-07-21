"""One-off script to (re)generate app/data/languages.json. Not part of the app.

Source: pycountry (https://pypi.org/project/pycountry/), which packages the
Debian iso-codes project's ISO 639 data — the standard authoritative source
for language codes. We take every entry that has an ISO 639-1 (two-letter)
code, i.e. the ~184-language set commonly meant by "ISO 639-1 languages".

A handful of ISO 639's own names carry parenthetical qualifiers inherited
from the standard's disambiguation of historical/macrolanguage entries
(e.g. "Nepali (macrolanguage)", "Modern Greek (1453-)"). Trimmed by hand
below for a UI-facing list, same principle as the manual Nepal district
additions in generate_cities.py: the underlying code/coverage is still
sourced, only the display label is cleaned up.
"""

import json
from pathlib import Path

import pycountry

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "languages.json"

NAME_OVERRIDES = {
    "el": "Greek",
    "ia": "Interlingua",
    "ms": "Malay",
    "ne": "Nepali",
    "oc": "Occitan",
    "or": "Oriya",
    "sw": "Swahili",
    "to": "Tongan",
}

languages = [
    {"name": NAME_OVERRIDES.get(lang.alpha_2, lang.name), "code": lang.alpha_2}
    for lang in pycountry.languages
    if hasattr(lang, "alpha_2")
]
languages.sort(key=lambda entry: entry["name"])

codes = [entry["code"] for entry in languages]
assert len(codes) == len(set(codes)), "duplicate language codes found"

print(f"total languages: {len(languages)}")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(languages, f, indent=2, ensure_ascii=False)
