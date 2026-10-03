from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from omo_slim_preset_switcher.omo import (
    OMO_JSON,
    OMO_JSONC,
    available_presets,
    clear_project_preset,
    read_config,
    resolve_config,
    scan_projects,
    selected_preset,
    write_preset,
    write_project_preset,
)


class OmoTests(unittest.TestCase):
    def test_jsonc_has_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / OMO_JSON).write_text("{}", encoding="utf-8")
            (root / OMO_JSONC).write_text("{}", encoding="utf-8")
            self.assertEqual(resolve_config(root), root / OMO_JSONC)

    def test_available_presets_uses_main_config(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / OMO_JSONC
            path.write_text(
                """{
                  "presets": {
                    "fast": {},
                    "deep": {},
                  },
                }""",
                encoding="utf-8",
            )
            self.assertEqual(available_presets(path), ["fast", "deep"])

    def test_scan_multiple_roots_and_deduplicate_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            project = root / "workspace" / "project-a"
            config_dir = project / ".opencode"
            config_dir.mkdir(parents=True)
            (config_dir / OMO_JSON).write_text(
                '{"preset":"fast"}',
                encoding="utf-8",
            )

            projects = scan_projects([root, root / "workspace"])

            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].name, "project-a")
            self.assertEqual(projects[0].preset, "fast")

    def test_global_preset_read_and_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / OMO_JSONC
            path.write_text(
                """{
                  // global selection
                  "preset": "fast",
                  "presets": {
                    "fast": {},
                    "deep": {},
                  },
                }""",
                encoding="utf-8",
            )

            self.assertEqual(selected_preset(path), "fast")
            write_preset(path, "deep")

            text = path.read_text(encoding="utf-8")
            self.assertIn("// global selection", text)
            self.assertEqual(selected_preset(path), "deep")

    def test_clear_project_preset_preserves_other_settings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / OMO_JSONC
            path.write_text(
                """{
                  // keep
                  "preset": "local",
                  "companion": {
                    "enabled": true,
                  },
                }""",
                encoding="utf-8",
            )

            clear_project_preset(path)

            text = path.read_text(encoding="utf-8")
            self.assertIn("// keep", text)
            config = read_config(path)
            self.assertNotIn("preset", config)
            self.assertEqual(config["companion"], {"enabled": True})

    def test_write_preset_preserves_jsonc_and_bom(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / OMO_JSONC
            content = """{
              // keep this comment
              "preset": "old",
              "presets": {
                "old": {},
                "new": {},
              },
            }"""
            path.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))

            write_project_preset(path, "new")

            raw_bytes = path.read_bytes()
            self.assertTrue(raw_bytes.startswith(b"\xef\xbb\xbf"))
            text = raw_bytes.decode("utf-8-sig")
            self.assertIn("// keep this comment", text)
            self.assertIn('"preset": "new"', text)
            self.assertNotIn(path.with_name(f"{path.name}.tmp").name, [p.name for p in path.parent.iterdir()])


if __name__ == "__main__":
    unittest.main()
