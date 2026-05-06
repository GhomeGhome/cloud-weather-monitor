from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AnnouncementDecision:
    should_announce: bool
    message: Optional[str] = None


class AnnouncementManager:
    def __init__(self, cooldown_sec: int) -> None:
        self.cooldown_sec = cooldown_sec
        self._last_announcement_ts: Optional[datetime] = None

    def evaluate(self, humidity_pct: float, tvoc_ppb: int, eco2_ppm: int, weather_hint: str) -> AnnouncementDecision:
        now = datetime.now(timezone.utc)
        if self._last_announcement_ts is not None:
            dt = (now - self._last_announcement_ts).total_seconds()
            if dt < self.cooldown_sec:
                return AnnouncementDecision(False)

        alerts = []
        if humidity_pct < 40:
            alerts.append("Humidity is low. Consider adding moisture.")
        if tvoc_ppb > 500 or eco2_ppm > 1000:
            alerts.append("Air quality is degraded. Consider ventilation.")
        if weather_hint:
            alerts.append(weather_hint)

        if not alerts:
            return AnnouncementDecision(False)

        self._last_announcement_ts = now
        return AnnouncementDecision(True, " ".join(alerts))
