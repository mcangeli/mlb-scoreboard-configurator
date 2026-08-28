import hmac
import os
from functools import wraps
from flask import Flask, Response, jsonify, render_template, request
from waitress import serve
from . import network, service
from .settings import load_settings, save_settings, web_username, web_password
from .storage import (
    named_path, read_json, write_json, coordinate_files, config_schema,
    validate, list_backups, restore_backup
)

app = Flask(__name__)

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
    return render_template("index.html")

@app.get("/api/bootstrap")
def bootstrap():
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

def main():
    host = os.environ.get("CONFIGURATOR_HOST", "0.0.0.0")
    port = int(os.environ.get("CONFIGURATOR_PORT", "8080"))
    serve(app, host=host, port=port, threads=6)
