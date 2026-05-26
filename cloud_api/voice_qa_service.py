import base64
import io
import json
import math
import random
import re
import struct
import wave
from typing import Dict, Any, Tuple

import requests

from bigquery_repo import BigQueryRepository
from config import settings


# ---------------------------------------------------------------------------
# Fun contextual advice catalogue
# Each key maps to a list of playful tips - one is picked at random.
# ---------------------------------------------------------------------------
_ADVICE = {
    # ── Outdoor weather ───────────────────────────────────────────────────
    "rain": [
        "Don't forget your umbrella - unless you enjoy surprise showers!",
        "Rain alert! Unless you're a duck, grab that umbrella.",
        "It's raining out there. Perfect weather for staying cozy inside!",
    ],
    "storm": [
        "Thunderstorm incoming - best to stay indoors and enjoy the show from the window!",
        "Lightning outside! Unplug your gadgets and make yourself a warm drink.",
        "Storm alert - maybe skip the outdoor run today.",
    ],
    "snow": [
        "Snow day! Boots, layers, and watch for icy patches.",
        "It's snowing - perfect excuse for hot chocolate and a blanket!",
        "Winter wonderland outside, but be careful on slippery roads!",
    ],
    "hot": [
        "It's scorching out there - don't forget your sunscreen!",
        "Hot day ahead. Stay hydrated and keep to the shade when you can.",
        "Watch out for sunburns today, it's a real scorcher!",
        "Drink plenty of water - your body will thank you!",
    ],
    "cold": [
        "Bundle up - it's freezing out there!",
        "Brrr! Don't forget your coat, scarf, and gloves.",
        "It's chilly - perfect excuse for hot chocolate on the way!",
    ],
    "wind": [
        "Quite windy today - hold onto your hat!",
        "Strong gusts today - maybe skip the umbrella, it'll flip inside-out!",
        "Windy out there - great hair day for some, bad hair day for others.",
    ],
    "clear": [
        "Gorgeous weather - get some vitamin D while it lasts!",
        "Beautiful sunny day - perfect for a walk outside!",
        "Sun's out - don't forget your sunglasses!",
    ],
    # ── Indoor air quality ────────────────────────────────────────────────
    "co2_high": [
        "Your indoor air is getting stuffy - open a window!",
        "CO2 is climbing in here. Time to air the place out!",
        "Crack open a window - the air inside could use some freshening up.",
        "High CO2 indoors - your brain will work better with some fresh air!",
    ],
    "tvoc_high": [
        "TVOC levels are elevated - ventilate the room!",
        "Something's off-gassing in here. Open a window and give it a few minutes.",
        "Air quality is not great - crack a window, it only takes a minute!",
    ],
    # ── Indoor humidity ───────────────────────────────────────────────────
    "humidity_low": [
        "The air is getting dry - your skin and sinuses will thank you for a humidifier!",
        "Pretty dry in here. Great time to water your plants - and yourself!",
        "Dry air alert - lip balm and a glass of water are your best friends right now.",
        "Low humidity indoors. Staying hydrated is extra important today!",
    ],
    "humidity_high": [
        "It's getting muggy in here - might want to crack a window!",
        "High humidity indoors - perfect conditions for feeling like a wet sponge. Ventilate!",
        "Humidity is high - a bit of airflow will make the whole place feel fresher.",
    ],
}


