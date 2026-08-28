import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path("/etc/mlb-scoreboard-configurator.env")
SYSTEMD_DIR = Path("/etc/systemd/system")

CONFIG_SERVICE = """[Unit]
Description=MLB LED Scoreboard Web Configurator
After=NetworkManager.service network.target
Wants=NetworkManager.service

[Service]
Type=simple
EnvironmentFile=-/etc/mlb-scoreboard-configurator.env
WorkingDirectory={root}
ExecStart={venv}/mlb-scoreboard-configurator
Restart=on-failure
RestartSec=3
User=root
Group=root
NoNewPrivileges=false

[Install]
WantedBy=multi-user.target
"""

HOTSPOT_SERVICE = """[Unit]
Description=MLB LED Scoreboard fallback hotspot check
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
EnvironmentFile=-/etc/mlb-scoreboard-configurator.env
WorkingDirectory={root}
ExecStart={venv}/mlb-scoreboard-hotspot-watch
User=root
Group=root
"""

HOTSPOT_TIMER = """[Unit]
Description=Check MLB Scoreboard Wi-Fi fallback once per minute

[Timer]
OnBootSec=20s
OnUnitActiveSec=60s
AccuracySec=10s
Persistent=true

[Install]
WantedBy=timers.target
"""

def run(args, check=True):
    print("+", " ".join(str(x) for x in args))
    return subprocess.run([str(x) for x in args], check=check)

def require_root():
    if os.geteuid() != 0:
        print(
            "This setup command installs systemd units under /etc and must be run with sudo.\n"
            f"Try:\n  sudo {sys.executable.rsplit('/',1)[0]}/mlb-scoreboard-configurator-setup",
            file=sys.stderr,
        )
        raise SystemExit(2)

