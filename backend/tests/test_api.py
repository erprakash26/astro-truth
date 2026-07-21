import json

import pytest
from fastapi.testclient import TestClient

from app import interpret, storage
from app.main import app

client = TestClient(app)


def _sse_text(body: str) -> str:
    """Concatenate the "text" field of every `data:` event in an SSE body,
    mirroring what the frontend's EventSource-style reader reconstructs."""
    text = ""
    for block in body.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                payload = json.loads(line[len("data: ") :])
                text += payload.get("text", "")
    return text


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "charts.db")


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_cities_search():
    response = client.get("/api/cities", params={"q": "kathmandu"})
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Kathmandu" in names


def test_list_cities_no_query_returns_results():
    response = client.get("/api/cities")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_list_languages_search():
    response = client.get("/api/languages", params={"q": "span"})
    assert response.status_code == 200
    names = [entry["name"] for entry in response.json()]
    assert "Spanish" in names


def test_list_languages_no_query_returns_results():
    response = client.get("/api/languages")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_translate_ui_mock_mode_returns_unavailable():
    response = client.post("/api/translate-ui", json={"language": "Spanish"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["translations"] is None
    assert "requires live mode" in body["note"]


def test_create_chart_unknown_city_returns_404():
    response = client.post(
        "/api/chart",
        json={"calendar": "AD", "date": "2000-01-01", "time": "12:00", "city_id": "nope"},
    )
    assert response.status_code == 404


def test_create_chart_invalid_date_returns_400():
    response = client.post(
        "/api/chart",
        json={
            "calendar": "AD",
            "date": "not-a-date",
            "time": "12:00",
            "city_id": "united-kingdom-london",
        },
    )
    assert response.status_code == 400


def test_create_chart_invalid_bs_date_returns_400():
    response = client.post(
        "/api/chart",
        json={
            "calendar": "BS",
            "date": "2056-13-01",
            "time": "12:00",
            "city_id": "united-kingdom-london",
        },
    )
    assert response.status_code == 400


@pytest.fixture
def reference_chart_response():
    response = client.post(
        "/api/chart",
        json={
            "calendar": "AD",
            "date": "2000-01-01",
            "time": "12:00",
            "city_id": "united-kingdom-london",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_reference_chart_lagna_and_moon(reference_chart_response):
    chart = reference_chart_response["chart"]
    assert chart["lagna_sign_name"] == "Aries"
    moon = chart["planets"]["Moon"]
    assert moon["sign_name"] == "Libra"
    assert moon["nakshatra"] == "Swati"


def test_reference_chart_has_dasha_timeline(reference_chart_response):
    timeline = reference_chart_response["dasha_timeline"]
    assert len(timeline) == 9
    assert timeline[0]["lord"] == "Rahu"
    assert timeline[1]["lord"] == "Jupiter"
    assert len(timeline[1]["antardashas"]) == 9


def test_reference_chart_share_and_retrieve(reference_chart_response):
    share_id = reference_chart_response["share_id"]
    assert share_id

    response = client.get(f"/api/chart/{share_id}")
    assert response.status_code == 200
    fetched = response.json()
    assert fetched["chart"]["lagna_sign_name"] == "Aries"
    assert fetched["share_id"] == share_id


def test_get_chart_unknown_share_id_returns_404():
    response = client.get("/api/chart/does-not-exist")
    assert response.status_code == 404


def test_create_chart_without_name_defaults_to_none(reference_chart_response):
    assert reference_chart_response["name"] is None


def test_create_chart_with_name_round_trips():
    response = client.post(
        "/api/chart",
        json={
            "calendar": "AD",
            "date": "2000-01-01",
            "time": "12:00",
            "city_id": "united-kingdom-london",
            "name": "Priya",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Priya"

    fetched = client.get(f"/api/chart/{body['share_id']}").json()
    assert fetched["name"] == "Priya"


def test_interpret_custom_language_falls_back_with_note(reference_chart_response, monkeypatch):
    # Regression test for a bug where a valid custom language (e.g. the
    # frontend's "Other" mode with "spanish" typed in) silently produced
    # English mock text with no indication the request wasn't honored.
    # Exercises the real /api/interpret SSE endpoint end-to-end, not just
    # interpret_chart_text() directly, so it also catches a regression in
    # request parsing or SSE encoding that a unit test on interpret.py alone
    # would miss.
    monkeypatch.setattr(interpret.time, "sleep", lambda seconds: None)
    share_id = reference_chart_response["share_id"]

    response = client.post("/api/interpret", json={"share_id": share_id, "language": "spanish"})

    assert response.status_code == 200
    text = _sse_text(response.text)
    assert "requires live mode" in text
    assert "spanish" in text
    assert interpret.DISCLAIMER in text
    assert "## Lagna" not in text  # not the default English interpretation


def test_create_chart_via_bs_calendar_matches_ad_equivalent(reference_chart_response):
    # BS 2056-09-17 == AD 2000-01-01 (see test_calendar.py)
    response = client.post(
        "/api/chart",
        json={
            "calendar": "BS",
            "date": "2056-09-17",
            "time": "12:00",
            "city_id": "united-kingdom-london",
        },
    )
    assert response.status_code == 200
    bs_chart = response.json()["chart"]
    ad_chart = reference_chart_response["chart"]
    assert bs_chart["lagna_sign_name"] == ad_chart["lagna_sign_name"]
    assert bs_chart["planets"]["Moon"]["nakshatra"] == ad_chart["planets"]["Moon"]["nakshatra"]
