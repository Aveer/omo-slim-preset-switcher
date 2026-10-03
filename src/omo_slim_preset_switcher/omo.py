from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import jsonc

OMO_JSONC = "oh-my-opencode-slim.jsonc"
OMO_JSON = "oh-my-opencode-slim.json"
PROJECT_CONFIG_DIR = ".opencode"

PRUNE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    PROJECT_CONFIG_DIR,
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".cache",
}


@dataclass(slots=True)
class ProjectConfig:
    name: str
    project_dir: Path
    source_root: Path
    config_path: Path
    preset: str
    error: str = ""


def resolve_config(config_dir: Path) -> Path | None:
    jsonc_path = config_dir / OMO_JSONC
    json_path = config_dir / OMO_JSON
    if jsonc_path.is_file():
        return jsonc_path
    if json_path.is_file():
        return json_path
    return None


def read_text(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig"), has_bom


def read_config(path: Path) -> dict[str, object]:
    text, _ = read_text(path)
    if path.suffix.casefold() == ".jsonc":
        return jsonc.loads(text)

    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Configuration root must be a JSON object.")
    return value


def available_presets(config_path: Path) -> list[str]:
    config = read_config(config_path)
    presets = config.get("presets", {})
    if not isinstance(presets, dict):
        raise ValueError(f'"presets" in {config_path} must be an object.')
    return list(presets.keys())


def selected_preset(config_path: Path) -> str:
    value = read_config(config_path).get("preset", "")
    return str(value) if isinstance(value, str) else ""


def project_config_path(project_dir: Path) -> Path | None:
    return resolve_config(project_dir / PROJECT_CONFIG_DIR)


def scan_projects(roots: Iterable[Path]) -> list[ProjectConfig]:
    found: dict[str, ProjectConfig] = {}

    for source_root in roots:
        root = source_root.expanduser()
        if not root.is_dir():
            continue

        for dirpath, dirnames, _filenames in os.walk(root):
            current = Path(dirpath)
            config_path = project_config_path(current)

            if config_path is not None:
                try:
                    config = read_config(config_path)
                    preset = str(config.get("preset", "") or "")
                    error = ""
                except Exception as exc:
                    preset = ""
                    error = str(exc)

                try:
                    key = str(config_path.resolve()).casefold()
                except OSError:
                    key = str(config_path.absolute()).casefold()

                found[key] = ProjectConfig(
                    name=current.name or str(current),
                    project_dir=current,
                    source_root=root,
                    config_path=config_path,
                    preset=preset,
                    error=error,
                )

            dirnames[:] = [name for name in dirnames if name not in PRUNE_DIRS]

    return sorted(found.values(), key=lambda item: str(item.project_dir).casefold())


def _atomic_write_text(config_path: Path, text: str, has_bom: bool) -> None:
    prefix = b"\xef\xbb\xbf" if has_bom else b""
    payload = prefix + text.encode("utf-8")
    tmp = config_path.with_name(f"{config_path.name}.tmp")

    try:
        with tmp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, config_path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def write_preset(config_path: Path, preset: str) -> None:
    original, has_bom = read_text(config_path)
    updated = jsonc.set_top_level_string(original, "preset", preset)

    parsed = (
        jsonc.loads(updated)
        if config_path.suffix.casefold() == ".jsonc"
        else json.loads(updated)
    )
    if not isinstance(parsed, dict) or parsed.get("preset") != preset:
        raise ValueError("Preset verification failed after update.")

    _atomic_write_text(config_path, updated, has_bom)


def clear_preset(config_path: Path) -> None:
    original, has_bom = read_text(config_path)
    updated = jsonc.remove_top_level_string(original, "preset")

    parsed = (
        jsonc.loads(updated)
        if config_path.suffix.casefold() == ".jsonc"
        else json.loads(updated)
    )
    if not isinstance(parsed, dict) or "preset" in parsed:
        raise ValueError("Preset removal verification failed.")

    _atomic_write_text(config_path, updated, has_bom)


def write_project_preset(config_path: Path, preset: str) -> None:
    write_preset(config_path, preset)


def clear_project_preset(config_path: Path) -> None:
    clear_preset(config_path)
