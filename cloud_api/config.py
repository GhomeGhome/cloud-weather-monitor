import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project_id: str = os.getenv("PROJECT_ID", "")
    region: str = os.getenv("REGION", "europe-west6")
    dataset_id: str = os.getenv("DATASET_ID", "weather_analytics")
    indoor_table: str = os.getenv("INDOOR_TABLE", "indoor_metrics")
    outdoor_table: str = os.getenv("OUTDOOR_TABLE", "outdoor_weather")
    events_table: str = os.getenv("EVENTS_TABLE", "device_events")
    latest_table: str = os.getenv("LATEST_TABLE", "latest_state")
    ingestion_secret: str = os.getenv("INGESTION_SHARED_SECRET", "")
    openweather_api_key: str = os.getenv("OPENWEATHER_API_KEY", "")
    openweather_lat: float = float(os.getenv("OPENWEATHER_LAT", "46.5197"))
    openweather_lon: float = float(os.getenv("OPENWEATHER_LON", "6.6323"))
    openweather_units: str = os.getenv("OPENWEATHER_UNITS", "metric")
    openweather_lang: str = os.getenv("OPENWEATHER_LANG", "en")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_stt_model: str = os.getenv("OPENAI_STT_MODEL", "whisper-1")
    openai_tts_model: str = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


settings = Settings()
