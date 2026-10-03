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
            with patch.dict(os.environ, {"APPDATA": raw}, clear=False):
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


if __name__ == "__main__":
    unittest.main()
