import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from jsonschema import Draft202012Validator
from .settings import scoreboard_root, state_dir

COORD_RE = re.compile(r"^[A-Za-z0-9_.-]+\.json$")

def named_path(name: str) -> Path:
    root = scoreboard_root()
    fixed = {
        "config": root / "config.json",
        "teams": root / "colors" / "teams.json",
        "scoreboard": root / "colors" / "scoreboard.json",
    }
    if name in fixed:
        return fixed[name]
    if name.startswith("coordinates/"):
        filename = name.split("/", 1)[1]
        if not COORD_RE.match(filename):
            raise ValueError("Invalid coordinate filename.")
        p = (root / "coordinates" / filename).resolve()
        if p.parent != (root / "coordinates").resolve():
            raise ValueError("Invalid coordinate path.")
        return p
    raise ValueError("Unknown configuration file.")

def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def coordinate_files():
    d = scoreboard_root() / "coordinates"
    if not d.exists():
        return []
    return sorted(p.name for p in d.glob("*.json") if p.is_file())

def config_schema():
    p = scoreboard_root() / "schemas" / "config.schema.json"
    return read_json(p) if p.exists() else None

def validate(name: str, data):
    errors = []
    if name == "config":
        schema = config_schema()
        if schema:
            validator = Draft202012Validator(schema)
            for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
                loc = ".".join(str(x) for x in err.absolute_path) or "(root)"
                errors.append({"path": loc, "message": err.message})
    return errors

def backups_dir():
    d = state_dir() / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d

def backup(path: Path):
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    rel = path.relative_to(scoreboard_root())
    safe = "__".join(rel.parts)
    target = backups_dir() / f"{safe}.{stamp}.bak"
    shutil.copy2(path, target)
    return target

def write_json(name: str, data):
    errors = validate(name, data)
    if errors:
        return False, errors
    path = named_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return True, []

def list_backups(name: str):
    target = named_path(name)
    rel = target.relative_to(scoreboard_root())
    prefix = "__".join(rel.parts) + "."
    out = []
    for p in sorted(backups_dir().glob(prefix + "*.bak"), reverse=True):
        out.append({
            "id": p.name,
            "size": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return out[:50]

def restore_backup(name: str, backup_id: str):
    if "/" in backup_id or "\\" in backup_id:
        raise ValueError("Invalid backup.")
    src = backups_dir() / backup_id
    if not src.exists():
        raise FileNotFoundError("Backup not found.")
    data = read_json(src)
    return write_json(name, data)



def ensure_color_files() -> list[str]:
    """Create missing live color files from their example templates.

    Existing live files are never overwritten. Returns a list of relative
    paths that were created.
    """
    created: list[str] = []
    colors_dir = scoreboard_root() / "colors"

    mappings = (
        ("teams.json", "teams.example.json"),
        ("scoreboard.json", "scoreboard.example.json"),
    )

    for live_name, example_name in mappings:
        live_path = colors_dir / live_name
        example_path = colors_dir / example_name

        if live_path.exists():
            continue

        if not example_path.exists():
            raise FileNotFoundError(
                f"Cannot create colors/{live_name}: colors/{example_name} does not exist."
            )

        # Validate the example before copying so we never create an invalid
        # live configuration file from malformed JSON.
        with example_path.open("r", encoding="utf-8") as fh:
            json.load(fh)

        live_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = live_path.with_suffix(live_path.suffix + ".tmp")
        shutil.copyfile(example_path, tmp_path)
        os.replace(tmp_path, live_path)
        created.append(f"colors/{live_name}")

    return created


def _plugin_name_variants(values: list[str]) -> set[str]:
    variants: set[str] = set()
    for value in values:
        name = str(value or "").strip().lower()
        if not name:
            continue
        variants.add(name)
        variants.add(name.replace("-", "_"))
        variants.add(name.replace("_", "-"))
    return variants


def remove_plugin_config_sections(candidates: list[str]) -> dict:
    """Remove matching plugin config and screen entries from config.json.

    The config file is written only when something changes, so the normal
    write_json backup behavior protects the previous configuration.
    """
    path = named_path("config")
    data = read_json(path)
    wanted = _plugin_name_variants(candidates)
    removed_plugins: list[str] = []
    removed_screens: list[dict] = []

    plugins = data.get("plugins")
    if isinstance(plugins, dict):
        for key in list(plugins.keys()):
            key_variants = _plugin_name_variants([key])
            if wanted.intersection(key_variants):
                removed_plugins.append(key)
                del plugins[key]

    rotation = data.get("rotation")
    screens = rotation.get("screens") if isinstance(rotation, dict) else None
    if isinstance(screens, list):
        kept = []
        for screen in screens:
            if not isinstance(screen, dict):
                kept.append(screen)
                continue

            kind = screen.get("kind")
            kind_variants = _plugin_name_variants([kind]) if kind is not None else set()
            if wanted.intersection(kind_variants):
                removed_screens.append(screen)
            else:
                kept.append(screen)

        if removed_screens:
            rotation["screens"] = kept

    if removed_plugins or removed_screens:
        write_json("config", data)

    return {
        "plugin_sections": removed_plugins,
        "screens": removed_screens,
    }
