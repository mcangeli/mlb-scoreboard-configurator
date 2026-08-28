import subprocess

SERVICE = "mlb-led-scoreboard.service"
ALLOWED_ACTIONS = {"start", "stop", "restart"}

def _run(args):
    return subprocess.run(args, text=True, capture_output=True, timeout=30)

def status():
    r = _run(["systemctl", "show", SERVICE, "--property=ActiveState,SubState,UnitFileState", "--no-page"])
    values = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values[k] = v
    return {
        "ok": r.returncode == 0,
        "active_state": values.get("ActiveState", "unknown"),
        "sub_state": values.get("SubState", "unknown"),
        "unit_file_state": values.get("UnitFileState", "unknown"),
        "message": (r.stderr or "").strip(),
    }

def action(name):
    if name not in ALLOWED_ACTIONS:
        return False, "Unsupported action."
    r = _run(["systemctl", name, SERVICE])
    return r.returncode == 0, (r.stdout + r.stderr).strip()
