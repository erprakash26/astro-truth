from datetime import date as date_cls
from datetime import datetime, timezone
from datetime import time as time_cls
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.calendar import CalendarError, bs_to_ad
from app.dasha import current_dasha, vimshottari
from app.engine import compute_chart, local_time_to_utc
from app.geocode import City, get_city, search_cities
from app.storage import load_chart, new_share_id, save_chart

app = FastAPI(title="AstroTruth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChartRequest(BaseModel):
    calendar: Literal["AD", "BS"]
    date: str
    time: str
    city_id: str


@app.get("/api/cities")
def list_cities(q: str = "") -> list[City]:
    return search_cities(q)


@app.post("/api/chart")
def create_chart(payload: ChartRequest) -> dict:
    city = get_city(payload.city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"Unknown city_id: {payload.city_id}")

    try:
        if payload.calendar == "BS":
            year, month, day = (int(part) for part in payload.date.split("-"))
            ad_date = bs_to_ad(year, month, day)
        else:
            ad_date = date_cls.fromisoformat(payload.date)
    except CalendarError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {payload.date}") from exc

    try:
        parsed_time = time_cls.fromisoformat(payload.time)
        local_dt = datetime.combine(ad_date, parsed_time)
        dt_utc = local_time_to_utc(local_dt, city.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chart = compute_chart(dt_utc, city.lat, city.lon)
    moon_longitude = chart.planets["Moon"].longitude
    dasha_sequence = vimshottari(moon_longitude, dt_utc)
    current = current_dasha(dasha_sequence, datetime.now(timezone.utc))

    share_id = new_share_id()
    response = {
        "share_id": share_id,
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
    }

    save_chart(share_id, response)
    return response


@app.get("/api/chart/{share_id}")
def get_chart(share_id: str) -> dict:
    chart = load_chart(share_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return chart
