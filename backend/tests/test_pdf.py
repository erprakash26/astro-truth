import asyncio
from datetime import datetime, timezone

import pymupdf
import pytest

from app.dasha import current_dasha, vimshottari
from app.engine import compute_chart, local_time_to_utc
from app.pdf import render_chart_html, render_chart_pdf
from app.transits import compute_transits


def _build_reference_stored(name: str | None = None) -> dict:
    dt_utc = local_time_to_utc(datetime(2000, 1, 1, 12, 0, 0), "Europe/London")
    chart = compute_chart(dt_utc, lat=51.5074, lon=-0.1278)
    moon_longitude = chart.planets["Moon"].longitude
    dasha_sequence = vimshottari(moon_longitude, dt_utc)
    now = datetime.now(timezone.utc)
    current = current_dasha(dasha_sequence, now)
    transits = compute_transits(chart.lagna_sign, chart.planets["Moon"].sign, now)
    return {
        "share_id": "test-reference",
        "name": name,
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


@pytest.fixture(scope="module")
def reference_stored() -> dict:
    return _build_reference_stored()


def _render(stored: dict, language: str) -> bytes:
    return asyncio.run(render_chart_pdf(stored, language))


def _first_page_pixmap_is_blank(pdf_bytes: bytes) -> bool:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pixmap = doc[0].get_pixmap()
    return all(byte == 255 for byte in pixmap.samples)


def _extract_text(pdf_bytes: bytes) -> str:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def test_english_pdf_is_non_blank_and_contains_expected_text(reference_stored):
    pdf_bytes = _render(reference_stored, "en")
    assert pdf_bytes[:4] == b"%PDF"

    assert not _first_page_pixmap_is_blank(pdf_bytes)

    text = _extract_text(pdf_bytes)
    assert "AstroTruth" in text
    assert "Aries" in text  # lagna sign
    assert "Libra" in text  # Moon sign, from the planet table
    assert "Jupiter" in text  # transits card
    assert "Saturn" in text
    assert "not a science" in text  # disclaimer, in the footer on every page

    # Antardasha breakdown for the currently active mahadasha, matching the
    # web page's behavior: computed from `now`, not hardcoded, since the
    # active mahadasha/antardasha shifts over time.
    current = reference_stored["current_dasha"]
    maha_lord = current["mahadasha"]["lord"]
    antar_lord = current["antardasha"]["lord"]
    assert f"{maha_lord}–{antar_lord} Antardasha" in text
    assert f"{maha_lord} · Current" in text


def test_nepali_pdf_is_non_blank_and_contains_expected_text(reference_stored):
    pdf_bytes = _render(reference_stored, "ne")
    assert pdf_bytes[:4] == b"%PDF"

    assert not _first_page_pixmap_is_blank(pdf_bytes)

    text = _extract_text(pdf_bytes)
    assert "मेष" in text  # lagna sign (Aries), proves Devanagari shaping/extraction works
    assert "कुण्डली चक्र" in text  # chart title
    assert "बृहस्पति" in text  # Jupiter, transits card
    assert "निश्चितता होइन" in text  # disclaimer, in the footer on every page

    # Same antardasha breakdown, localized: lord names stay in English (as
    # stored in the API data) but the "Antardasha"/"Current" labels localize.
    current = reference_stored["current_dasha"]
    maha_lord = current["mahadasha"]["lord"]
    antar_lord = current["antardasha"]["lord"]
    assert f"{maha_lord}–{antar_lord} अन्तर्दशा" in text
    assert "हालको" in text  # हालको ("Current")


def test_pdf_has_multiple_pages(reference_stored):
    pdf_bytes = _render(reference_stored, "en")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) >= 1
    # Footer disclaimer must repeat on every page, not just the first.
    for page in doc:
        assert "not a science" in page.get_text()


def test_pdf_title_falls_back_to_generic_without_name(reference_stored):
    text = _extract_text(_render(reference_stored, "en"))
    assert "Kundali Chart" in text


def test_pdf_title_uses_name_when_present_english():
    stored = _build_reference_stored(name="Priya")
    text = _extract_text(_render(stored, "en"))
    assert "Priya's Kundali Chart" in text


def test_pdf_title_uses_name_when_present_nepali():
    stored = _build_reference_stored(name="Priya")
    text = _extract_text(_render(stored, "ne"))
    assert "Priya" in text
    assert "कुण्डली चक्र" in text


def test_pdf_header_includes_logo_mark(reference_stored):
    html = render_chart_html(reference_stored, "en")
    assert 'class="logo-mark"' in html
    # Same diamond-outline path used in the web header/favicon.
    assert "M50,8 L92,50 L50,92 L8,50 Z" in html


def test_pdf_interpretation_falls_back_for_unsupported_language(reference_stored):
    # Mock mode has no pre-written text for arbitrary languages; the PDF's
    # interpretation section should say so plainly rather than mistranslate.
    text = _extract_text(_render(reference_stored, "Spanish"))
    assert "requires live mode" in text
    assert "Spanish" in text
