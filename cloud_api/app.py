import json
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from bigquery_repo import BigQueryRepository
from config import settings
from models import (
    AlertState,
    DeviceAnswerRequest,
    IngestRequest,
    IngestResponse,
    PirStateRequest,
    QaRequest,
    QaResponse,
    SpeechToTextRequest,
    SpeechToTextResponse,
    TextToSpeechRequest,
    TextToSpeechResponse,
)
from voice_qa_service import VoiceQaService
from weather_client import fetch_current_weather, fetch_weather_forecast

app = FastAPI(title="Weather Ingestion API", version="0.1.0")

# Allow the Streamlit dashboard (and its embedded JS components) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory ephemeral state (cleared on restart — fine for demo)
# ---------------------------------------------------------------------------
_pir_states: Dict[str, Dict] = {}    # device_id -> {state, ts}
_device_answers: Dict[str, str] = {} # device_id -> answer text (consumed once)

_repo: Optional[BigQueryRepository] = None


def get_repo() -> BigQueryRepository:
    global _repo
    if _repo is None:
        _repo = BigQueryRepository()
    return _repo


@app.get("/")
def root() -> dict:
    return {"service": "weather-ingestion-api", "status": "alive"}


@app.get("/live")
def live() -> dict:
    """Liveness check. Avoid path `/healthz` on Cloud Run (can be intercepted at Google edge)."""
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


# Backwards compatibility for local docs; may not work on some Cloud Run public URLs.
@app.get("/health")
def health_alias() -> dict:
    return live()


@app.post("/v1/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest) -> IngestResponse:
    if not settings.ingestion_secret:
        raise HTTPException(status_code=500, detail="INGESTION_SHARED_SECRET is missing")
    if payload.secret != settings.ingestion_secret:
        raise HTTPException(status_code=401, detail="Invalid secret")

    repo = get_repo()
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
    repo = get_repo()
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
    repo = get_repo()
    try:
        if refresh:
            weather = fetch_current_weather()
            repo.insert_outdoor_weather(weather)
        return {"status": "success", "weather": repo.get_latest_outdoor()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/v1/weather/forecast")
def weather_forecast(days: int = 5) -> dict:
    try:
        forecast = fetch_weather_forecast(days=days)
        return {"status": "success", "forecast": forecast}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/v1/weather/greeting")
def weather_greeting(device_id: str = "core2-main", utc_hour: int | None = None) -> dict:
    """Return a spoken greeting for PIR-triggered announcements."""
    repo = get_repo()
    service = VoiceQaService(repo)
    try:
        text = service.generate_greeting(device_id=device_id, utc_hour=utc_hour)
        return {"status": "success", "text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/qa", response_model=QaResponse)
def qa(payload: QaRequest) -> QaResponse:
    repo = get_repo()
    service = VoiceQaService(repo)
    try:
        intent, answer = service.answer_question(device_id=payload.device_id, question=payload.question)
        return QaResponse(status="success", answer=answer, intent=intent)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/stt", response_model=SpeechToTextResponse)
def stt(payload: SpeechToTextRequest) -> SpeechToTextResponse:
    repo = get_repo()
    service = VoiceQaService(repo)
    try:
        provider, text = service.speech_to_text(
            audio_base64=payload.audio_base64,
            mime_type=payload.mime_type,
            language=payload.language,
        )
        return SpeechToTextResponse(status="success", text=text, provider=provider)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/tts", response_model=TextToSpeechResponse)
def tts(payload: TextToSpeechRequest) -> TextToSpeechResponse:
    repo = get_repo()
    service = VoiceQaService(repo)
    try:
        provider, audio_base64 = service.text_to_speech(
            text=payload.text,
            voice=payload.voice,
            audio_format=payload.audio_format,
            device=payload.device,
        )
        if provider == "none":
            return TextToSpeechResponse(status="success", provider=provider, text=payload.text)
        return TextToSpeechResponse(status="success", provider=provider, audio_base64=audio_base64)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# PIR coordination endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/pir/state")
def set_pir_state(payload: PirStateRequest) -> dict:
    """Core2 calls this when PIR sensor activates (state='on') or deactivates (state='off')."""
    _pir_states[payload.device_id] = {
        "state": payload.state,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    return {"status": "ok"}


@app.get("/v1/pir/state/{device_id}")
def get_pir_state(device_id: str) -> dict:
    """Dashboard polls this every second to know when to show the recording banner."""
    return _pir_states.get(device_id, {"state": "off", "ts": None})


@app.post("/v1/device/{device_id}/answer")
def push_device_answer(device_id: str, payload: DeviceAnswerRequest) -> dict:
    """Dashboard pushes the QA answer here so Core2 can display it."""
    _device_answers[device_id] = payload.answer
    return {"status": "ok"}


@app.get("/v1/device/{device_id}/answer")
def get_device_answer(device_id: str) -> dict:
    """Core2 polls this to retrieve and consume the queued answer (one-shot)."""
    answer = _device_answers.pop(device_id, None)
    return {"answer": answer}
