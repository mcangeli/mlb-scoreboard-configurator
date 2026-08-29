from __future__ import annotations

import os
import re
import socket
import subprocess
from pathlib import Path

ENV_FILE = Path("/etc/mlb-scoreboard-configurator.env")
HOSTNAME_RE = re.compile(r"^(?=.{1,63}$)(?!-)[A-Za-z0-9-]+(?<!-)$")


def current_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return ""


def validate_hostname(hostname: str) -> str:
    hostname = (hostname or "").strip()
    if not HOSTNAME_RE.fullmatch(hostname):
        raise ValueError(
            "Hostname must be 1-63 characters using only letters, numbers, and hyphens, "
            "and cannot begin or end with a hyphen."
        )
    return hostname


def set_hostname(hostname: str) -> None:
    hostname = validate_hostname(hostname)
    subprocess.run(["hostnamectl", "set-hostname", hostname], check=True)


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value
    return data


def _validate_auth_value(name: str, value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{name} cannot be empty.")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{name} cannot contain newlines.")
    return value


def write_auth(username: str, password: str, path: Path = ENV_FILE) -> None:
    username = _validate_auth_value("Username", username)
    password = _validate_auth_value("Password", password)

    data = read_env_file(path)
    data["CONFIGURATOR_USERNAME"] = username
    data["CONFIGURATOR_PASSWORD"] = password

    preferred_order = [
        "MLB_SCOREBOARD_ROOT",
        "MLB_WIFI_INTERFACE",
        "CONFIGURATOR_HOST",
        "CONFIGURATOR_PORT",
        "CONFIGURATOR_USERNAME",
        "CONFIGURATOR_PASSWORD",
    ]
    keys = preferred_order + sorted(k for k in data if k not in preferred_order)
    lines = [f"{k}={data[k]}" for k in keys if k in data]
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def configurator_auth(path: Path = ENV_FILE) -> dict[str, str]:
    data = read_env_file(path)
    return {
        "username": data.get("CONFIGURATOR_USERNAME", "admin"),
        "password_set": bool(data.get("CONFIGURATOR_PASSWORD", "scoreboard")),
    }


def restart_configurator_service() -> None:
    subprocess.run(
        ["systemctl", "restart", "mlb-scoreboard-configurator.service"],
        check=True,
    )
