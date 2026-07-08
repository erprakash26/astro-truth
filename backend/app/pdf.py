"""PDF export of a computed chart, rendered from a single HTML template
via headless Chromium (Playwright's page.pdf()).

WeasyPrint was tried first but its native Pango/Cairo/GObject libraries
are not resolvable on this Windows host; headless Chromium avoids that
dependency entirely while keeping one HTML/CSS template as the source of
truth (no separate PDF-only layout to maintain).
"""

from __future__ import annotations

import base64
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from app.interpret import DISCLAIMER, interpret_chart_text

APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
FONT_PATH = APP_DIR / "static" / "fonts" / "NotoSansDevanagari-Regular.ttf"

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

SIGN_NAMES = {
    "en": [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ],
    "ne": [
        "मेष", "वृष", "मिथुन", "कर्कट", "सिंह", "कन्या",
        "तुला", "वृश्चिक", "धनु", "मकर", "कुम्भ", "मीन",
    ],
}

TRANSIT_PLANET_NAMES = {
    "en": {"Jupiter": "Jupiter", "Saturn": "Saturn"},
    "ne": {"Jupiter": "बृहस्पति", "Saturn": "शनि"},
}

HOUSE_ORDINALS = {
    "en": ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"],
    "ne": [
        "पहिलो", "दोस्रो", "तेस्रो", "चौथो", "पाँचौं", "छैटौं",
        "सातौं", "आठौं", "नवौं", "दशौं", "एघारौं", "बाह्रौं",
    ],
}

FOOTER_DISCLAIMER = {
    "en": DISCLAIMER,
    "ne": (
        "ज्योतिषशास्त्र एक परम्परागत विश्वास प्रणाली हो, विज्ञान होइन। "
        "यसले निश्चितता होइन, प्रवृत्तिहरू मात्र वर्णन गर्छ।"
    ),
}

LABELS = {
    "en": {
        "app_name": "AstroTruth",
        "chart_title": "Kundali Chart",
        "lagna": "Lagna",
        "planets": "Planets",
        "graha": "Graha",
        "sign": "Sign",
        "degree": "Degree",
        "nakshatra_pada": "Nakshatra / Pada",
        "house": "House",
        "dignity": "Dignity",
        "transits": "Current Transits",
        "from_lagna": "from Lagna",
        "from_moon": "from Moon",
        "next_ingress": "Next sign change",
        "dasha_timeline": "Vimshottari Dasha Timeline",
        "mahadasha": "Mahadasha",
        "antardasha": "Antardasha",
        "start": "Start",
        "end": "End",
        "current": "Current",
        "interpretation": "Interpretation",
    },
    "ne": {
        "app_name": "AstroTruth",
        "chart_title": "कुण्डली चक्र",
        "lagna": "लग्न",
        "planets": "ग्रहहरू",
        "graha": "ग्रह",
        "sign": "राशि",
        "degree": "डिग्री",
        "nakshatra_pada": "नक्षत्र / पाद",
        "house": "भाव",
        "dignity": "स्थिति",
        "transits": "हालको गोचर",
        "from_lagna": "लग्नबाट",
        "from_moon": "चन्द्रमाबाट",
        "next_ingress": "अर्को राशि परिवर्तन",
        "dasha_timeline": "विंशोत्तरी दशा समयरेखा",
        "mahadasha": "महादशा",
        "antardasha": "अन्तर्दशा",
        "start": "सुरु",
        "end": "अन्त्य",
        "current": "हालको",
        "interpretation": "व्याख्या",
    },
}

DIGNITY_LABELS = {
    "en": {"exalted": "Exalted", "own_sign": "Own sign", "debilitated": "Debilitated", "moolatrikona": "Moolatrikona"},
    "ne": {"exalted": "उच्च", "own_sign": "स्वराशि", "debilitated": "नीच", "moolatrikona": "मूलत्रिकोण"},
}

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _ordinal(language: str, house: int) -> str:
    ordinals = HOUSE_ORDINALS.get(language, HOUSE_ORDINALS["en"])
    return ordinals[house - 1] if 1 <= house <= 12 else str(house)


def _sign_name(language: str, sign: int) -> str:
    names = SIGN_NAMES.get(language, SIGN_NAMES["en"])
    return names[sign]


