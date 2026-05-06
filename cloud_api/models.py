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