def _pick(key: str) -> str:
    """Return a random tip from the catalogue for the given condition key."""
    tips = _ADVICE.get(key, [])
    return random.choice(tips) if tips else ""


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
    """Human-readable air quality assessment with random contextual tips."""
    if tvoc is None and eco2 is None:
        return "unknown"
    issues = []
    if tvoc is not None:
        if tvoc < 220:
            issues.append("TVOC is good")
        elif tvoc < 660:
            issues.append(f"TVOC is moderate at {tvoc:.0f} ppb")
        else:
            issues.append(f"TVOC is high at {tvoc:.0f} ppb - {_pick('tvoc_high')}")
    if eco2 is not None:
        if eco2 < 800:
            issues.append("CO2 is excellent")
        elif eco2 < 1000:
            issues.append(f"CO2 is acceptable at {eco2:.0f} ppm")
        elif eco2 < 2000:
            issues.append(f"CO2 is elevated at {eco2:.0f} ppm - {_pick('co2_high')}")
        else:
            issues.append(f"CO2 is very high at {eco2:.0f} ppm - {_pick('co2_high')}")
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
                    tip = (" " + _pick("humidity_low")) if h < 40 else ""
                    return "humidity", f"The current indoor humidity is {h:.0f} percent.{tip}"
            return "humidity", f"I don't have humidity data for {label}."

        avg = summary["avg_humidity_pct"]
        hi  = summary.get("max_humidity_pct")
        resp = f"{label.capitalize()}, indoor humidity averaged {avg:.0f} percent"
        if hi is not None and hi > avg + 5:
            resp += f", peaking at {hi:.0f} percent"
        resp += "."
        if avg < 40:
            resp += " " + _pick("humidity_low")
        elif avg > 70:
            resp += " " + _pick("humidity_high")
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

        # Contextual advice - pick a random tip from the catalogue
        desc_l = desc.lower()
        tip = ""
        if any(w in desc_l for w in ["thunder", "storm"]):
            tip = _pick("storm")
        elif any(w in desc_l for w in ["rain", "drizzle", "shower"]):
            tip = _pick("rain")
        elif any(w in desc_l for w in ["snow", "sleet", "blizzard", "freezing"]):
            tip = _pick("snow")
        elif any(w in desc_l for w in ["clear", "sunny"]):
            if tmax is not None and tmax >= 28:
                tip = _pick("hot")
            else:
                tip = _pick("clear")
        elif any(w in desc_l for w in ["wind", "gust", "breezy"]):
            tip = _pick("wind")
        if tmax is not None and tmax >= 30 and not tip:
            tip = _pick("hot")
        elif tmax is not None and tmax <= 2 and not tip:
            tip = _pick("cold")
        if tip:
            resp += f" {tip}"

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
                    alerts.append(_pick("humidity_low"))
                elif avg_h > 70:
                    alerts.append(_pick("humidity_high"))

        if aq:
            avg_tvoc = aq.get("avg_tvoc_ppb")
            avg_eco2 = aq.get("avg_eco2_ppm")
            if avg_tvoc is not None and avg_tvoc > 220:
                alerts.append(f"TVOC was elevated at {avg_tvoc:.0f} ppb - {_pick('tvoc_high')}")
            if avg_eco2 is not None and avg_eco2 > 1000:
                alerts.append(f"CO2 was high at {avg_eco2:.0f} ppm - {_pick('co2_high')}")

        if not parts:
            return "no_data", f"I don't have enough data for {label} yet."

        resp = f"Here is a summary for {label}: " + ", ".join(parts) + "."
        if alerts:
            resp += " Note: " + "; ".join(alerts) + "."
        return "summary", resp

    # ------------------------------------------------------------------
    # PIR greeting
    # ------------------------------------------------------------------
    def generate_greeting(self, device_id: str, utc_hour: int | None = None) -> str:
        """Build a friendly spoken greeting for PIR-triggered announcements.

        Format: "Good <time>! Today, <weather>. <indoor note if notable>. <tip>."
        """
        from datetime import datetime, timezone
        if utc_hour is None:
            utc_hour = datetime.now(timezone.utc).hour

        # Time-of-day salutation
        if 5 <= utc_hour < 12:
            salutation = "Good morning"
        elif 12 <= utc_hour < 18:
            salutation = "Good afternoon"
        elif 18 <= utc_hour < 22:
            salutation = "Good evening"
        else:
            salutation = "Hello"

        parts = [f"{salutation}!"]
        tip = ""

        # ── Outdoor weather ──────────────────────────────────────────────
        outdoor = self.repo.get_latest_outdoor()
        if outdoor:
            temp  = outdoor.get("temperature_c")
            desc  = outdoor.get("weather_description") or outdoor.get("weather_main") or ""
            desc_l = desc.lower()

            weather_str = "Today"
            if temp is not None:
                weather_str += f", it's {temp:.0f} degrees outside"
            if desc:
                weather_str += f" with {desc.lower()}"
            parts.append(weather_str + ".")

            # Pick tip based on outdoor conditions
            if any(w in desc_l for w in ["thunder", "storm"]):
                tip = _pick("storm")
            elif any(w in desc_l for w in ["rain", "drizzle", "shower"]):
                tip = _pick("rain")
            elif any(w in desc_l for w in ["snow", "sleet", "blizzard", "freezing"]):
                tip = _pick("snow")
            elif any(w in desc_l for w in ["wind", "gust", "breezy"]):
                tip = _pick("wind")
            elif temp is not None and temp >= 28:
                tip = _pick("hot")
            elif temp is not None and temp <= 2:
                tip = _pick("cold")
            elif any(w in desc_l for w in ["clear", "sunny"]):
                tip = _pick("clear")

        # ── Indoor conditions (override tip only if outdoor gave nothing) ──
        try:
            snap     = self._latest_indoor(device_id)
            humidity = snap.get("humidity_pct")
            eco2     = snap.get("eco2_ppm")
            tvoc     = snap.get("tvoc_ppb")

            if humidity is not None and humidity < 40:
                if not tip:
                    tip = _pick("humidity_low")
                parts.append(f"Indoor humidity is low at {humidity:.0f} percent.")
            elif humidity is not None and humidity > 70:
                if not tip:
                    tip = _pick("humidity_high")
                parts.append(f"Indoor humidity is high at {humidity:.0f} percent.")

            if eco2 is not None and eco2 > 1500:
                if not tip:
                    tip = _pick("co2_high")
                parts.append(f"CO2 indoors is elevated at {eco2:.0f} ppm.")
            elif tvoc is not None and tvoc > 500:
                if not tip:
                    tip = _pick("tvoc_high")
        except Exception:
            pass

        if tip:
            parts.append(tip)

        return " ".join(parts)

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

        # Pass raw bytes directly - io.BytesIO.name is not settable in Python 3.11
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
            # 1. Decimate 24 kHz → 8 kHz (factor 3 — Core2 speaker max rate)
            # 2. Normalize to 95 % full-scale; max_gain=200 handles OpenAI TTS
            #    which outputs at ~1-5 % of full scale.
            # Mono WAV: the device uses machine.I2S directly with ALL_LEFT
            # channel format, which sends the mono sample to both I2S L and R
            # slots so the AW88298 receives full amplitude on both inputs.
            pcm_8k = _downsample_pcm(response.content, src_rate=24000, dst_rate=8000)
            pcm_loud = _normalize_pcm(pcm_8k, headroom=0.95, max_gain=10)
            wav = _pcm_to_wav(pcm_loud, rate=8000)
            return "openai", base64.b64encode(wav).decode("ascii")

        return "openai", base64.b64encode(response.content).decode("ascii")


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _downsample_pcm(pcm: bytes, src_rate: int = 24000, dst_rate: int = 8000) -> bytes:
    """Downsample 16-bit signed mono PCM with box-filter averaging.

    Simple decimation (take every Nth sample) causes high-frequency aliasing
    that sounds like crackling/static at 8 kHz playback.  Averaging each
    group of N samples acts as a crude low-pass (anti-aliasing) filter and
    eliminates those artefacts.
    """
    factor = src_rate // dst_rate          # 3 for 24 kHz → 8 kHz
    n = len(pcm) // 2
    samples = struct.unpack(f"<{n}h", pcm)
    decimated = tuple(
        sum(samples[i:i + factor]) // factor
        for i in range(0, n - factor + 1, factor)
    )
    return struct.pack(f"<{len(decimated)}h", *decimated)


