import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app

client = TestClient(app)


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
