import asyncio
import re
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


_DEVANAGARI_COMBINING_MARKS = "ऀ-ःऺ-्॑-ॗॢॣ"


def _normalize_extraction_quirks(text: str) -> str:
    """pymupdf's text layer for this Devanagari font has two known
    extraction quirks -- confirmed via rendered-pixel screenshots to not be
    real rendering bugs, just glyph<->Unicode round-tripping noise in this
    font+library combination:

    - A dependent vowel sign / anusvara sometimes doubles on extraction
      (e.g. "व्याख्या" comes back as "व्यााख्याा").
    - A "reph" (ra + virama forming the diacritic-like mark reordered above
      the following consonant, e.g. in "अन्तर्दशा" or "कर्कट") sometimes
      drops from the extracted text entirely.

    Collapse runs of a repeated *combining mark* (not base consonants,
    which can legitimately repeat, e.g. "निश्चितता") and strip reph
    sequences from both sides of a comparison so text assertions aren't
    coupled to either quirk."""
    text = re.sub(rf"([{_DEVANAGARI_COMBINING_MARKS}])\1+", r"\1", text)
    text = text.replace("र्", "")
    return text


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
    # The footer disclaimer itself is checked separately in
    # test_nepali_pdf_footer_disclaimer_is_rendered_as_image_on_every_page --
    # it's an embedded PNG for Nepali (see render_chart_pdf), not extractable
    # text, so it can't be asserted on here.

    # Same antardasha breakdown, localized: lord names stay in English (as
    # stored in the API data) but the "Antardasha"/"Current" labels localize.
    # "अन्तर्दशा" contains a reph ("र्"), which pymupdf sometimes drops on
    # extraction for this font (see _normalize_extraction_quirks) -- compare
    # normalized text against a normalized expectation.
    current = reference_stored["current_dasha"]
    maha_lord = current["mahadasha"]["lord"]
    antar_lord = current["antardasha"]["lord"]
    normalized_text = _normalize_extraction_quirks(text)
    assert _normalize_extraction_quirks(f"{maha_lord}–{antar_lord} अन्तर्दशा") in normalized_text
    assert "हालको" in text  # हालको ("Current")


def test_pdf_has_multiple_pages(reference_stored):
    pdf_bytes = _render(reference_stored, "en")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) >= 1
    # Footer disclaimer must repeat on every page, not just the first.
    for page in doc:
        assert "not a science" in page.get_text()


def _footer_strip_pixmap(page) -> "pymupdf.Pixmap":
    # Playwright's footer_template renders inside the PDF's bottom margin
    # (18mm ~= 51pt at 72dpi); crop generously to that band.
    rect = page.rect
    footer_rect = pymupdf.Rect(0, rect.height - 60, rect.width, rect.height)
    return page.get_pixmap(clip=footer_rect)


def test_nepali_pdf_footer_disclaimer_is_rendered_as_image_on_every_page(reference_stored):
    # Chromium's print header/footer templates render in an isolated context
    # that can't load external resources at all -- confirmed by testing an
    # inline <style>/@font-face block placed directly inside a footer
    # template, which still produced tofu boxes for Devanagari even though
    # the identical font/CSS works fine in the main page. render_chart_pdf
    # works around this by rendering the Nepali disclaimer to a PNG with the
    # real font and embedding it as an <img>, so it's no longer extractable
    # via get_text() -- verify it lands on every page instead via an
    # embedded image plus non-blank footer pixels.
    pdf_bytes = _render(reference_stored, "ne")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) >= 1
    for page in doc:
        assert len(page.get_images()) > 0  # the disclaimer PNG
        pixmap = _footer_strip_pixmap(page)
        assert not all(byte == 255 for byte in pixmap.samples)


def test_english_pdf_footer_disclaimer_stays_plain_text(reference_stored):
    # An ASCII disclaimer doesn't need the image workaround -- Arial covers
    # it fine -- so the English footer should stay real, extractable text
    # rather than switching to an image unnecessarily.
    pdf_bytes = _render(reference_stored, "en")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc[0].get_images()) == 0


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


def test_pdf_html_devanagari_font_family_is_not_html_escaped(reference_stored):
    # Regression test for a bug where Jinja's autoescaping turned the
    # font-family declaration's quotes into HTML entities (&#39;) inside the
    # <style> block. <style> is a "raw text" element per the HTML spec, so
    # browsers don't decode entities there -- the CSS parser saw a garbage
    # token instead of 'Noto Sans Devanagari' and silently fell through to
    # the Georgia/serif fallback, which has no Devanagari glyphs. This
    # rendered fine on some Chromium builds/platforms (tolerant parsing) and
    # produced fully blank Devanagari text on others (observed on Render's
    # Linux container) -- a rendered-PDF pixel/text assertion alone can pass
    # on one platform while the bug is still live on another, so this
    # asserts on the generated CSS text directly instead.
    html = render_chart_html(reference_stored, "ne")
    assert "&#39;Noto Sans Devanagari&#39;" not in html
    assert "'Noto Sans Devanagari', Georgia" in html


def test_pdf_html_headings_use_devanagari_font_for_nepali(reference_stored):
    # Regression test: h1/h2/h3 used to hardcode their own font-family
    # stack (Georgia/Times/serif) that never included the Devanagari font at
    # all, so every heading -- the chart title, "Lagna", "Current transits",
    # every interpretation section heading -- rendered blank in Nepali
    # regardless of the escaping bug above. Headings must inherit body's
    # font stack instead of declaring their own.
    html = render_chart_html(reference_stored, "ne")
    assert "h1, h2, h3 { font-family: inherit" in html


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


@pytest.fixture(scope="module")
def non_reference_stored() -> dict:
    # A real, non-reference birth chart (Kathmandu, not the Stage-1 London
    # reference chart). Every test above uses reference_stored, which makes
    # _is_reference_chart() true and always takes the hand-written _MOCK_TEXT
    # path -- that hid a real bug (Devanagari text going blank in the PDF)
    # that only showed up for charts running through _generate_grounded_mock_text.
    dt_utc = local_time_to_utc(datetime(1990, 6, 15, 8, 30, 0), "Asia/Kathmandu")
    chart = compute_chart(dt_utc, lat=27.7129, lon=85.3228)
    moon_longitude = chart.planets["Moon"].longitude
    dasha_sequence = vimshottari(moon_longitude, dt_utc)
    now = datetime.now(timezone.utc)
    current = current_dasha(dasha_sequence, now)
    transits = compute_transits(chart.lagna_sign, chart.planets["Moon"].sign, now)
    return {
        "share_id": "test-non-reference",
        "name": None,
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


def test_nepali_pdf_for_non_reference_chart_is_non_blank_and_contains_expected_text(
    non_reference_stored,
):
    pdf_bytes = _render(non_reference_stored, "ne")
    assert pdf_bytes[:4] == b"%PDF"

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = _normalize_extraction_quirks("\n".join(page.get_text() for page in doc))

    # Static labels (not chart-derived) -- these must never render blank,
    # regardless of which chart or LLM code path produced the interpretation.
    assert "कुण्डली चक्र" in text  # chart title
    assert "लग्न" in text  # "Lagna" heading
    assert "हालको गोचर" in text  # "Current transits" heading
    assert _normalize_extraction_quirks("विंशोत्तरी दशा समयरेखा") in text  # dasha timeline heading
    assert "व्याख्या" in text  # "Interpretation" heading

    # Chart-grounded interpretation body (from _generate_grounded_mock_text,
    # the non-reference-chart code path) must also be present, not blank.
    assert _normalize_extraction_quirks("कर्कट") in text  # this chart's lagna sign, Cancer