def detect_scoreboard_root(explicit=None):
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("MLB_SCOREBOARD_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    cwd = Path.cwd().resolve()
    if (cwd / "config.json").exists() and (cwd / "coordinates").exists():
        return cwd

    # Common install location fallback.
    common = Path("/home/pi/mlb-led-scoreboard")
    if common.exists():
        return common.resolve()

    raise SystemExit(
        "Could not determine MLB-LED-Scoreboard root. "
        "Run this from the mlb-led-scoreboard directory or pass --root /path/to/mlb-led-scoreboard."
    )

def detect_venv(root: Path, explicit=None):
    if explicit:
        venv = Path(explicit).expanduser().resolve()
    else:
        candidates = []

        # Prefer the directory containing the invoked console script. This
        # remains correct when the command is run through sudo, where
        # sys.executable may resolve to /usr/bin/python.
        invoked = Path(sys.argv[0]).expanduser()
        try:
            invoked = invoked.resolve()
            if invoked.parent.name == "bin":
                candidates.append(invoked.parent)
        except Exception:
            pass

        # Then try the active Python interpreter.
        current = Path(sys.executable).resolve()
        if current.parent.name == "bin":
            candidates.append(current.parent)

        # Finally fall back to the conventional scoreboard venv.
        candidates.append((root / "venv" / "bin").resolve())

        required = ["mlb-scoreboard-configurator", "mlb-scoreboard-hotspot-watch"]
        venv = next(
            (candidate for candidate in candidates
             if all((candidate / name).exists() for name in required)),
            candidates[-1],
        )

    required = ["mlb-scoreboard-configurator", "mlb-scoreboard-hotspot-watch"]
    missing = [name for name in required if not (venv / name).exists()]
    if missing:
        raise SystemExit(
            f"Could not find installed configurator executables in {venv}. "
            "Install the package first with the scoreboard venv/bin/pip."
        )
    return venv

def nmcli_check():
    if not shutil.which("nmcli"):
        raise SystemExit(
            "nmcli is required for Wi-Fi/hotspot management. "
            "Install/enable NetworkManager before running setup."
        )

def write_if_changed(path: Path, content: str, mode=0o644):
    old = path.read_text() if path.exists() else None
    if old != content:
        path.write_text(content)
        os.chmod(path, mode)
        print(f"Updated {path}")
        return True
    print(f"Unchanged {path}")
    return False

def ensure_env(root: Path, interface: str, port: int):
    defaults = {
        "MLB_SCOREBOARD_ROOT": str(root),
        "MLB_WIFI_INTERFACE": interface,
        "CONFIGURATOR_HOST": "0.0.0.0",
        "CONFIGURATOR_PORT": str(port),
        "CONFIGURATOR_USERNAME": "admin",
        "CONFIGURATOR_PASSWORD": "scoreboard",
    }

    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            existing[k] = v

    changed = False
    for k, v in defaults.items():
        if k not in existing:
            existing[k] = v
            changed = True

    # Always keep root/interface/port in sync with explicit setup inputs.
    for k, v in {
        "MLB_SCOREBOARD_ROOT": str(root),
        "MLB_WIFI_INTERFACE": interface,
        "CONFIGURATOR_PORT": str(port),
    }.items():
        if existing.get(k) != v:
            existing[k] = v
            changed = True

    content = "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n"
    if not ENV_FILE.exists() or changed or ENV_FILE.read_text() != content:
        ENV_FILE.write_text(content)
        os.chmod(ENV_FILE, 0o600)
        print(f"Updated {ENV_FILE}")
    else:
        print(f"Unchanged {ENV_FILE}")

    if existing.get("CONFIGURATOR_PASSWORD") == "scoreboard":
        print("\nWARNING: CONFIGURATOR_PASSWORD is still the default 'scoreboard'.")
        print(f"Change it in {ENV_FILE}, then restart mlb-scoreboard-configurator.service.\n")

def main():
    parser = argparse.ArgumentParser(
        description="Install/update systemd integration for MLB Scoreboard Configurator."
    )
    parser.add_argument("--root", help="Path to MLB-LED-Scoreboard checkout.")
    parser.add_argument("--venv-bin", help="Path to the scoreboard virtualenv bin directory.")
    parser.add_argument("--wifi-interface", default=os.environ.get("MLB_WIFI_INTERFACE", "wlan0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CONFIGURATOR_PORT", "8080")))
    parser.add_argument("--no-enable", action="store_true", help="Install/update units without enabling/starting them.")
    args = parser.parse_args()

    require_root()
    nmcli_check()

    root = detect_scoreboard_root(args.root)
    venv = detect_venv(root, args.venv_bin)

    if not (root / "config.json").exists():
        raise SystemExit(f"{root} does not look like an MLB-LED-Scoreboard checkout (config.json missing).")

    changed = False
    changed |= write_if_changed(
        SYSTEMD_DIR / "mlb-scoreboard-configurator.service",
        CONFIG_SERVICE.format(root=root, venv=venv),
    )
    changed |= write_if_changed(
        SYSTEMD_DIR / "mlb-scoreboard-hotspot-watch.service",
        HOTSPOT_SERVICE.format(root=root, venv=venv),
    )
    changed |= write_if_changed(
        SYSTEMD_DIR / "mlb-scoreboard-hotspot-watch.timer",
        HOTSPOT_TIMER,
    )

    ensure_env(root, args.wifi_interface, args.port)

    if changed:
        run(["systemctl", "daemon-reload"])

    if not args.no_enable:
        run(["systemctl", "enable", "--now", "mlb-scoreboard-configurator.service"])
        run(["systemctl", "enable", "--now", "mlb-scoreboard-hotspot-watch.timer"])
        # Restart to pick up a package upgrade or changed env/unit definitions.
        run(["systemctl", "restart", "mlb-scoreboard-configurator.service"])
        run(["systemctl", "restart", "mlb-scoreboard-hotspot-watch.timer"])

    print("\nMLB Scoreboard Configurator setup complete.")
    print(f"Scoreboard root: {root}")
    print(f"Virtualenv bin:  {venv}")
    print(f"Web UI:          http://<raspberry-pi-ip>:{args.port}/")
    print("\nFuture upgrades:")
    print("  sudo venv/bin/pip install --upgrade git+https://github.com/mcangeli/mlb-scoreboard-configurator.git")
    print("  sudo venv/bin/mlb-scoreboard-configurator-setup")

if __name__ == "__main__":
    main()