def _dignity_label(language: str, planet: dict) -> str | None:
    labels = DIGNITY_LABELS.get(language, DIGNITY_LABELS["en"])
    if planet.get("exalted"):
        return labels["exalted"]
    if planet.get("own_sign"):
        return labels["own_sign"]
    if planet.get("moolatrikona"):
        return labels["moolatrikona"]
    if planet.get("debilitated"):
        return labels["debilitated"]
    return None


def _parse_interpretation(text: str) -> list[dict]:
    """Split "## heading" / paragraph lines into renderable blocks."""
    blocks: list[dict] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            blocks.append({"type": "heading", "text": line[3:]})
        else:
            blocks.append({"type": "paragraph", "text": line})
    return blocks


def _font_data_uri() -> str:
    data = FONT_PATH.read_bytes()
    return "data:font/ttf;base64," + base64.b64encode(data).decode("ascii")


def _mahadasha_rows(dasha_timeline: list[dict], current_dasha: dict | None) -> list[dict]:
    """One row per mahadasha; the currently active one also carries its full
    antardasha breakdown (mirrors the web page, where only the active
    mahadasha's antardashas are shown by default)."""
    current_maha_start = current_dasha["mahadasha"]["start"] if current_dasha else None
    current_antar_start = current_dasha["antardasha"]["start"] if current_dasha else None

    rows = []
    for period in dasha_timeline:
        is_current = current_maha_start is not None and period["start"] == current_maha_start
        antardasha_rows = (
            [
                {
                    "lord": antar["lord"],
                    "start": antar["start"],
                    "end": antar["end"],
                    "is_current": current_antar_start is not None and antar["start"] == current_antar_start,
                }
                for antar in period["antardashas"]
            ]
            if is_current
            else []
        )
        rows.append(
            {
                "lord": period["lord"],
                "start": period["start"],
                "end": period["end"],
                "is_current": is_current,
                "antardasha_rows": antardasha_rows,
            }
        )
    return rows


def render_chart_html(stored: dict, language: str) -> str:
    chart = stored["chart"]
    planets = [chart["planets"][name] for name in PLANET_ORDER if name in chart["planets"]]
    planet_rows = [
        {
            **planet,
            "sign_name_localized": _sign_name(language, planet["sign"]),
            "dignity_label": _dignity_label(language, planet),
        }
        for planet in planets
    ]

    transits = stored.get("transits")
    transit_cards = None
    if transits:
        transit_cards = [
            {
                **transits[key],
                "display_name": TRANSIT_PLANET_NAMES.get(language, TRANSIT_PLANET_NAMES["en"])[
                    transits[key]["name"]
                ],
                "sign_name_localized": _sign_name(language, transits[key]["sign"]),
                "house_from_lagna_label": _ordinal(language, transits[key]["house_from_lagna"]),
                "house_from_moon_label": _ordinal(language, transits[key]["house_from_moon"]),
            }
            for key in ("jupiter", "saturn")
        ]

    interpretation_text = interpret_chart_text(stored, language)

    template = _env.get_template("chart_pdf.html")
    return template.render(
        language=language,
        labels=LABELS.get(language, LABELS["en"]),
        font_data_uri=_font_data_uri(),
        lagna_sign_name=_sign_name(language, chart["lagna_sign"]),
        chart=chart,
        planet_rows=planet_rows,
        mahadasha_rows=_mahadasha_rows(stored["dasha_timeline"], stored.get("current_dasha")),
        current_dasha=stored.get("current_dasha"),
        transit_cards=transit_cards,
        interpretation_blocks=_parse_interpretation(interpretation_text),
        disclaimer=FOOTER_DISCLAIMER.get(language, FOOTER_DISCLAIMER["en"]),
    )


async def render_chart_pdf(stored: dict, language: str) -> bytes:
    html = render_chart_html(stored, language)
    disclaimer = FOOTER_DISCLAIMER.get(language, FOOTER_DISCLAIMER["en"])
    footer_template = f"""
        <div style="font-size:8px; width:100%; text-align:center; color:#6b1a24;
                    padding:0 24px; font-family: Arial, sans-serif;">
          {disclaimer} &middot; <span class="pageNumber"></span>/<span class="totalPages"></span>
        </div>
    """

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(html, wait_until="load")
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=footer_template,
                margin={"top": "20mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            )
        finally:
            await browser.close()

    return pdf_bytes
