import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceSettings:
    device_id: str = os.getenv("DEVICE_ID", "core2-main")
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8080")
    ingestion_secret: str = os.getenv("INGESTION_SHARED_SECRET", "")
    wifi_ssid: str = os.getenv("WIFI_SSID", "iot-unil")
    wifi_password: str = os.getenv("WIFI_PASSWORD", "")
    firmware_version: str = os.getenv("FIRMWARE_VERSION", "0.1.0")
    sensor_interval_sec: int = int(os.getenv("SENSOR_INTERVAL_SEC", "30"))
    ingest_interval_sec: int = int(os.getenv("INGEST_INTERVAL_SEC", "60"))
    speech_cooldown_sec: int = int(os.getenv("SPEECH_COOLDOWN_SEC", "3600"))


settings = DeviceSettings()
