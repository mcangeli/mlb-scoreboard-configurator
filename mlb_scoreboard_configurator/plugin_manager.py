from __future__ import annotations
import importlib.metadata
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

ENTRYPOINT_GROUP = "bullpen.mlbled.plugin"
_GITHUB_HOSTS = {"github.com", "www.github.com"}

def scoreboard_root() -> Path:
    return Path(os.environ.get("MLB_SCOREBOARD_ROOT", "/home/pi/mlb-led-scoreboard")).expanduser().resolve()

def venv_bin() -> Path:
    configured = os.environ.get("MLB_SCOREBOARD_VENV_BIN")
    return Path(configured).expanduser().resolve() if configured else scoreboard_root() / "venv" / "bin"

def pip_executable() -> Path:
    pip = venv_bin() / "pip"
    if not pip.is_file():
        raise FileNotFoundError(f"Scoreboard pip was not found at {pip}.")
    return pip

def normalize_github_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Enter a GitHub repository URL.")
    if value.startswith("git+"):
        value = value[4:]
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _GITHUB_HOSTS:
        raise ValueError("Only HTTPS GitHub repository URLs are supported.")
    if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        raise ValueError("GitHub URLs cannot include credentials, ports, query strings, or fragments.")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) != 2:
        raise ValueError("The URL must point directly to a GitHub repository.")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    valid = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not valid.fullmatch(owner) or not valid.fullmatch(repo):
        raise ValueError("Invalid GitHub owner or repository name.")
    return f"https://github.com/{owner}/{repo}.git"

def install_plugin(github_url: str) -> dict:
    repo = normalize_github_url(github_url)
    proc = subprocess.run(
        [str(pip_executable()), "install", "--upgrade", f"git+{repo}"],
        capture_output=True, text=True, timeout=600, check=False
    )
    output = "\n".join(x for x in (proc.stdout.strip(), proc.stderr.strip()) if x).strip()
    if proc.returncode != 0:
        raise RuntimeError(output[-12000:] if output else f"pip exited with status {proc.returncode}.")
    return {"repository": repo, "output": output[-12000:]}

def installed_plugins() -> list[dict]:
    eps = importlib.metadata.entry_points()
    try:
        entries = list(eps.select(group=ENTRYPOINT_GROUP))
    except AttributeError:
        entries = list(eps.get(ENTRYPOINT_GROUP, []))
    plugins = []
    for ep in entries:
        dist_name, version = "", ""
        try:
            if ep.dist is not None:
                dist_name = ep.dist.metadata.get("Name", ep.dist.name or "")
                version = ep.dist.version or ""
        except Exception:
            pass
        plugins.append({
            "name": ep.name,
            "entry_point": ep.value,
            "distribution": dist_name,
            "version": version,
        })
    plugins.sort(key=lambda x: ((x["name"] or "").lower(), (x["distribution"] or "").lower()))
    return plugins


def _safe_distribution_name(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Plugin package name is missing.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError("Plugin package name contains unsupported characters.")
    return value


def update_plugin(distribution: str) -> dict:
    distribution = _safe_distribution_name(distribution)
    proc = subprocess.run([str(pip_executable()), "install", "--upgrade", distribution], capture_output=True, text=True, timeout=600, check=False)
    output = "\n".join(x for x in (proc.stdout.strip(), proc.stderr.strip()) if x).strip()
    if proc.returncode != 0:
        raise RuntimeError(output[-12000:] if output else f"pip exited with status {proc.returncode}.")
    return {"distribution": distribution, "output": output[-12000:]}


def uninstall_plugin(distribution: str) -> dict:
    distribution = _safe_distribution_name(distribution)
    proc = subprocess.run([str(pip_executable()), "uninstall", "-y", distribution], capture_output=True, text=True, timeout=600, check=False)
    output = "\n".join(x for x in (proc.stdout.strip(), proc.stderr.strip()) if x).strip()
    if proc.returncode != 0:
        raise RuntimeError(output[-12000:] if output else f"pip exited with status {proc.returncode}.")
    return {"distribution": distribution, "output": output[-12000:]}
