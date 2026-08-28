import subprocess
from .settings import load_settings, wifi_interface

def run(args, timeout=30):
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        class R:
            returncode = 127
            stdout = ""
            stderr = "nmcli was not found"
        return R()

def _unescape_nmcli(value):
    return value.replace("\\:", ":")

def status():
    r = run(["nmcli", "-t", "-f", "TYPE,DEVICE,STATE,CONNECTION", "device", "status"])
    devices = []
    connected_wifi = None
    for line in r.stdout.splitlines():
        p = line.split(":")
        if len(p) >= 4:
            item = {"type": p[0], "device": p[1], "state": p[2], "connection": ":".join(p[3:])}
            devices.append(item)
            if p[0] == "wifi" and p[2] == "connected":
                # Ignore our fallback AP as a client connection.
                if item["connection"] != load_settings()["hotspot_connection_name"]:
                    connected_wifi = item
    return {
        "connected": connected_wifi is not None,
        "connection": connected_wifi,
        "devices": devices,
        "interface": wifi_interface(),
        "hotspot_active": hotspot_active(),
    }

def scan():
    iface = wifi_interface()
    run(["nmcli", "device", "wifi", "rescan", "ifname", iface], timeout=15)
    r = run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE", "device", "wifi", "list", "ifname", iface])
    seen, results = set(), []
    for line in r.stdout.splitlines():
        p = line.split(":")
        if not p:
            continue
        ssid = _unescape_nmcli(p[0])
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        results.append({
            "ssid": ssid,
            "signal": p[1] if len(p) > 1 else "",
            "security": p[2] if len(p) > 2 else "",
            "in_use": p[3] == "*" if len(p) > 3 else False,
        })
    return sorted(results, key=lambda x: int(x["signal"] or 0), reverse=True)

def connect(ssid, password=""):
    if not ssid:
        return False, "SSID is required."
    stop_hotspot()
    args = ["nmcli", "device", "wifi", "connect", ssid, "ifname", wifi_interface()]
    if password:
        args += ["password", password]
    r = run(args, timeout=45)
    return r.returncode == 0, (r.stdout + r.stderr).strip()

def disconnect():
    r = run(["nmcli", "device", "disconnect", wifi_interface()])
    return r.returncode == 0, (r.stdout + r.stderr).strip()

def hotspot_active():
    s = load_settings()
    r = run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"])
    for line in r.stdout.splitlines():
        p = line.split(":")
        if len(p) >= 3 and p[0] == s["hotspot_connection_name"] and p[2] == wifi_interface():
            return True
    return False

def start_hotspot():
    s = load_settings()
    if not s.get("hotspot_enabled", True):
        return False, "Fallback hotspot is disabled."
    if len(s["hotspot_password"]) < 8:
        return False, "Hotspot password must be at least 8 characters."
    name = s["hotspot_connection_name"]
    iface = wifi_interface()
    # Recreate to guarantee current SSID/password.
    run(["nmcli", "connection", "delete", name], timeout=10)
    r = run([
        "nmcli", "connection", "add", "type", "wifi", "ifname", iface,
        "con-name", name, "autoconnect", "no", "ssid", s["hotspot_ssid"]
    ])
    if r.returncode != 0:
        return False, (r.stdout + r.stderr).strip()
    commands = [
        ["nmcli", "connection", "modify", name, "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg"],
        ["nmcli", "connection", "modify", name, "ipv4.method", "shared", "ipv6.method", "disabled"],
        ["nmcli", "connection", "modify", name, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", s["hotspot_password"]],
    ]
    for cmd in commands:
        x = run(cmd)
        if x.returncode != 0:
            return False, (x.stdout + x.stderr).strip()
    up = run(["nmcli", "connection", "up", name], timeout=30)
    return up.returncode == 0, (up.stdout + up.stderr).strip()

def stop_hotspot():
    s = load_settings()
    if not hotspot_active():
        return True, "Hotspot is not active."
    r = run(["nmcli", "connection", "down", s["hotspot_connection_name"]])
    return r.returncode == 0, (r.stdout + r.stderr).strip()

def maintain_hotspot():
    s = load_settings()
    st = status()
    if st["connected"]:
        if st["hotspot_active"]:
            return stop_hotspot()
        return True, "Client Wi-Fi is connected."
    if s.get("hotspot_enabled", True):
        if st["hotspot_active"]:
            return True, "Fallback hotspot is already active."
        return start_hotspot()
    if st["hotspot_active"]:
        return stop_hotspot()
    return True, "Fallback hotspot is disabled."
