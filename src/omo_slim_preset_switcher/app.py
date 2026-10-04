from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .omo import (
    ProjectConfig,
    available_presets,
    clear_project_preset,
    environment_preset,
    resolve_config,
    scan_projects,
    selected_preset,
    write_preset,
    write_project_preset,
)
from .settings import load_settings, normalize_path, save_settings, settings_path

INHERIT_GLOBAL = "Inherit global"


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, settings: dict[str, object]) -> None:
        super().__init__(parent)
        self.result: dict[str, object] | None = None
        self.title("Settings")
        self.geometry("760x500")
        self.minsize(640, 420)
        self.transient(parent)
        self.grab_set()

        self.config_dir_var = tk.StringVar(
            value=str(settings.get("opencode_config_dir", ""))
        )

        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Project folders",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Each folder is scanned recursively for "
                ".opencode/oh-my-opencode-slim.jsonc or .json."
            ),
        ).pack(anchor="w", pady=(2, 8))

        roots_row = ttk.Frame(outer)
        roots_row.pack(fill="both", expand=True)

        self.roots_list = tk.Listbox(
            roots_row,
            activestyle="dotbox",
            exportselection=False,
        )
        self.roots_list.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            roots_row,
            orient="vertical",
            command=self.roots_list.yview,
        )
        scrollbar.pack(side="left", fill="y")
        self.roots_list.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(roots_row)
        buttons.pack(side="left", fill="y", padx=(10, 0))
        ttk.Button(buttons, text="Add…", command=self.add_root).pack(fill="x")
        ttk.Button(buttons, text="Remove", command=self.remove_root).pack(
            fill="x", pady=(6, 0)
        )

        roots = settings.get("project_roots", [])
        if isinstance(roots, list):
            for root in roots:
                self.roots_list.insert("end", str(root))

        ttk.Separator(outer).pack(fill="x", pady=14)

        ttk.Label(
            outer,
            text="OpenCode config folder",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Folder containing the main oh-my-opencode-slim.jsonc/.json. "
                "JSONC wins when both exist."
            ),
        ).pack(anchor="w", pady=(2, 8))

        config_row = ttk.Frame(outer)
        config_row.pack(fill="x")
        ttk.Entry(
            config_row,
            textvariable=self.config_dir_var,
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            config_row,
            text="Browse…",
            command=self.browse_config_dir,
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            outer,
            text=f"Settings are stored outside the repo: {settings_path()}",
            foreground="#666666",
        ).pack(anchor="w", pady=(8, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(
            actions,
            text="Save & rescan",
            command=self.save,
        ).pack(side="right", padx=(0, 8))

    def add_root(self) -> None:
        selected = filedialog.askdirectory(
            parent=self,
            title="Select project root folder",
        )
        if not selected:
            return

        normalized = str(normalize_path(selected))
        existing = {
            self.roots_list.get(index).casefold()
            for index in range(self.roots_list.size())
        }
        if normalized.casefold() not in existing:
            self.roots_list.insert("end", normalized)

    def remove_root(self) -> None:
        selection = self.roots_list.curselection()
        if selection:
            self.roots_list.delete(selection[0])

    def browse_config_dir(self) -> None:
        initial = self.config_dir_var.get().strip() or None
        selected = filedialog.askdirectory(
            parent=self,
            title="Select OpenCode config folder",
            initialdir=initial,
        )
        if selected:
            self.config_dir_var.set(str(normalize_path(selected)))

    def save(self) -> None:
        roots: list[str] = []
        seen: set[str] = set()
        for index in range(self.roots_list.size()):
            value = str(normalize_path(self.roots_list.get(index)))
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                roots.append(value)

        config_dir = self.config_dir_var.get().strip()
        if not config_dir:
            messagebox.showerror(
                "Invalid settings",
                "OpenCode config folder cannot be empty.",
                parent=self,
            )
            return

        self.result = {
            "project_roots": roots,
            "opencode_config_dir": str(normalize_path(config_dir)),
        }
        self.destroy()


class PresetSwitcher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OMO Slim Preset Switcher")
        self.geometry("1120x720")
        self.minsize(840, 480)

        self.settings_data = load_settings()
        self.presets: list[str] = []
        self.projects: list[ProjectConfig] = []
        self.main_config_path: Path | None = None
        self.env_preset = ""

        self.filter_var = tk.StringVar()
        self.bulk_var = tk.StringVar()
        self.global_preset_var = tk.StringVar()
        self.paths_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._setup_style()
        self._build_ui()
        self.filter_var.trace_add("write", lambda *_: self.render_projects())
        self.refresh_all()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Project.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Subtle.TLabel", foreground="#666666")
        style.configure("Error.TLabel", foreground="#b42318")

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="OMO Slim Preset Switcher",
            style="Title.TLabel",
        ).pack(side="left")
        ttk.Button(
            header,
            text="Settings",
            command=self.open_settings,
        ).pack(side="right")
        ttk.Button(
            header,
            text="Refresh",
            command=self.refresh_all,
        ).pack(side="right", padx=(0, 6))

        ttk.Label(
            outer,
            textvariable=self.paths_var,
            style="Subtle.TLabel",
            justify="left",
        ).pack(fill="x", anchor="w", pady=(8, 10))

        global_controls = ttk.Frame(outer)
        global_controls.pack(fill="x", pady=(0, 10))
        ttk.Label(
            global_controls,
            text="Global preset:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")
        self.global_combo = ttk.Combobox(
            global_controls,
            textvariable=self.global_preset_var,
            state="readonly",
            width=28,
        )
        self.global_combo.pack(side="left", padx=(6, 6))
        ttk.Button(
            global_controls,
            text="Apply global",
            command=self.apply_global_preset,
        ).pack(side="left")
        ttk.Label(
            global_controls,
            text="Used by projects with no local preset override.",
            style="Subtle.TLabel",
        ).pack(side="left", padx=(10, 0))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 10))

        ttk.Label(controls, text="Filter:").pack(side="left")
        ttk.Entry(
            controls,
            textvariable=self.filter_var,
            width=30,
        ).pack(side="left", padx=(6, 18))

        ttk.Label(controls, text="Set project override for visible:").pack(side="left")
        self.bulk_combo = ttk.Combobox(
            controls,
            textvariable=self.bulk_var,
            state="readonly",
            width=28,
        )
        self.bulk_combo.pack(side="left", padx=(6, 6))
        ttk.Button(
            controls,
            text="Apply",
            command=self.apply_bulk,
        ).pack(side="left")

        self.summary_label = ttk.Label(
            controls,
            text="",
            style="Subtle.TLabel",
        )
        self.summary_label.pack(side="right")

        ttk.Separator(outer).pack(fill="x", pady=(0, 6))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(
            body,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.rows = ttk.Frame(self.canvas)
        self.rows_window = self.canvas.create_window(
            (0, 0),
            window=self.rows,
            anchor="nw",
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.rows.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(
                self.rows_window, width=event.width
            ),
        )
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(
            outer,
            textvariable=self.status_var,
            style="Subtle.TLabel",
        ).pack(fill="x", anchor="w", pady=(8, 0))

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def roots(self) -> list[Path]:
        raw = self.settings_data.get("project_roots", [])
        if not isinstance(raw, list):
            return []
        return [normalize_path(str(root)) for root in raw if str(root).strip()]

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.settings_data)
        self.wait_window(dialog)
        if dialog.result is None:
            return

        try:
            save_settings(dialog.result)
        except Exception as exc:
            messagebox.showerror("Cannot save settings", str(exc), parent=self)
            return

        self.settings_data = dialog.result
        self.refresh_all()

    def refresh_all(self) -> None:
        config_dir = normalize_path(
            str(self.settings_data.get("opencode_config_dir", ""))
        )
        self.main_config_path = resolve_config(config_dir)

        self.presets = []
        global_preset = ""
        self.env_preset = environment_preset()
        if self.main_config_path is not None:
            try:
                self.presets = available_presets(self.main_config_path)
                global_preset = selected_preset(self.main_config_path)
            except Exception as exc:
                messagebox.showerror(
                    "Cannot load presets",
                    f"{exc}\n\nConfig:\n{self.main_config_path}",
                    parent=self,
                )

        self.global_combo["values"] = self.presets
        if global_preset:
            self.global_preset_var.set(global_preset)
        elif self.presets and self.global_preset_var.get() not in self.presets:
            self.global_preset_var.set(self.presets[0])
        elif not self.presets:
            self.global_preset_var.set("")

        bulk_options = [INHERIT_GLOBAL, *self.presets]
        self.bulk_combo["values"] = bulk_options
        if self.presets:
            if self.bulk_var.get() not in bulk_options:
                self.bulk_var.set(self.presets[0])
        else:
            self.bulk_var.set(INHERIT_GLOBAL)

        roots = self.roots()
        self.projects = scan_projects(roots)
        self.render_projects()

        roots_label = "; ".join(str(root) for root in roots) or "(none configured)"
        config_label = (
            str(self.main_config_path)
            if self.main_config_path is not None
            else f"(not found in {config_dir})"
        )
        self.paths_var.set(
            f"Project roots: {roots_label}\nMain OMO config: {config_label}"
        )

        missing = sum(1 for root in roots if not root.is_dir())
        status = [
            f"{len(self.projects)} project(s)",
            f"{len(self.presets)} preset(s)",
        ]
        if global_preset:
            status.append(f"global: {global_preset}")
        if self.env_preset:
            status.append(f"env override: {self.env_preset}")
        if missing:
            status.append(f"{missing} missing root(s)")
        if self.main_config_path is None:
            status.append("main OMO config not found")
        if not roots:
            status.append("add project folders in Settings")
        self.status_var.set(" · ".join(status))

    def visible_projects(self) -> list[ProjectConfig]:
        needle = self.filter_var.get().strip().casefold()
        if not needle:
            return self.projects
        return [
            project
            for project in self.projects
            if needle in project.name.casefold()
            or needle in str(project.project_dir).casefold()
            or needle in project.preset.casefold()
        ]

    def render_projects(self) -> None:
        for child in self.rows.winfo_children():
            child.destroy()

        projects = self.visible_projects()
        self.summary_label.configure(
            text=f"{len(projects)} / {len(self.projects)} projects"
        )

        if not projects:
            ttk.Label(
                self.rows,
                text="No matching projects.",
                style="Subtle.TLabel",
                padding=(4, 14),
            ).pack(anchor="w")
            return

        for project in projects:
            self._render_project(project)

    def _render_project(self, project: ProjectConfig) -> None:
        row = ttk.Frame(self.rows, padding=(4, 7))
        row.pack(fill="x")

        info = ttk.Frame(row)
        info.pack(side="left", fill="x", expand=True)
        ttk.Label(
            info,
            text=project.name,
            style="Project.TLabel",
        ).pack(anchor="w")
        effective = (
            self.env_preset
            or project.preset
            or self.global_preset_var.get()
            or "(none)"
        )
        override = project.preset or INHERIT_GLOBAL
        ttk.Label(
            info,
            text=(
                f"{project.project_dir}   [{project.config_path.suffix[1:].upper()}]"
                f"   Project: {override}   Effective: {effective}"
                + (
                    f"   [env override]"
                    if self.env_preset
                    else ""
                )
            ),
            style="Subtle.TLabel",
        ).pack(anchor="w")

        if project.error:
            ttk.Label(
                info,
                text=f"Invalid config: {project.error}",
                style="Error.TLabel",
            ).pack(anchor="w", pady=(2, 0))

        controls = ttk.Frame(row)
        controls.pack(side="right", padx=(12, 0))

        value = tk.StringVar(value=project.preset or INHERIT_GLOBAL)
        options = [INHERIT_GLOBAL, *self.presets]
        if project.preset and project.preset not in self.presets:
            options.insert(1, project.preset)

        combo = ttk.Combobox(
            controls,
            textvariable=value,
            values=options,
            state=("readonly" if not project.error else "disabled"),
            width=28,
        )
        combo.pack(side="left", padx=(0, 6))
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event, item=project, selected=value: self.change_preset(
                item, selected.get()
            ),
        )

        ttk.Button(
            controls,
            text="Open",
            command=lambda item=project: self.open_project(item.project_dir),
        ).pack(side="left")

        ttk.Separator(self.rows).pack(fill="x")

    def change_preset(self, project: ProjectConfig, preset: str) -> bool:
        try:
            if preset == INHERIT_GLOBAL:
                clear_project_preset(project.config_path)
                project.preset = ""
                self.status_var.set(
                    f"{project.name}: project override removed → inherit global"
                )
            else:
                if preset not in self.presets:
                    self.render_projects()
                    return False
                write_project_preset(project.config_path, preset)
                project.preset = preset
                self.status_var.set(
                    f"{project.name}: project preset → {preset}"
                )
        except Exception as exc:
            messagebox.showerror(
                "Cannot change preset",
                f"{project.name}\n\n{exc}",
                parent=self,
            )
            self.render_projects()
            return False

        self.render_projects()
        return True

    def apply_global_preset(self) -> None:
        preset = self.global_preset_var.get()
        if preset not in self.presets or self.main_config_path is None:
            return

        if not messagebox.askyesno(
            "Change global preset",
            (
                f'Set the global preset to "{preset}"?\n\n'
                "Projects that inherit global will follow this value. "
                "Projects with local overrides will stay unchanged."
            ),
            parent=self,
        ):
            return

        try:
            write_preset(self.main_config_path, preset)
        except Exception as exc:
            messagebox.showerror(
                "Cannot change global preset",
                str(exc),
                parent=self,
            )
            return

        if self.env_preset:
            self.status_var.set(
                f'Global preset → {preset} · effective remains "{self.env_preset}" '
                "because OH_MY_OPENCODE_SLIM_PRESET is set"
            )
        else:
            self.status_var.set(f"Global preset → {preset}")
        self.render_projects()

    def apply_bulk(self) -> None:
        preset = self.bulk_var.get()
        inherit = preset == INHERIT_GLOBAL
        if not inherit and preset not in self.presets:
            return

        projects = [
            project
            for project in self.visible_projects()
            if not project.error
        ]
        if not projects:
            return

        action = (
            "Remove project preset overrides so these projects inherit global"
            if inherit
            else f'Set project override "{preset}"'
        )
        if not messagebox.askyesno(
            "Apply project preset",
            f"{action} for {len(projects)} visible project(s)?",
            parent=self,
        ):
            return

        updated = 0
        failures: list[str] = []
        for project in projects:
            try:
                if inherit:
                    clear_project_preset(project.config_path)
                    project.preset = ""
                else:
                    write_project_preset(project.config_path, preset)
                    project.preset = preset
                updated += 1
            except Exception as exc:
                failures.append(f"{project.name}: {exc}")

        self.render_projects()
        if failures:
            messagebox.showwarning(
                "Bulk update completed with warnings",
                f"Updated: {updated}\nFailed: {len(failures)}\n\n"
                + "\n".join(failures[:12]),
                parent=self,
            )
        elif inherit:
            self.status_var.set(
                f"Removed project overrides for {updated} project(s) → inherit global."
            )
        else:
            self.status_var.set(
                f'Set project override "{preset}" for {updated} project(s).'
            )

    def open_project(self, path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", str(path)])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror(
                "Cannot open project",
                str(exc),
                parent=self,
            )


def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main() -> None:
    enable_dpi_awareness()
    app = PresetSwitcher()
    app.mainloop()
