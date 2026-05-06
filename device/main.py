import time

from announcer import AnnouncementManager
from cloud_client import CloudClient
from config import settings
from sensors import SensorManager
from ui import DeviceUI
from wifi_config import load_wifi_config


def weather_hint(weather_payload: dict) -> str:
    data = weather_payload.get("weather", {}) if isinstance(weather_payload, dict) else {}
    desc = (data.get("weather_description") or "").lower()
    if "rain" in desc:
        return "Rain is expected. Take an umbrella."
    if "storm" in desc:
        return "Storm conditions expected. Be careful outside."
    return ""


def run() -> None:
    wifi = load_wifi_config(settings.wifi_ssid, settings.wifi_password)
    print(f"[BOOT] using wifi ssid={wifi.get('ssid')}")

    sensors = SensorManager()
    ui = DeviceUI()
    cloud = CloudClient()
    announcer = AnnouncementManager(cooldown_sec=settings.speech_cooldown_sec)

    try:
        snapshot = cloud.latest_snapshot()
        ui.render_boot_snapshot(snapshot)
    except Exception as exc:
        print(f"[WARN] failed to load boot snapshot: {exc}")

    last_ingest_ts = 0.0
    while True:
        reading = sensors.read()
        weather = {}
        try:
            weather = cloud.latest_weather(refresh=False)
        except Exception as exc:
            print(f"[WARN] weather fetch failed: {exc}")
        ui.render(reading, weather)

        now = time.time()
        if now - last_ingest_ts >= settings.ingest_interval_sec:
            try:
                ingest_response = cloud.ingest(reading)
                print(f"[INGEST] {ingest_response}")
                last_ingest_ts = now
            except Exception as exc:
                print(f"[ERROR] ingest failed: {exc}")

        decision = announcer.evaluate(
            humidity_pct=reading.humidity_pct,
            tvoc_ppb=reading.tvoc_ppb,
            eco2_ppm=reading.eco2_ppm,
            weather_hint=weather_hint(weather),
        )
        if decision.should_announce and decision.message:
            ui.announce(decision.message)

        time.sleep(settings.sensor_interval_sec)


if __name__ == "__main__":
    run()
