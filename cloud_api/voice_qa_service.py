import base64
import io
import json
import re
import struct
from typing import Dict, Any, Tuple

import requests

from bigquery_repo import BigQueryRepository
from config import settings


# ---------------------------------------------------------------------------
# Keyword sets for flexible intent detection
# ---------------------------------------------------------------------------
_TEMP_WORDS = {
    "temperature", "temp", "degrees", "degree", "celsius", "hot", "cold",
    "warm", "cool", "heat", "heated", "cooler", "warmer",
}
_HUMIDITY_WORDS = {
    "humidity", "humid", "dry", "wet", "moisture", "moist", "damp",
    "dryness", "wetness",
}
_AIR_WORDS = {
    "air", "tvoc", "voc", "co2", "eco2", "carbon", "pollution", "polluted",
    "pollutant", "breathe", "stuffy", "stuffy", "quality", "dioxide",
    "volatile", "organic",
}
_OUTDOOR_WORDS = {
    "outside", "outdoor", "outdoors", "weather", "exterior", "external",
    "rain", "raining", "sunny", "cloudy", "clouds", "wind", "windy",
    "umbrella", "outside",
}
_FORECAST_WORDS = {
    "forecast", "tomorrow", "upcoming", "next", "week", "days",
    "prediction", "expect", "expecting",
}
_EXCEED_WORDS = {
    "exceed", "exceeded", "exceeding", "above", "over", "more",
    "higher", "surpass", "surpassed", "reach", "reached", "past",
    "beyond", "greater",
}


def _words(text: str) -> set:
    """Return lowercased word set from text."""
    return set(re.findall(r"\w+", text.lower()))


def _parse_days_ago(ql: str) -> int:
    """Return how many days ago the question refers to (0 = today/now)."""
    if re.search(r"\b(yesterday|1\s+day\s+ago|last\s+day)\b", ql):
        return 1
    if re.search(r"\b(2\s+days?\s+ago|two\s+days?\s+ago|day\s+before\s+yesterday)\b", ql):
        return 2
    if re.search(r"\b(3\s+days?\s+ago|three\s+days?\s+ago)\b", ql):
        return 3
    m = re.search(r"\b(\d+)\s+days?\s+ago\b", ql)
    if m:
        return int(m.group(1))
    return 0  # today / now / current


def _parse_days_ahead(ql: str) -> int:
    """Return how many days into the future the question refers to (0 = today)."""
    if re.search(r"\bday\s+after\s+tomorrow\b", ql):
        return 2
    if re.search(r"\btomorrow\b", ql):
        return 1
    m = re.search(r"\bin\s+(\d+)\s+days?\b", ql)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d+)\s+days?\s+from\s+now\b", ql)
    if m:
        return int(m.group(1))
    if re.search(r"\bnext\s+week\b", ql):
        return 7
    return 0  # today / now


def _time_label(days_ago: int) -> str:
    if days_ago == 0:
        return "today"
    if days_ago == 1:
        return "yesterday"
    return f"{days_ago} days ago"


def _air_quality_label(tvoc: float | None, eco2: float | None) -> str:
    """Human-readable air quality assessment."""
    if tvoc is None and eco2 is None:
        return "unknown"
    issues = []
    if tvoc is not None:
        if tvoc < 220:
            issues.append("TVOC is good")
        elif tvoc < 660:
            issues.append(f"TVOC is moderate at {tvoc:.0f} ppb")
        else:
            issues.append(f"TVOC is high at {tvoc:.0f} ppb — consider ventilating")
    if eco2 is not None:
        if eco2 < 800:
            issues.append("CO2 is excellent")
        elif eco2 < 1000:
            issues.append(f"CO2 is acceptable at {eco2:.0f} ppm")
        elif eco2 < 2000:
            issues.append(f"CO2 is elevated at {eco2:.0f} ppm — open a window")
        else:
            issues.append(f"CO2 is very high at {eco2:.0f} ppm — ventilate immediately")
    return "; ".join(issues)


