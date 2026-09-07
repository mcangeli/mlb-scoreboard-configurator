from __future__ import annotations
import importlib.metadata
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

ENTRYPOINT_GROUP = "bullpen.mlbled.plugin"
_GITHUB_HOSTS = {"github.com", "www.github.com"}
CONFIGURATOR_DISTRIBUTION = "mlb-scoreboard-configurator"
CONFIGURATOR_REPOSITORY = "https://github.com/mcangeli/mlb-scoreboard-configurator.git"

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


def setup_executable() -> Path:
    setup = venv_bin() / "mlb-scoreboard-configurator-setup"
    if not setup.is_file():
        raise FileNotFoundError(f"Configurator setup command was not found at {setup}.")
    return setup


def _canonical_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", (value or "").strip().lower())

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
            "github_url": _direct_url_for_distribution(dist_name),
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


def update_plugin(distribution: str = "", github_url: str = "") -> dict:
    """Update an installed plugin.

    The configurator itself is special: reinstall it from GitHub, rerun its
    setup command without restarting the currently-serving process, then let
    the browser request the service restart after this API response completes.

    Other plugins use the traditional installed-distribution pip upgrade path.
    """
    distribution = (distribution or "").strip()
    github_url = (github_url or "").strip()
    canonical = _canonical_distribution(distribution)

    if canonical == CONFIGURATOR_DISTRIBUTION:
        repo = normalize_github_url(github_url or CONFIGURATOR_REPOSITORY)
        proc = subprocess.run(
            [
                str(pip_executable()), "install",
                "--upgrade", "--force-reinstall", f"git+{repo}",
            ],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        install_output = "\n".join(
            x for x in (proc.stdout.strip(), proc.stderr.strip()) if x
        ).strip()
        if proc.returncode != 0:
            raise RuntimeError(
                install_output[-12000:]
                if install_output
                else f"pip exited with status {proc.returncode}."
            )

        setup = subprocess.run(
            [
                str(setup_executable()),
                "--root", str(scoreboard_root()),
                "--venv-bin", str(venv_bin()),
                "--no-enable",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        setup_output = "\n".join(
            x for x in (setup.stdout.strip(), setup.stderr.strip()) if x
        ).strip()
        if setup.returncode != 0:
            combined = "\n\n".join(x for x in (install_output, setup_output) if x)
            raise RuntimeError(
                combined[-12000:]
                if combined
                else f"Configurator setup exited with status {setup.returncode}."
            )

        combined = "\n\n".join(
            x for x in (
                install_output,
                "Configurator setup:\n" + setup_output if setup_output else "",
            ) if x
        )
        return {
            "distribution": distribution,
            "repository": repo,
            "output": combined[-12000:],
            "self_update": True,
            "restart_required": True,
        }

    distribution = _safe_distribution_name(distribution)
    proc = subprocess.run(
        [str(pip_executable()), "install", "--upgrade", distribution],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    output = "\n".join(
        x for x in (proc.stdout.strip(), proc.stderr.strip()) if x
    ).strip()
    if proc.returncode != 0:
        raise RuntimeError(
            output[-12000:]
            if output
            else f"pip exited with status {proc.returncode}."
        )
    return {
        "distribution": distribution,
        "repository": "",
        "output": output[-12000:],
        "self_update": False,
        "restart_required": False,
    }


def uninstall_plugin(distribution: str) -> dict:
    distribution = _safe_distribution_name(distribution)
    proc = subprocess.run([str(pip_executable()), "uninstall", "-y", distribution], capture_output=True, text=True, timeout=600, check=False)
    output = "\n".join(x for x in (proc.stdout.strip(), proc.stderr.strip()) if x).strip()
    if proc.returncode != 0:
        raise RuntimeError(output[-12000:] if output else f"pip exited with status {proc.returncode}.")
    return {"distribution": distribution, "output": output[-12000:]}



def repository_file() -> Path:
    """Return the editable plugin repository path.

    Prefer a state-file copy so package upgrades do not overwrite user edits.
    Seed it from the packaged catalog on first use.
    """
    state_path = scoreboard_root() / ".configurator" / "plugin_repository.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    if not state_path.exists():
        packaged = Path(__file__).with_name("plugin_repository.json")
        if packaged.exists():
            state_path.write_text(packaged.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            state_path.write_text('{"plugins": []}\n', encoding="utf-8")
    return state_path


def _validate_repository_entry(entry: dict) -> dict:
    if not isinstance(entry, dict):
        raise ValueError("Repository entry must be an object.")

    name = str(entry.get("name") or "").strip()
    description = str(entry.get("description") or "").strip()
    github_url = str(entry.get("github_url") or "").strip()
    distribution = str(entry.get("distribution") or "").strip()
    entry_point = str(entry.get("entry_point") or "").strip()

    if not name:
        raise ValueError("Plugin name is required.")
    if not github_url:
        raise ValueError("GitHub repository URL is required.")

    github_url = normalize_github_url(github_url)

    if distribution:
        _safe_distribution_name(distribution)

    if entry_point and not re.fullmatch(r"[A-Za-z0-9_.-]+", entry_point):
        raise ValueError("Bullpen entry-point name contains unsupported characters.")

    return {
        "name": name,
        "description": description,
        "github_url": github_url,
        "distribution": distribution,
        "entry_point": entry_point,
    }


def save_repository_plugins(plugins: list[dict]) -> list[dict]:
    if not isinstance(plugins, list):
        raise ValueError("Repository must be a list of plugins.")

    cleaned = [_validate_repository_entry(p) for p in plugins]

    seen = set()
    for p in cleaned:
        key = (
            p["github_url"].lower(),
            p["distribution"].lower(),
            p["entry_point"].lower(),
        )
        if key in seen:
            raise ValueError(f'Duplicate repository entry: {p["name"]}')
        seen.add(key)

    path = repository_file()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"plugins": cleaned}, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return cleaned


def repository_plugins() -> list[dict]:
    path = repository_file()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        data = __import__("json").load(fh)
    plugins = data.get("plugins", [])
    return [p for p in plugins if isinstance(p, dict)]

def _direct_url_for_distribution(dist_name: str) -> str:
    if not dist_name:
        return ""
    try:
        dist = importlib.metadata.distribution(dist_name)
        raw = dist.read_text("direct_url.json")
        if not raw:
            return ""
        data = __import__("json").loads(raw)
        url = str(data.get("url") or "")
        vcs = data.get("vcs_info") or {}
        if vcs.get("vcs") == "git" and "github.com" in url:
            return url[4:] if url.startswith("git+") else url
    except Exception:
        pass
    return ""
