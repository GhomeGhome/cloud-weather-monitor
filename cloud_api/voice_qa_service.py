import base64
import io
import re
from typing import Tuple

import requests

from bigquery_repo import BigQueryRepository
from config import settings


class VoiceQaService:
    def __init__(self, repo: BigQueryRepository) -> None:
        self.repo = repo

    def answer_question(self, device_id: str, question: str) -> Tuple[str, str]:
        q = (question or "").strip()
        ql = q.lower()

        # "what was the temperature at home yesterday?"
        if "temperature" in ql and "yesterday" in ql:
            summary = self.repo.get_day_summary(device_id=device_id, days_ago=1)
            if not summary:
                return "temperature_yesterday", "I could not find data for yesterday."
            avg_t = summary.get("avg_temp_c")
            min_t = summary.get("min_temp_c")
            max_t = summary.get("max_temp_c")
            if avg_t is None:
                return "temperature_yesterday", "I found yesterday data, but temperature is missing."
            return (
                "temperature_yesterday",
                "Yesterday at home, average temperature was {:.1f} C (min {:.1f} C, max {:.1f} C).".format(
                    float(avg_t),
                    float(min_t) if min_t is not None else float(avg_t),
                    float(max_t) if max_t is not None else float(avg_t),
                ),
            )

        # "Did humidity exceed 50% 2 days ago?"
        if "humidity" in ql and "exceed" in ql:
            threshold_match = re.search(r"(\d+(?:\.\d+)?)\s*%", ql)
            days_match = re.search(r"(\d+)\s+day", ql)
            threshold = float(threshold_match.group(1)) if threshold_match else 50.0
            days_ago = int(days_match.group(1)) if days_match else (1 if "yesterday" in ql else 0)
            exceeded = self.repo.did_humidity_exceed(
                device_id=device_id, threshold_pct=threshold, days_ago=days_ago
            )
            label = "yesterday" if days_ago == 1 else f"{days_ago} days ago"
            return (
                "humidity_exceed",
                f"Yes, humidity exceeded {threshold:.0f}% {label}."
                if exceeded
                else f"No, humidity did not exceed {threshold:.0f}% {label}.",
            )

        # Generic fallback: return most recent day summary.
        summary = self.repo.get_day_summary(device_id=device_id, days_ago=0)
        if not summary:
            return "fallback", "I could not parse this question yet, and I have no recent data."
        avg_t = summary.get("avg_temp_c")
        avg_h = summary.get("avg_humidity_pct")
        return (
            "fallback",
            "I can answer temperature and humidity history questions. "
            "Today so far: avg temperature {:.1f} C, avg humidity {:.1f}%.".format(
                float(avg_t) if avg_t is not None else 0.0,
                float(avg_h) if avg_h is not None else 0.0,
            ),
        )

    def speech_to_text(self, audio_base64: str, mime_type: str, language: str) -> Tuple[str, str]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")

        audio_bytes = base64.b64decode(audio_base64)
        ext = ".wav"
        if "mp3" in (mime_type or ""):
            ext = ".mp3"
        elif "webm" in (mime_type or ""):
            ext = ".webm"
        elif "ogg" in (mime_type or ""):
            ext = ".ogg"

        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = f"audio{ext}"

        url = f"{settings.openai_base_url.rstrip('/')}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        files = {"file": (file_obj.name, file_obj, mime_type or "application/octet-stream")}
        data = {"model": settings.openai_stt_model, "language": language or "en"}

        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        response.raise_for_status()
        payload = response.json()
        return "openai", payload.get("text", "")

    def text_to_speech(self, text: str, voice: str, audio_format: str) -> Tuple[str, str]:
        if not settings.openai_api_key:
            # Fallback text-only mode for demos when no key is configured.
            return "none", ""

        url = f"{settings.openai_base_url.rstrip('/')}/audio/speech"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_tts_model,
            "voice": voice or "alloy",
            "input": text,
            "format": audio_format or "mp3",
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return "openai", base64.b64encode(response.content).decode("ascii")
