import hmac
import os
import subprocess
from functools import wraps
from flask import Flask, Response, jsonify, render_template, request
from waitress import serve
from . import network, service
from .settings import load_settings, save_settings, web_username, web_password
from . import __version__
from .plugin_manager import installed_plugins, install_plugin
from .system_settings import (
    current_hostname, validate_hostname, set_hostname,
    configurator_auth, write_auth, restart_configurator_service
)
from .storage import (
    named_path, read_json, write_json, coordinate_files, config_schema,
    validate, list_backups, restore_backup, ensure_color_files
)

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def disable_cache(response):
    if request.path.startswith("/api/") or request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

def check_auth(auth):
    return bool(
        auth and
        hmac.compare_digest(auth.username or "", web_username()) and
        hmac.compare_digest(auth.password or "", web_password())
    )

def require_auth(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not check_auth(request.authorization):
            return Response(
                "Authentication required.",
                401,
                {"WWW-Authenticate": 'Basic realm="MLB Scoreboard Configurator"'}
            )
        return fn(*args, **kwargs)
    return wrapped

@app.before_request
def authenticate():
    if request.path == "/healthz":
        return None
    if not check_auth(request.authorization):
        return Response(
            "Authentication required.",
            401,
            {"WWW-Authenticate": 'Basic realm="MLB Scoreboard Configurator"'}
        )

@app.get("/healthz")
def health():
    return jsonify(ok=True)

@app.get("/")
def index():
    return render_template("index.html", configurator_version=__version__)

@app.get("/api/bootstrap")
def bootstrap():
    ensure_color_files()
    files = [
        {"id": "config", "label": "config.json", "kind": "config"},
        {"id": "teams", "label": "colors/teams.json", "kind": "colors"},
        {"id": "scoreboard", "label": "colors/scoreboard.json", "kind": "colors"},
    ]
    files += [
        {"id": f"coordinates/{f}", "label": f"coordinates/{f}", "kind": "coordinates"}
        for f in coordinate_files()
    ]
    return jsonify(
        files=files,
        wifi=network.status(),
        settings=load_settings(),
        service=service.status(),
    )

@app.get("/api/file/<path:name>")
def get_file(name):
    try:
        if name in ("teams", "scoreboard"):
            ensure_color_files()
        data = read_json(named_path(name))
        payload = {"data": data, "validation": validate(name, data)}
        if name == "config":
            payload["schema"] = config_schema()
        return jsonify(payload)
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.post("/api/file/<path:name>/validate")
def validate_file(name):
    try:
        data = request.get_json(force=True)
        return jsonify(ok=not validate(name, data), errors=validate(name, data))
    except Exception as e:
        return jsonify(ok=False, errors=[{"path": "(root)", "message": str(e)}]), 400

@app.put("/api/file/<path:name>")
def put_file(name):
    try:
        data = request.get_json(force=True)
        if not isinstance(data, (dict, list)):
            raise ValueError("JSON root must be an object or array.")
        ok, errors = write_json(name, data)
        if not ok:
            return jsonify(ok=False, errors=errors), 422
        return jsonify(ok=True, backups=list_backups(name))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400

@app.get("/api/file/<path:name>/backups")
def backups(name):
    try:
        return jsonify(backups=list_backups(name))
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.post("/api/file/<path:name>/restore")
def restore(name):
    try:
        backup_id = request.get_json(force=True).get("backup_id", "")
        ok, errors = restore_backup(name, backup_id)
        return jsonify(ok=ok, errors=errors), (200 if ok else 422)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400

@app.get("/api/wifi/status")
def wifi_status():
    return jsonify(network.status())

@app.get("/api/wifi/networks")
def wifi_networks():
    return jsonify(networks=network.scan())

@app.post("/api/wifi/connect")
def wifi_connect():
    body = request.get_json(force=True) or {}
    ok, message = network.connect(str(body.get("ssid", "")), str(body.get("password", "")))
    return jsonify(ok=ok, message=message, status=network.status()), (200 if ok else 400)

@app.post("/api/wifi/disconnect")
def wifi_disconnect():
    ok, message = network.disconnect()
    return jsonify(ok=ok, message=message, status=network.status()), (200 if ok else 400)

@app.post("/api/wifi/hotspot/<action>")
def hotspot(action):
    if action == "start":
        ok, message = network.start_hotspot()
    elif action == "stop":
        ok, message = network.stop_hotspot()
    else:
        return jsonify(ok=False, message="Unsupported hotspot action."), 400
    return jsonify(ok=ok, message=message, status=network.status()), (200 if ok else 400)

@app.get("/api/settings")
def get_settings():
    return jsonify(load_settings())

@app.put("/api/settings")
def put_settings():
    try:
        return jsonify(ok=True, settings=save_settings(request.get_json(force=True) or {}))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400

@app.get("/api/service/status")
def service_status():
    return jsonify(service.status())

@app.post("/api/service/<action>")
def service_action(action):
    ok, message = service.action(action)
    return jsonify(ok=ok, message=message, status=service.status()), (200 if ok else 400)


@app.get("/api/plugins")
@require_auth
def get_plugins():
    try:
        return jsonify(plugins=installed_plugins())
    except Exception as e:
        return jsonify(error=f"Could not enumerate installed plugins: {e}"), 500

@app.post("/api/plugins/install")
@require_auth
def install_plugin_from_github():
    payload = request.get_json(silent=True) or {}
    try:
        result = install_plugin(str(payload.get("url", "")))
        result["ok"] = True
        result["plugins"] = installed_plugins()
        return jsonify(result)
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    except subprocess.TimeoutExpired:
        return jsonify(ok=False, error="Plugin installation timed out."), 504
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

def main():
    host = os.environ.get("CONFIGURATOR_HOST", "0.0.0.0")
    port = int(os.environ.get("CONFIGURATOR_PORT", "8080"))
    serve(app, host=host, port=port, threads=6)


@app.get("/api/system/settings")
@require_auth
def system_settings_get():
    auth = configurator_auth()
    return jsonify({
        "hostname": current_hostname(),
        "username": auth["username"],
        "password_set": auth["password_set"],
    })


@app.put("/api/system/hostname")
@require_auth
def system_hostname_put():
    payload = request.get_json(silent=True) or {}
    hostname = payload.get("hostname", "")
    try:
        hostname = validate_hostname(hostname)
        set_hostname(hostname)
        return jsonify({"ok": True, "hostname": hostname})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"Could not change hostname: {e}"}), 500


@app.put("/api/system/auth")
@require_auth
def system_auth_put():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")
    confirm = payload.get("confirm_password", "")

    if password != confirm:
        return jsonify({"ok": False, "error": "Passwords do not match."}), 400
    try:
        write_auth(username, password)
        return jsonify({
            "ok": True,
            "username": username.strip(),
            "restart_required": True,
        })
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"Could not update authentication: {e}"}), 500


@app.post("/api/system/restart-configurator")
@require_auth
def system_restart_configurator():
    try:
        restart_configurator_service()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Could not restart configurator service: {e}"}), 500
