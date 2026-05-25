from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class IndoorPayload(BaseModel):
    temperature_c: float = Field(..., ge=-40, le=85)
    humidity_pct: float = Field(..., ge=0, le=100)
    tvoc_ppb: Optional[int] = Field(default=None, ge=0)
    eco2_ppm: Optional[int] = Field(default=None, ge=0)


class MotionPayload(BaseModel):
    detected: bool = False
    pir_sensor_id: Optional[str] = None


class MetaPayload(BaseModel):
    firmware_version: Optional[str] = None
    wifi_ssid: Optional[str] = None


class IngestRequest(BaseModel):
    secret: str
    device_id: str
    timestamp: datetime
    indoor: IndoorPayload
    motion: MotionPayload = MotionPayload()
    meta: MetaPayload = MetaPayload()


class AlertState(BaseModel):
    low_humidity: bool = False
    poor_air_quality: bool = False
    message: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    device_id: str
    accepted_ts: datetime
    alerts: AlertState


class LatestSnapshot(BaseModel):
    indoor: dict
    outdoor: dict
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SpeechToTextRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64-encoded audio bytes")
    mime_type: str = Field(default="audio/wav")
    language: str = Field(default="en")


class SpeechToTextResponse(BaseModel):
    status: str
    text: str
    provider: str


class QaRequest(BaseModel):
    device_id: str
    question: str


class QaResponse(BaseModel):
    status: str
    answer: str
    intent: str


class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = Field(default="alloy")
    audio_format: str = Field(default="mp3")
    device: bool = Field(default=False, description="If True, return 8 kHz raw PCM for Core2 speaker.playRaw()")


class TextToSpeechResponse(BaseModel):
    status: str
    provider: str
    audio_base64: Optional[str] = None
    text: Optional[str] = None


class PirStateRequest(BaseModel):
    device_id: str
    state: str  # "on" or "off"


class DeviceAnswerRequest(BaseModel):
    answer: str
