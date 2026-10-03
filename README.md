# OMO Slim Preset Switcher

A small local desktop utility for managing [oh-my-opencode-slim](https://github.com/alvinunreal/oh-my-opencode-slim) presets across multiple projects.

## Why

OMO Slim already has preset management inside its TUI. This utility solves a different problem: managing project-local preset selection across many repositories from one lightweight desktop window, including environments where OpenCode Desktop does not expose the TUI preset manager.

## Features

- Multiple configurable project-root folders.
- Configurable OpenCode config directory.
- Automatic discovery of project-local `.opencode/oh-my-opencode-slim.jsonc` and `.json`.
- Correct `.jsonc` precedence when both files exist.
- Reads available presets from the main OMO Slim config.
- Shows the active preset for every discovered project.
- Change one project or all currently filtered projects.
- Preserves JSONC comments and formatting when changing only the top-level `preset` value.
- Atomic writes using a sibling temporary file and `os.replace`.
- No third-party runtime dependencies; the UI uses Python's standard-library Tkinter.
- No machine-specific paths are stored in the repository.

## Requirements

- Python 3.11+
- Tkinter 8.6+ (included with the standard Windows Python installer)

## Run

```bash
python -m omo_slim_preset_switcher
```

On Windows you can also double-click `run.cmd`.

## First run

Open **Settings** and add one or more folders that contain your projects.

The OpenCode config directory is discovered from standard configuration locations:

1. `OPENCODE_CONFIG_DIR`
2. `XDG_CONFIG_HOME/opencode`
3. `~/.config/opencode`

You can override it from Settings.

Project roots intentionally default to an empty list. The application never assumes a private or machine-specific projects directory.

## App settings

User settings are stored outside the repository:

- Windows: `%APPDATA%/OmoSlimPresetSwitcher/settings.json`
- Linux/macOS: `$XDG_CONFIG_HOME/OmoSlimPresetSwitcher/settings.json` or `~/.config/OmoSlimPresetSwitcher/settings.json`

## Preset semantics

For each discovered project the application edits only the top-level project-local `preset` field. It does not copy preset definitions into projects.

Preset definitions are read from the configured main OMO Slim config.

If a project already has a `.jsonc` config, that file is used. Otherwise the `.json` config is used.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Scope

This project is intentionally a standalone workspace/fleet-style preset manager. It is not an alternative implementation of OMO Slim's preset domain and does not modify OpenCode itself.
