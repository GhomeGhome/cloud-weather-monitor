from typing import Any, Dict

from sensors import SensorReading


class DeviceUI:
    """
    Placeholder UI implementation for local testing.
    Replace print calls with M5Stack widgets on hardware.
    """

    def render(self, reading: SensorReading, weather: Dict[str, Any]) -> None:
        weather_data = weather.get("weather", {}) if isinstance(weather, dict) else {}
        line = (
            f"[UI] indoor: {reading.temperature_c}C / {reading.humidity_pct}% "
            f"tvoc={reading.tvoc_ppb} eco2={reading.eco2_ppm} motion={reading.motion_detected} | "
            f"outdoor: {weather_data.get('temperature_c')}C {weather_data.get('weather_main')}"
        )
        print(line)

    def render_boot_snapshot(self, snapshot: Dict[str, Any]) -> None:
        print(f"[UI] boot snapshot loaded: {snapshot}")

    def announce(self, text: str) -> None:
        print(f"[TTS] {text}")