def _normalize_pcm(pcm: bytes, headroom: float = 0.90, max_gain: float = 30.0) -> bytes:
    """Normalize PCM so the loudest sample reaches headroom * MAX.

    OpenAI TTS outputs at ~5-15 % of full scale. This measures the actual
    peak and scales the whole signal up so it hits 90 % of max — guaranteed
    loud without distortion, regardless of input level.
    max_gain caps amplification so near-silent passages are not blown up.
    """
    n = len(pcm) // 2
    if n == 0:
        return pcm
    MAX = 32767.0
    samples = struct.unpack(f"<{n}h", pcm)
    peak = max(abs(s) for s in samples)
    if peak == 0:
        return pcm
    scale = min(headroom * MAX / peak, max_gain)
    normalized = tuple(max(-32768, min(32767, int(s * scale))) for s in samples)
    return struct.pack(f"<{n}h", *normalized)


def _mono_to_stereo_pcm(pcm: bytes) -> bytes:
    """Duplicate each mono 16-bit sample to both L and R channels.

    The Core2 AW88298 amplifier mixes L+R into its mono speaker output.
    With CHN_L playback the R channel is silence, so the sum is signal/2 (-6 dB).
    Sending the same sample on both channels gives L+R = full amplitude.
    The resulting buffer is twice as long; playRaw with CHN_LR at the same
    sample_rate produces the correct duration and pitch.
    """
    n = len(pcm) // 2
    samples = struct.unpack(f"<{n}h", pcm)
    stereo = [val for s in samples for val in (s, s)]
    return struct.pack(f"<{n * 2}h", *stereo)


def _soft_limit_pcm(pcm: bytes, gain: float = 8.0) -> bytes:
    """Apply gain then tanh soft-limiting - kept for reference."""
    n = len(pcm) // 2
    if n == 0:
        return pcm
    MAX = 32767.0
    samples = struct.unpack(f"<{n}h", pcm)
    limited = tuple(int(math.tanh(s * gain / MAX) * MAX) for s in samples)
    return struct.pack(f"<{n}h", *limited)


def _pcm_to_wav(pcm: bytes, channels: int = 1, rate: int = 8000) -> bytes:
    """Wrap raw 16-bit signed mono PCM in a RIFF WAV container."""
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)   # 16-bit
        w.setframerate(rate)
        w.writeframes(pcm)
    return out.getvalue()
