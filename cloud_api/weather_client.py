from datetime import datetime, timezone
from typing import Any, Dict

import requests

from config import settings


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_current_weather() -> Dict[str, Any]:
    if not settings.openweather_api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not configured")

    response = requests.get(
        OPENWEATHER_URL,
        params={
            "lat": settings.openweather_lat,
            "lon": settings.openweather_lon,
            "appid": settings.openweather_api_key,
            "units": settings.openweather_units,
            "lang": settings.openweather_lang,
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    weather0 = payload.get("weather", [{}])[0]
    main = payload.get("main", {})
    wind = payload.get("wind", {})
    return {
        "weather_ts": datetime.now(timezone.utc).isoformat(),
        "source": "openweathermap",
        "lat": settings.openweather_lat,
        "lon": settings.openweather_lon,
        "temperature_c": main.get("temp"),
        "humidity_pct": main.get("humidity"),
        "pressure_hpa": main.get("pressure"),
        "wind_speed_ms": wind.get("speed"),
        "weather_main": weather0.get("main"),
        "weather_description": weather0.get("description"),
        "weather_icon": weather0.get("icon"),
        "forecast_json": None,
    }
