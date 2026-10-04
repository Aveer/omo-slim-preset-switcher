from __future__ import annotations

import json
import os
import tempfile
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


def path_key(value: str | Path) -> str:
    """Return a path identity key using the current platform's case rules."""
    return os.path.normcase(os.path.normpath(str(normalize_path(value))))


def _normalized_roots(raw_roots: object) -> list[str]:
    roots: list[str] = []
    seen: set[str] = set()

    if not isinstance(raw_roots, list):
        return roots

    for raw in raw_roots:
        value = str(raw).strip()
        if not value:
            continue

        normalized = str(normalize_path(value))
        key = path_key(normalized)
        if key not in seen:
            seen.add(key)
            roots.append(normalized)

    return roots


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

    roots = _normalized_roots(data.get("project_roots", []))
    config_raw = data.get("opencode_config_dir", defaults["opencode_config_dir"])
    config_dir = str(normalize_path(str(config_raw)))

    return {
        "project_roots": roots,
        "opencode_config_dir": config_dir,
    }


def save_settings(settings: dict[str, object]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    roots = _normalized_roots(settings.get("project_roots", []))
    config_dir = str(
        normalize_path(
            str(settings.get("opencode_config_dir", default_opencode_config_dir()))
        )
    )

    payload = {
        "project_roots": roots,
        "opencode_config_dir": config_dir,
    }

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