class VoiceQaService:
    def __init__(self, repo: BigQueryRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def answer_question(self, device_id: str, question: str) -> Tuple[str, str]:
        q = (question or "").strip()
        if not q:
            return "empty", "I didn't receive a question. Please try again."

        ql = q.lower()
        w = _words(ql)
        days_ago = _parse_days_ago(ql)
        label = _time_label(days_ago)

        # ---- Humidity exceed check ----------------------------------------
        if (w & _EXCEED_WORDS) and (w & _HUMIDITY_WORDS or "humidity" in ql or "%" in ql):
            threshold_m = re.search(r"(\d+(?:\.\d+)?)\s*%", ql)
            threshold = float(threshold_m.group(1)) if threshold_m else 50.0
            exceeded = self.repo.did_humidity_exceed(device_id, threshold, days_ago)
            if exceeded:
                return (
                    "humidity_exceed",
                    f"Yes, the indoor humidity did exceed {threshold:.0f} percent {label}.",
                )
            return (
                "humidity_exceed",
                f"No, the indoor humidity did not exceed {threshold:.0f} percent {label}.",
            )

        # ---- Outdoor / weather -------------------------------------------
        if (w & _OUTDOOR_WORDS) and not (w & _FORECAST_WORDS):
            return self._answer_outdoor()

        # ---- Forecast -------------------------------------------------------
        if w & _FORECAST_WORDS:
            days_ahead = _parse_days_ahead(ql)
            return self._answer_forecast(days_ahead)

        # ---- Air quality ----------------------------------------------------
        if w & _AIR_WORDS:
            return self._answer_air(device_id, days_ago, label)

        # ---- Temperature only -----------------------------------------------
        if (w & _TEMP_WORDS) and not (w & _HUMIDITY_WORDS):
            return self._answer_temperature(device_id, days_ago, label)

        # ---- Humidity only --------------------------------------------------
        if (w & _HUMIDITY_WORDS) and not (w & _TEMP_WORDS):
            return self._answer_humidity(device_id, days_ago, label)

        # ---- Off-topic detection (no relevant keywords found) ---------------
        all_topic_words = (
            _TEMP_WORDS | _HUMIDITY_WORDS | _AIR_WORDS
            | _OUTDOOR_WORDS | _FORECAST_WORDS | _EXCEED_WORDS
        )
        if not (w & all_topic_words):
            return (
                "off_topic",
                "I am here to tell you about your indoor environment and outdoor weather. "
                "You can ask me about temperature, humidity, air quality, or the weather forecast!",
            )

        # ---- Full summary (temperature + humidity + air) --------------------
        return self._answer_summary(device_id, days_ago, label)

    # ------------------------------------------------------------------
    # Topic handlers
    # ------------------------------------------------------------------
    def _answer_temperature(self, device_id: str, days_ago: int, label: str) -> Tuple[str, str]:
        summary = self.repo.get_day_summary(device_id=device_id, days_ago=days_ago)
        if not summary or summary.get("avg_temp_c") is None:
            # Fallback to latest snapshot for "today"
            if days_ago == 0:
                snap = self._latest_indoor(device_id)
                t = snap.get("temperature_c")
                if t is not None:
                    return "temperature", f"The current indoor temperature is {t:.1f} degrees."
            return "temperature", f"I don't have temperature data for {label}."

        avg = summary["avg_temp_c"]
        lo  = summary.get("min_temp_c")
        hi  = summary.get("max_temp_c")
        resp = f"{label.capitalize()}, the indoor temperature averaged {avg:.1f} degrees"
        if lo is not None and hi is not None and lo != hi:
            resp += f", ranging from a low of {lo:.1f} to a high of {hi:.1f} degrees"
        resp += "."
        return "temperature", resp

    def _answer_humidity(self, device_id: str, days_ago: int, label: str) -> Tuple[str, str]:
        summary = self.repo.get_day_summary(device_id=device_id, days_ago=days_ago)
        if not summary or summary.get("avg_humidity_pct") is None:
            if days_ago == 0:
                snap = self._latest_indoor(device_id)
                h = snap.get("humidity_pct")
                if h is not None:
                    note = " That's quite dry — consider a humidifier." if h < 40 else ""
                    return "humidity", f"The current indoor humidity is {h:.0f} percent.{note}"
            return "humidity", f"I don't have humidity data for {label}."

        avg = summary["avg_humidity_pct"]
        hi  = summary.get("max_humidity_pct")
        resp = f"{label.capitalize()}, indoor humidity averaged {avg:.0f} percent"
        if hi is not None and hi > avg + 5:
            resp += f", peaking at {hi:.0f} percent"
        resp += "."
        if avg < 40:
            resp += " Humidity was low — you might want to use a humidifier."
        elif avg > 70:
            resp += " Humidity was high — good ventilation is recommended."
        return "humidity", resp

    def _answer_air(self, device_id: str, days_ago: int, label: str) -> Tuple[str, str]:
        aq = self.repo.get_day_air_quality(device_id=device_id, days_ago=days_ago)
        if not aq:
            if days_ago == 0:
                snap = self._latest_indoor(device_id)
                tvoc = snap.get("tvoc_ppb")
                eco2 = snap.get("eco2_ppm")
                if tvoc is not None or eco2 is not None:
                    quality = _air_quality_label(tvoc, eco2)
                    return "air_quality", f"Current indoor air quality: {quality}."
            return "air_quality", f"I don't have air quality data for {label}."

        avg_tvoc = aq.get("avg_tvoc_ppb")
        avg_eco2 = aq.get("avg_eco2_ppm")
        quality = _air_quality_label(avg_tvoc, avg_eco2)
        return "air_quality", f"Air quality {label}: {quality}."

    def _answer_outdoor(self) -> Tuple[str, str]:
        outdoor = self.repo.get_latest_outdoor()
        if not outdoor:
            return "outdoor", "I don't have current outdoor weather data available."
        temp = outdoor.get("temperature_c")
        hum  = outdoor.get("humidity_pct")
        desc = outdoor.get("weather_description") or outdoor.get("weather_main") or ""
        parts = []
        if temp is not None:
            parts.append(f"the temperature is {temp:.1f} degrees")
        if hum is not None:
            parts.append(f"humidity is {hum:.0f} percent")
        body = ", ".join(parts)
        suffix = f" {desc.capitalize()}." if desc else "."
        return "outdoor", f"Outside right now, {body}{suffix}" if body else f"Outdoor conditions: {desc}."

    def _answer_forecast(self, days_ahead: int = 0) -> Tuple[str, str]:
        # Fetch real multi-day forecast from OpenWeatherMap
        try:
            from weather_client import fetch_weather_forecast
            data = fetch_weather_forecast(days=max(days_ahead + 1, 5))
            daily = data.get("daily", [])
        except Exception:
            daily = []

        # Fallback to latest stored outdoor reading if forecast unavailable
        if not daily:
            outdoor = self.repo.get_latest_outdoor()
            if not outdoor:
                return "forecast", "I don't have forecast data available right now."
            desc = outdoor.get("weather_description") or outdoor.get("weather_main") or "unknown"
            temp = outdoor.get("temperature_c")
            resp = f"Based on the latest data, it is {temp:.1f} degrees and {desc}." if temp else f"Current conditions: {desc}."
            return "forecast", resp

        # Pick the requested day (clamp to available range)
        idx = min(days_ahead, len(daily) - 1)
        day = daily[idx]

        tmin = day.get("temp_min_c")
        tmax = day.get("temp_max_c")
        desc = day.get("weather_description") or day.get("weather_main") or "conditions unknown"

        # Natural time label
        if days_ahead == 0:
            when = "Today"
        elif days_ahead == 1:
            when = "Tomorrow"
        else:
            when = f"In {days_ahead} days"

        # Build sentence
        if tmin is not None and tmax is not None:
            resp = (
                f"{when}, expect {desc} with temperatures between "
                f"{tmin:.0f} and {tmax:.0f} degrees."
            )
        else:
            resp = f"{when}, the forecast is {desc}."

        # Contextual advice
        desc_l = desc.lower()
        if any(w in desc_l for w in ["rain", "drizzle", "shower", "storm", "thunder"]):
            resp += " Don't forget your umbrella!"
        elif any(w in desc_l for w in ["snow", "sleet", "blizzard", "freezing"]):
            resp += " Dress warmly and watch for icy conditions!"
        elif any(w in desc_l for w in ["clear", "sunny"]):
            resp += " Looks like a great day to be outside!"

        return "forecast", resp

    def _answer_summary(self, device_id: str, days_ago: int, label: str) -> Tuple[str, str]:
        summary = self.repo.get_day_summary(device_id=device_id, days_ago=days_ago)
        aq = self.repo.get_day_air_quality(device_id=device_id, days_ago=days_ago)

        parts = []
        alerts = []

        if summary:
            avg_t = summary.get("avg_temp_c")
            lo_t  = summary.get("min_temp_c")
            hi_t  = summary.get("max_temp_c")
            avg_h = summary.get("avg_humidity_pct")

            if avg_t is not None:
                t_str = f"temperature averaged {avg_t:.1f} degrees"
                if lo_t and hi_t and lo_t != hi_t:
                    t_str += f" (low {lo_t:.1f}, high {hi_t:.1f})"
                parts.append(t_str)
            if avg_h is not None:
                parts.append(f"humidity was {avg_h:.0f} percent")
                if avg_h < 40:
                    alerts.append("humidity was low — consider a humidifier")
                elif avg_h > 70:
                    alerts.append("humidity was high — ventilate the room")

        if aq:
            avg_tvoc = aq.get("avg_tvoc_ppb")
            avg_eco2 = aq.get("avg_eco2_ppm")
            if avg_tvoc is not None and avg_tvoc > 220:
                alerts.append(f"TVOC was elevated at {avg_tvoc:.0f} ppb")
            if avg_eco2 is not None and avg_eco2 > 1000:
                alerts.append(f"CO2 was high at {avg_eco2:.0f} ppm")

        if not parts:
            return "no_data", f"I don't have enough data for {label} yet."

        resp = f"Here is a summary for {label}: " + ", ".join(parts) + "."
        if alerts:
            resp += " Note: " + "; ".join(alerts) + "."
        return "summary", resp

    # ------------------------------------------------------------------
    # Helper: latest indoor reading from snapshot
    # ------------------------------------------------------------------
    def _latest_indoor(self, device_id: str) -> Dict[str, Any]:
        try:
            snap = self.repo.get_latest_snapshot(device_id)
            indoor = snap.get("indoor", {})
            if isinstance(indoor, str):
                indoor = json.loads(indoor)
            return indoor or {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Speech-to-text (OpenAI Whisper)
    # ------------------------------------------------------------------
    def speech_to_text(self, audio_base64: str, mime_type: str, language: str) -> Tuple[str, str]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")

        audio_bytes = base64.b64decode(audio_base64)

        # Derive file extension from mime_type for OpenAI filename hint
        mime = (mime_type or "").lower()
        if "mp3" in mime:
            ext = ".mp3"
        elif "webm" in mime:
            ext = ".webm"
        elif "ogg" in mime:
            ext = ".ogg"
        elif "mp4" in mime or "m4a" in mime:
            ext = ".m4a"
        else:
            ext = ".wav"

        # Pass raw bytes directly — io.BytesIO.name is not settable in Python 3.11
        filename = f"audio{ext}"
        url = f"{settings.openai_base_url.rstrip('/')}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        files = {"file": (filename, audio_bytes, mime_type or "audio/wav")}
        data = {"model": settings.openai_stt_model, "language": language or "en"}

        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        response.raise_for_status()
        return "openai", response.json().get("text", "")

    # ------------------------------------------------------------------
    # Text-to-speech (OpenAI TTS)
    # ------------------------------------------------------------------
    def text_to_speech(self, text: str, voice: str, audio_format: str, device: bool = False) -> Tuple[str, str]:
        if not settings.openai_api_key:
            return "none", ""

        url = f"{settings.openai_base_url.rstrip('/')}/audio/speech"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        # When device=True we request raw 24 kHz PCM from OpenAI then
        # downsample to 8 kHz so Core2's speaker.playRaw() can handle it.
        actual_format = "pcm" if device else (audio_format or "mp3")

        payload = {
            "model": settings.openai_tts_model,
            "voice": voice or "alloy",
            "input": text,
            "response_format": actual_format,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        if device:
            pcm_8k = _downsample_pcm(response.content)
            return "openai", base64.b64encode(pcm_8k).decode("ascii")

        return "openai", base64.b64encode(response.content).decode("ascii")


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _downsample_pcm(pcm: bytes, src_rate: int = 24000, dst_rate: int = 8000,
                    gain: float = 4.0) -> bytes:
    """Downsample 16-bit signed mono PCM by averaging groups of samples,
    then apply a gain to compensate for the amplitude loss from averaging.

    OpenAI TTS returns 24 kHz mono 16-bit PCM.
    Core2 speaker.playRaw() works best at 8 kHz (3:1 decimation).
    Averaging reduces amplitude by ~factor; gain=4.0 restores loudness.
    """
    factor = src_rate // dst_rate          # 3 for 24 kHz → 8 kHz
    n = len(pcm) // 2                      # number of 16-bit samples
    samples = struct.unpack(f"<{n}h", pcm)
    out: list[int] = []
    for i in range(0, n - factor + 1, factor):
        avg = sum(samples[i:i + factor]) // factor
        amplified = int(avg * gain)
        out.append(max(-32768, min(32767, amplified)))
    return struct.pack(f"<{len(out)}h", *out)
