from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from config import settings


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


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


def fetch_weather_forecast(days: int = 5) -> Dict[str, Any]:
    if not settings.openweather_api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not configured")

    response = requests.get(
        OPENWEATHER_FORECAST_URL,
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
    rows: List[Dict[str, Any]] = payload.get("list", [])

    by_date: Dict[str, Dict[str, Any]] = {}
    ordered_dates: List[str] = []

    for row in rows:
        dt_txt = str(row.get("dt_txt", ""))
        if len(dt_txt) < 10:
            continue
        date_key = dt_txt[:10]

        if date_key not in by_date:
            by_date[date_key] = {
                "date": date_key,
                "temp_min_c": None,
                "temp_max_c": None,
                "weather_main": None,
                "weather_description": None,
                "weather_icon": None,
                "_best_hour_distance": 999,
            }
            ordered_dates.append(date_key)

        day = by_date[date_key]
        main = row.get("main", {}) if isinstance(row.get("main"), dict) else {}
        tmin = main.get("temp_min")
        tmax = main.get("temp_max")
        if tmin is not None:
            day["temp_min_c"] = tmin if day["temp_min_c"] is None else min(day["temp_min_c"], tmin)
        if tmax is not None:
            day["temp_max_c"] = tmax if day["temp_max_c"] is None else max(day["temp_max_c"], tmax)

        # Pick weather around midday first (closest to 12:00), fallback to first available.
        hour = 0
        try:
            hour = int(dt_txt[11:13])
        except Exception:
            hour = 0
        distance = abs(hour - 12)
        if distance < day["_best_hour_distance"]:
            weather0 = (row.get("weather") or [{}])[0]
            day["weather_main"] = weather0.get("main")
            day["weather_description"] = weather0.get("description")
            day["weather_icon"] = weather0.get("icon")
            day["_best_hour_distance"] = distance

    daily = []
    for d in ordered_dates[: max(1, int(days))]:
        item = by_date[d]
        daily.append(
            {
                "date": item["date"],
                "temp_min_c": item["temp_min_c"],
                "temp_max_c": item["temp_max_c"],
                "weather_main": item["weather_main"],
                "weather_description": item["weather_description"],
                "weather_icon": item["weather_icon"],
            }
        )

    return {
        "lat": settings.openweather_lat,
        "lon": settings.openweather_lon,
        "source": "openweathermap",
        "daily": daily,
    }
