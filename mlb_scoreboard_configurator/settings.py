import json
import os
import secrets
from pathlib import Path

def scoreboard_root() -> Path:
    return Path(os.environ.get("MLB_SCOREBOARD_ROOT", "/home/pi/mlb-led-scoreboard")).resolve()

def state_dir() -> Path:
    p = scoreboard_root() / ".configurator"
    p.mkdir(parents=True, exist_ok=True)
    return p

SETTINGS_DEFAULTS = {
    "hotspot_enabled": True,
    "hotspot_ssid": "MLB-Scoreboard-Setup",
    "hotspot_password": "ScoreboardSetup",
    "hotspot_connection_name": "mlb-scoreboard-setup",
}

def settings_path():
    return state_dir() / "settings.json"

def load_settings():
    data = dict(SETTINGS_DEFAULTS)
    p = settings_path()
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except Exception:
            pass
    return data

def save_settings(data):
    out = dict(SETTINGS_DEFAULTS)
    out.update({k: data.get(k, v) for k, v in SETTINGS_DEFAULTS.items()})
    if len(str(out["hotspot_password"])) < 8:
        raise ValueError("Hotspot password must be at least 8 characters.")
    tmp = settings_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, settings_path())
    return out

def web_username():
    return os.environ.get("CONFIGURATOR_USERNAME", "admin")

def web_password():
    return os.environ.get("CONFIGURATOR_PASSWORD", "scoreboard")

def wifi_interface():
    return os.environ.get("MLB_WIFI_INTERFACE", "wlan0")
