# OMO Slim Preset Switcher

[![CI](https://github.com/Aveer/omo-slim-preset-switcher/actions/workflows/test.yml/badge.svg)](https://github.com/Aveer/omo-slim-preset-switcher/actions/workflows/test.yml)

A small local desktop utility for managing [oh-my-opencode-slim](https://github.com/alvinunreal/oh-my-opencode-slim) presets across multiple projects.

## Why

OMO Slim already has preset management inside its TUI. This utility solves a different problem: managing project-local preset selection across many repositories from one lightweight desktop window, including environments where OpenCode Desktop does not expose the TUI preset manager.

## Features

- Multiple configurable project-root folders.
- Configurable OpenCode config directory.
- Automatic discovery of project-local `.opencode/oh-my-opencode-slim.jsonc` and `.json`.
- Correct `.jsonc` precedence when both files exist.
- Reads available presets and the current global preset from the main OMO Slim config.
- Explicit global preset control for projects that inherit the user-level setting.
- Per-project overrides with an **Inherit global** action that removes only the local `preset` key.
- Shows both the project override and effective preset for every discovered project.
- Change one project, bulk-set project overrides, or bulk-return visible projects to **Inherit global**.
- Preserves JSONC comments and formatting when changing only the top-level `preset` value.
- Atomic config and app-settings writes use securely created unique sibling temporary files plus `os.replace`.
- Path deduplication follows the host platform's case-sensitivity rules.
- No third-party runtime dependencies; the UI uses Python's standard-library Tkinter.
- No machine-specific paths are stored in the repository.

## Requirements

- Python 3.11+
- Tkinter 8.6+ (included with the standard Windows Python installer)

CI currently validates Python 3.11 and 3.14 on both Windows and Ubuntu.

## Run

### From a checkout on Windows

Double-click `run.cmd`. It adds the local `src` directory to `PYTHONPATH` and launches the GUI without leaving a persistent console window.

You can also run the module directly:

```bash
python -m omo_slim_preset_switcher
```

### Install as a Python application

From a checkout:

```bash
python -m pip install .
```

The installed GUI entry point is:

```bash
omo-slim-presets
```

On Windows this is installed as a GUI script, so launching it does not require a console window.

For development, an editable install still works:

```bash
python -m pip install -e .
```

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

The application treats **Global** and **Project** selection as separate layers.

- **Global preset** edits only the top-level `preset` in the configured main OMO Slim config. Projects without a local override inherit this value.
- **Project preset** edits only the top-level `preset` in that project's existing `.opencode/oh-my-opencode-slim.jsonc` or `.json`.
- **Inherit global** removes only the project's top-level `preset` key and preserves the rest of the project config, including JSONC comments.
- **Bulk apply** is deliberately project-local: it can set one override across visible projects or remove their overrides via **Inherit global**, but it never changes the global preset.

Preset definitions are read from the configured main OMO Slim config. The tool does not copy preset definitions into project files.

For the displayed **Effective** preset, the app follows OMO Slim precedence:

1. `OH_MY_OPENCODE_SLIM_PRESET` when set;
2. project-local `preset`;
3. global/user `preset`.

Top-level preset strings using OMO's `{env:NAME}` syntax are interpolated for display. When `OH_MY_OPENCODE_SLIM_PRESET` is active, Project/Global config edits are still allowed but the UI marks that the runtime effective preset remains masked by the environment override.

If both project `.jsonc` and `.json` exist, JSONC wins. The scanner intentionally lists projects that already contain an OMO Slim project config; it does not crawl arbitrary repositories and create configs implicitly.

## Tests

```bash
python -m unittest discover -s tests -v
```

The GitHub Actions matrix also verifies a normal installed package, the GUI entry point, and Tkinter import on Windows.

## Releases

Tagged releases build both a wheel and source distribution and publish them to GitHub Releases. Runtime dependencies remain empty.

## Scope

This project is intentionally a standalone workspace/fleet-style preset manager. It is not an alternative implementation of OMO Slim's preset domain and does not modify OpenCode itself.
