from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omo_slim_preset_switcher.settings import (
    default_opencode_config_dir,
    default_settings,
    load_settings,
    path_key,
    save_settings,
)


class SettingsTests(unittest.TestCase):
    def test_project_roots_default_to_empty(self) -> None:
        self.assertEqual(default_settings()["project_roots"], [])

    def test_opencode_config_dir_honors_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"OPENCODE_CONFIG_DIR": "~/custom-opencode"},
            clear=False,
        ):
            self.assertEqual(
                default_opencode_config_dir(),
                Path("~/custom-opencode").expanduser(),
            )

    def test_round_trip_deduplicates_roots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            env = (
                {"APPDATA": raw}
                if os.name == "nt"
                else {"XDG_CONFIG_HOME": raw}
            )
            with patch.dict(os.environ, env, clear=False):
                save_settings(
                    {
                        "project_roots": ["/tmp/a", "/tmp/a"],
                        "opencode_config_dir": "/tmp/config",
                    }
                )
                loaded = load_settings()

            self.assertEqual(loaded["project_roots"], [str(Path("/tmp/a"))])
            self.assertEqual(
                loaded["opencode_config_dir"],
                str(Path("/tmp/config")),
            )

    def test_path_key_follows_platform_case_rules(self) -> None:
        upper = path_key("Some/Project")
        lower = path_key("some/project")

        if os.name == "nt":
            self.assertEqual(upper, lower)
        else:
            self.assertNotEqual(upper, lower)

    @unittest.skipIf(
        os.name == "nt",
        "symlink creation may require elevated Windows privileges",
    )
    def test_settings_write_does_not_follow_predictable_tmp_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            env = {"XDG_CONFIG_HOME": raw}
            with patch.dict(os.environ, env, clear=False):
                path = Path(raw) / "OmoSlimPresetSwitcher" / "settings.json"
                path.parent.mkdir(parents=True)
                victim = path.parent / "victim.txt"
                predictable_tmp = path.with_name(f"{path.name}.tmp")

                victim.write_text("do-not-touch", encoding="utf-8")
                predictable_tmp.symlink_to(victim)

                save_settings(
                    {
                        "project_roots": ["/tmp/a"],
                        "opencode_config_dir": "/tmp/config",
                    }
                )

                self.assertEqual(
                    victim.read_text(encoding="utf-8"),
                    "do-not-touch",
                )
                self.assertTrue(predictable_tmp.is_symlink())
                self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
