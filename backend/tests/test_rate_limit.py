import pytest
from fastapi.testclient import TestClient

from app import interpret, storage
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "charts.db")


@pytest.fixture(autouse=True)
def no_artificial_stream_delay(monkeypatch):
    # The mock interpreter sleeps briefly between words to simulate a real
    # stream; that's irrelevant to rate-limit enforcement and would make a
    # 10+ request test needlessly slow, so skip it here.
    monkeypatch.setattr(interpret.time, "sleep", lambda seconds: None)


@pytest.fixture
def share_id():
    response = client.post(
        "/api/chart",
        json={"calendar": "AD", "date": "2000-01-01", "time": "12:00", "city_id": "united-kingdom-london"},
    )
    assert response.status_code == 200
    return response.json()["share_id"]


def test_interpret_rate_limit_returns_429_after_limit_exceeded(share_id):
    statuses = [
        client.post("/api/interpret", json={"share_id": share_id, "language": "en"}).status_code
        for _ in range(13)
    ]

    assert statuses.count(200) <= 10
    assert 429 in statuses
    # Once the limit trips it should keep rejecting, not flap back to 200.
    assert statuses[-1] == 429


def test_pdf_rate_limit_returns_429_after_limit_exceeded(share_id):
    statuses = [client.get(f"/api/chart/{share_id}/pdf").status_code for _ in range(12)]

    assert statuses.count(200) <= 10
    assert 429 in statuses


def test_chart_creation_rate_limit_returns_429_after_limit_exceeded():
    payload = {"calendar": "AD", "date": "2000-01-01", "time": "12:00", "city_id": "united-kingdom-london"}
    statuses = [client.post("/api/chart", json=payload).status_code for _ in range(13)]

    assert statuses.count(200) <= 10
    assert 429 in statuses
    assert statuses[-1] == 429
