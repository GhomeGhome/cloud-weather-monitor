import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from bigquery_repo import BigQueryRepository
from config import settings
from models import AlertState, IngestRequest, IngestResponse
from weather_client import fetch_current_weather


app = FastAPI(title="Weather Ingestion API", version="0.1.0")
repo = BigQueryRepository()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest) -> IngestResponse:
    if not settings.ingestion_secret:
        raise HTTPException(status_code=500, detail="INGESTION_SHARED_SECRET is missing")
    if payload.secret != settings.ingestion_secret:
        raise HTTPException(status_code=401, detail="Invalid secret")

    try:
        alert_flags = repo.insert_indoor_reading(payload)
        if alert_flags["low_humidity"]:
            repo.insert_event(
                device_id=payload.device_id,
                event_type="ALERT_LOW_HUMIDITY",
                severity="warning",
                message="Indoor humidity dropped below 40%",
            )
        if alert_flags["poor_air_quality"]:
            repo.insert_event(
                device_id=payload.device_id,
                event_type="ALERT_POOR_AIR",
                severity="warning",
                message="Indoor air quality degraded (TVOC/eCO2 threshold exceeded)",
            )
        repo.upsert_latest_state(payload.device_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    message = None
    if alert_flags["low_humidity"] and alert_flags["poor_air_quality"]:
        message = "Low humidity and poor air quality detected."
    elif alert_flags["low_humidity"]:
        message = "Low humidity detected."
    elif alert_flags["poor_air_quality"]:
        message = "Poor air quality detected."

    return IngestResponse(
        status="success",
        device_id=payload.device_id,
        accepted_ts=payload.timestamp,
        alerts=AlertState(
            low_humidity=alert_flags["low_humidity"],
            poor_air_quality=alert_flags["poor_air_quality"],
            message=message,
        ),
    )


@app.get("/v1/device/{device_id}/latest")
def latest_device_state(device_id: str) -> dict:
    try:
        snapshot = repo.get_latest_snapshot(device_id)
        return {
            "device_id": device_id,
            "indoor": json.loads(snapshot["indoor"]),
            "outdoor": json.loads(snapshot["outdoor"]),
            "updated_at": snapshot["updated_at"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/v1/weather/current")
def current_weather(refresh: bool = False) -> dict:
    try:
        if refresh:
            weather = fetch_current_weather()
            repo.insert_outdoor_weather(weather)
        return {"status": "success", "weather": repo.get_latest_outdoor()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
