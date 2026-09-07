import subprocess

SERVICES = {
    "scoreboard": "mlb-led-scoreboard.service",
    "configurator": "mlb-scoreboard-configurator.service",
}
ALLOWED_ACTIONS = {"start", "stop", "restart"}


def _run(args):
    return subprocess.run(args, text=True, capture_output=True, timeout=30)


def _service_name(target: str) -> str:
    try:
        return SERVICES[target]
    except KeyError:
        raise ValueError("Unsupported service target.")


def status(target: str = "scoreboard"):
    service_name = _service_name(target)
    r = _run([
        "systemctl", "show", service_name,
        "--property=ActiveState,SubState,UnitFileState", "--no-page"
    ])
    values = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values[k] = v
    return {
        "ok": r.returncode == 0,
        "target": target,
        "service": service_name,
        "active_state": values.get("ActiveState", "unknown"),
        "sub_state": values.get("SubState", "unknown"),
        "unit_file_state": values.get("UnitFileState", "unknown"),
        "message": (r.stderr or "").strip(),
    }


def action(name: str, target: str = "scoreboard"):
    if name not in ALLOWED_ACTIONS:
        return False, "Unsupported action."
    try:
        service_name = _service_name(target)
    except ValueError as e:
        return False, str(e)
    r = _run(["systemctl", name, service_name])
    return r.returncode == 0, (r.stdout + r.stderr).strip()
