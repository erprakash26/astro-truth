"""Grounding eval for app.interpret's mock-mode interpretations.

Not a unit test of a single function's return value — this checks a
*property* that must hold for any chart, in either language: every
{Planet, Sign} claim the generated text makes must be traceable to a real
field in the chart JSON it was given. See EVALS.md for why this is
rule-based rather than an LLM judge, and how to add an LLM-judge eval
later behind USE_MOCK_LLM=false.

Runs against three distinct, previously-verified birth charts (see
tests/test_regression.py for the same three) so the check isn't just
validating one hand-written example against itself.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from app.dasha import current_dasha, vimshottari
from app.engine import compute_chart, local_time_to_utc
from app.interpret import DISCLAIMER, DISCLAIMER_NE, PLANET_NAME_NE, SIGN_NAME_NE, interpret_chart_text
from app.transits import compute_transits

# ---------------------------------------------------------------------------
# Chart fixtures: same three charts as tests/test_regression.py.
# ---------------------------------------------------------------------------


def _build_stored(dt: datetime, tz: str, lat: float, lon: float) -> dict:
    dt_utc = local_time_to_utc(dt, tz)
    chart = compute_chart(dt_utc, lat=lat, lon=lon)
    dasha_sequence = vimshottari(chart.planets["Moon"].longitude, dt_utc)
    now = datetime.now(timezone.utc)
    current = current_dasha(dasha_sequence, now)
    transits = compute_transits(chart.lagna_sign, chart.planets["Moon"].sign, now)
    return {
        "chart": chart.model_dump(mode="json"),
        "dasha_timeline": [period.model_dump(mode="json") for period in dasha_sequence],
        "current_dasha": (
            {
                "mahadasha": current[0].model_dump(mode="json"),
                "antardasha": current[1].model_dump(mode="json"),
            }
            if current is not None
            else None
        ),
        "transits": transits.model_dump(mode="json"),
    }


CHARTS = {
    "london_reference": dict(dt=datetime(2000, 1, 1, 12, 0, 0), tz="Europe/London", lat=51.5074, lon=-0.1278),
    # UTC+5:45 fractional-hour timezone edge case.
    "kathmandu": dict(dt=datetime(1995, 5, 15, 6, 30, 0), tz="Asia/Kathmandu", lat=27.7129, lon=85.3228),
    "new_york": dict(dt=datetime(1985, 11, 2, 14, 15, 0), tz="America/New_York", lat=40.7128, lon=-74.006),
}


@pytest.fixture(scope="module", params=list(CHARTS.items()), ids=list(CHARTS.keys()))
def stored_chart(request):
    name, spec = request.param
    return name, _build_stored(**spec)


# ---------------------------------------------------------------------------
# Rule-based {Planet, Sign} extraction.
#
# For each sentence, every planet mention is paired with a sign mention via
# two passes:
#   1. Forward span: a planet pairs with the sign found between its own
#      position and the next planet mention, if exactly one sign is there.
#      Handles "Moon (7th house, Libra) and Jupiter (1st house, Aries)".
#   2. Backward inheritance: a planet with no pair from pass 1 inherits the
#      next planet's sign. Handles "Sun and Mercury are conjunct in ...
#      Sagittarius" (the sign follows both names, not just the second).
#      This is sound here because whole-sign houses guarantee two planets
#      in the same house are also in the same sign.
# ---------------------------------------------------------------------------

EN_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
EN_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
NE_PLANET_TO_EN = {v: k for k, v in PLANET_NAME_NE.items()}
NE_SIGN_TO_EN = {v: k for k, v in SIGN_NAME_NE.items()}
ALL_PLANET_NAMES = EN_PLANETS + list(PLANET_NAME_NE.values())
ALL_SIGN_NAMES = EN_SIGNS + list(SIGN_NAME_NE.values())
TRANSIT_KEYWORDS = ("transit", "गोचर", "ट्रान्जिट")

# Phrases that legitimately juxtapose a planet name with a sign name without
# making a position claim, and would otherwise produce false positives:
#   - Yoga names ("Budhaditya Yoga") are proper nouns, not sentences about
#     where a planet sits — and "बुधादित्य" contains "बुध" (Mercury) as a
#     literal substring, a real false-match caught while building this eval.
#   - "ruled by Mars" / "...जसलाई मंगलले शासन गर्छ" describes which planet
#     *rules* a zodiac sign (fixed astrological fact), not where that planet
#     is currently placed — also caught as a real false positive.
_MASK_PATTERNS = [
    re.compile(r"Budhaditya(?:\s+Yoga)?"),
    re.compile(r"Gajakesari(?:\s+Yoga)?"),
    re.compile(r"बुधादित्य(?:\s+योग)?"),
    re.compile(r"गजकेसरी(?:\s+योग)?"),
    re.compile(r"ruled by (?:fast-moving |slow-moving )?(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)"),
    re.compile(r"(?:सूर्य|चन्द्रमा|मंगल|बुध|बृहस्पति|शुक्र|शनि|राहु|केतु)ले\s*शासन\s*गर्छ"),
]


def _mask_non_position_mentions(sentence: str) -> str:
    for pattern in _MASK_PATTERNS:
        sentence = pattern.sub(" ", sentence)
    return sentence


def _split_sentences(text: str) -> list[str]:
    # Split on '.', the Devanagari danda '।', and ';' — the strengths/
    # cautions section joins otherwise-independent clauses with semicolons
    # (e.g. "...Aries, its most confident position; Saturn is in its own
    # sign in Aquarius..."), and without this split the pairing logic can
    # reach across an unrelated clause.
    return [s.strip() for s in re.split(r"[.।;]", text) if s.strip()]


def _find_positions(sentence: str, names: list[str]) -> list[tuple[int, str]]:
    hits = [(m.start(), name) for name in names for m in re.finditer(re.escape(name), sentence)]
    hits.sort(key=lambda hit: hit[0])
    return hits


def _is_transit_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(keyword in lowered or keyword in sentence for keyword in TRANSIT_KEYWORDS)


def extract_planet_sign_claims(text: str) -> list[dict]:
    """Every {planet, sign} claim the text makes, in canonical English names."""
    claims = []
    for sentence in _split_sentences(text):
        search_sentence = _mask_non_position_mentions(sentence)
        planet_hits = _find_positions(search_sentence, ALL_PLANET_NAMES)
        sign_hits = _find_positions(search_sentence, ALL_SIGN_NAMES)
        if not planet_hits or not sign_hits:
            continue

        is_transit = _is_transit_sentence(sentence)
        paired_sign: list[str | None] = [None] * len(planet_hits)

        for i, (pos, _name) in enumerate(planet_hits):
            span_end = planet_hits[i + 1][0] if i + 1 < len(planet_hits) else len(sentence) + 1
            in_span = [sign for sign_pos, sign in sign_hits if pos < sign_pos < span_end]
            if len(in_span) == 1:
                paired_sign[i] = in_span[0]

        for i in range(len(planet_hits) - 2, -1, -1):
            if paired_sign[i] is None and paired_sign[i + 1] is not None:
                paired_sign[i] = paired_sign[i + 1]

        for (_pos, planet_raw), sign_raw in zip(planet_hits, paired_sign):
            if sign_raw is None:
                continue
            claims.append(
                {
                    "planet": NE_PLANET_TO_EN.get(planet_raw, planet_raw),
                    "sign": NE_SIGN_TO_EN.get(sign_raw, sign_raw),
                    "is_transit": is_transit,
                    "sentence": sentence,
                }
            )
    return claims


def assert_grounded(chart_json: dict, text: str) -> None:
    chart = chart_json["chart"]
    transits = chart_json.get("transits") or {}
    claims = extract_planet_sign_claims(text)
    assert claims, "extraction found no {Planet, Sign} claims to check — extraction may be broken"

    for claim in claims:
        planet, sign, is_transit = claim["planet"], claim["sign"], claim["is_transit"]
        transit_key = planet.lower()
        if is_transit and transit_key in transits:
            expected = transits[transit_key]["sign_name"]
            source = f"transits.{transit_key}.sign_name"
        elif planet in chart["planets"]:
            expected = chart["planets"][planet]["sign_name"]
            source = f"chart.planets.{planet}.sign_name"
        else:
            continue  # not a recognized planet name; nothing to check
        assert sign == expected, (
            f"GROUNDING FAILURE: text claims {planet} is in {sign} "
            f"(sentence: {claim['sentence']!r}) but {source} is {expected!r}"
        )


# ---------------------------------------------------------------------------
# Banned directive language: mock output must never cross into medical,
# legal, or financial advice, regardless of chart or language.
# ---------------------------------------------------------------------------

BANNED_PHRASES_EN = [
    "you should invest",
    "take this medicine",
    "you will divorce",
    "you should sue",
    "you must divorce",
    "buy this stock",
    "sell your house",
    "take medication",
    "see a doctor immediately",
    "file for divorce",
    "you will get cancer",
]
BANNED_PHRASES_NE = [
    "तपाईंले लगानी गर्नुपर्छ",
    "यो औषधि खानुहोस्",
    "तपाईं पारपाचुके गर्नुहुनेछ",
]


def assert_no_directive_language(text: str) -> None:
    lowered = text.lower()
    for phrase in BANNED_PHRASES_EN:
        assert phrase not in lowered, f"BANNED PHRASE FOUND: {phrase!r}"
    for phrase in BANNED_PHRASES_NE:
        assert phrase not in text, f"BANNED PHRASE FOUND: {phrase!r}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", ["en", "ne"])
def test_interpretation_is_grounded_in_chart_json(stored_chart, language):
    _name, chart_json = stored_chart
    text = interpret_chart_text(chart_json, language)
    assert_grounded(chart_json, text)


@pytest.mark.parametrize("language", ["en", "ne"])
def test_disclaimer_is_present(stored_chart, language):
    _name, chart_json = stored_chart
    text = interpret_chart_text(chart_json, language)
    expected = DISCLAIMER_NE if language == "ne" else DISCLAIMER
    assert expected in text


@pytest.mark.parametrize("language", ["en", "ne"])
def test_no_directive_language(stored_chart, language):
    _name, chart_json = stored_chart
    text = interpret_chart_text(chart_json, language)
    assert_no_directive_language(text)


def test_extractor_finds_claims_on_a_known_sentence():
    """Sanity-check the extractor itself against fixed sentences, so a bug
    in extraction can't silently make test_interpretation_is_grounded_in_...
    pass by finding zero claims."""
    text = (
        "Sun and Mercury are conjunct in your ninth house, Sagittarius, "
        "forming Budhaditya Yoga. Moon sits in the seventh house (Libra) "
        "and Jupiter in the first house (Aries)."
    )
    claims = {(c["planet"], c["sign"]) for c in extract_planet_sign_claims(text)}
    assert ("Sun", "Sagittarius") in claims
    assert ("Mercury", "Sagittarius") in claims
    assert ("Moon", "Libra") in claims
    assert ("Jupiter", "Aries") in claims


def test_extractor_flags_a_deliberately_wrong_claim():
    """Sanity-check that a genuine contradiction is actually caught, so the
    grounding test isn't vacuously passing."""
    chart_json = _build_stored(**CHARTS["london_reference"])
    real_sun_sign = chart_json["chart"]["planets"]["Sun"]["sign_name"]
    wrong_sign = "Pisces" if real_sun_sign != "Pisces" else "Virgo"
    bad_text = f"Sun sits in {wrong_sign}. {DISCLAIMER}"
    with pytest.raises(AssertionError, match="GROUNDING FAILURE"):
        assert_grounded(chart_json, bad_text)
