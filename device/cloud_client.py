from datetime import datetime, timezone
from typing import Any, Dict

import requests

from config import settings
from sensors import SensorReading


class CloudClient:
    def __init__(self) -> None:
        self.base_url = settings.api_base_url.rstrip("/")

    def ingest(self, reading: SensorReading) -> Dict[str, Any]:
        payload = {
            "secret": settings.ingestion_secret,
            "device_id": settings.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indoor": {
                "temperature_c": reading.temperature_c,
                "humidity_pct": reading.humidity_pct,
                "tvoc_ppb": reading.tvoc_ppb,
                "eco2_ppm": reading.eco2_ppm,
            },
            "motion": {
                "detected": reading.motion_detected,
                "pir_sensor_id": reading.pir_sensor_id,
            },
            "meta": {
                "firmware_version": settings.firmware_version,
                "wifi_ssid": settings.wifi_ssid,
            },
        }
        response = requests.post(f"{self.base_url}/v1/ingest", json=payload, timeout=8)
        response.raise_for_status()
        return response.json()

    def latest_snapshot(self) -> Dict[str, Any]:
        response = requests.get(f"{self.base_url}/v1/device/{settings.device_id}/latest", timeout=8)
        response.raise_for_status()
        return response.json()

    def latest_weather(self, refresh: bool = False) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/v1/weather/current",
            params={"refresh": str(refresh).lower()},
            timeout=8,
        )
        response.raise_for_status()
        return response.json()
