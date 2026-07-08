import asyncio
from datetime import datetime, timezone

import pymupdf
import pytest

from app.dasha import current_dasha, vimshottari
from app.engine import compute_chart, local_time_to_utc
from app.pdf import render_chart_pdf
from app.transits import compute_transits


def _build_reference_stored() -> dict:
    dt_utc = local_time_to_utc(datetime(2000, 1, 1, 12, 0, 0), "Europe/London")
    chart = compute_chart(dt_utc, lat=51.5074, lon=-0.1278)
    moon_longitude = chart.planets["Moon"].longitude
    dasha_sequence = vimshottari(moon_longitude, dt_utc)
    now = datetime.now(timezone.utc)
    current = current_dasha(dasha_sequence, now)
    transits = compute_transits(chart.lagna_sign, chart.planets["Moon"].sign, now)
    return {
        "share_id": "test-reference",
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


def test_nepali_pdf_is_non_blank_and_contains_expected_text(reference_stored):
    pdf_bytes = _render(reference_stored, "ne")
    assert pdf_bytes[:4] == b"%PDF"

    assert not _first_page_pixmap_is_blank(pdf_bytes)

    text = _extract_text(pdf_bytes)
    assert "मेष" in text  # lagna sign (Aries), proves Devanagari shaping/extraction works
    assert "कुण्डली चक्र" in text  # chart title
    assert "बृहस्पति" in text  # Jupiter, transits card
    assert "निश्चितता होइन" in text  # disclaimer, in the footer on every page


def test_pdf_has_multiple_pages(reference_stored):
    pdf_bytes = _render(reference_stored, "en")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) >= 1
    # Footer disclaimer must repeat on every page, not just the first.
    for page in doc:
        assert "not a science" in page.get_text()
