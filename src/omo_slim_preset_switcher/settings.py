from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR_NAME = "OmoSlimPresetSwitcher"


def settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_DIR_NAME / "settings.json"


def default_opencode_config_dir() -> Path:
    explicit = os.environ.get("OPENCODE_CONFIG_DIR", "").strip()
    if explicit:
        return Path(os.path.expandvars(explicit)).expanduser()

    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return Path(os.path.expandvars(xdg)).expanduser() / "opencode"

    return Path.home() / ".config" / "opencode"


def normalize_path(value: str | Path) -> Path:
    return Path(os.path.expandvars(str(value).strip())).expanduser()


def default_settings() -> dict[str, object]:
    return {
        "project_roots": [],
        "opencode_config_dir": str(default_opencode_config_dir()),
    }


def load_settings() -> dict[str, object]:
    defaults = default_settings()
    path = settings_path()
    if not path.is_file():
        return defaults

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return defaults

    if not isinstance(data, dict):
        return defaults

    roots_raw = data.get("project_roots", [])
    roots: list[str] = []
    seen: set[str] = set()
    if isinstance(roots_raw, list):
        for raw in roots_raw:
            value = str(raw).strip()
            if not value:
                continue
            normalized = str(normalize_path(value))
            key = normalized.casefold()
            if key not in seen:
                seen.add(key)
                roots.append(normalized)

    config_raw = data.get("opencode_config_dir", defaults["opencode_config_dir"])
    config_dir = str(normalize_path(str(config_raw)))

    return {
        "project_roots": roots,
        "opencode_config_dir": config_dir,
    }


def save_settings(settings: dict[str, object]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    roots_raw = settings.get("project_roots", [])
    roots: list[str] = []
    seen: set[str] = set()
    if isinstance(roots_raw, list):
        for raw in roots_raw:
            value = str(raw).strip()
            if not value:
                continue
            normalized = str(normalize_path(value))
            key = normalized.casefold()
            if key not in seen:
                seen.add(key)
                roots.append(normalized)

    config_dir = str(
        normalize_path(
            str(settings.get("opencode_config_dir", default_opencode_config_dir()))
        )
    )

    payload = {
        "project_roots": roots,
        "opencode_config_dir": config_dir,
    }

    tmp = path.with_name(f"{path.name}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
