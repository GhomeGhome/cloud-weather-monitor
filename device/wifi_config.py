import json
from pathlib import Path
from typing import Dict


WIFI_CONFIG_PATH = Path("device/wifi_config.json")


def load_wifi_config(default_ssid: str, default_password: str) -> Dict[str, str]:
    if WIFI_CONFIG_PATH.exists():
        return json.loads(WIFI_CONFIG_PATH.read_text(encoding="utf-8"))
    return {"ssid": default_ssid, "password": default_password}


def save_wifi_config(ssid: str, password: str) -> None:
    WIFI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    WIFI_CONFIG_PATH.write_text(json.dumps({"ssid": ssid, "password": password}), encoding="utf-8")
