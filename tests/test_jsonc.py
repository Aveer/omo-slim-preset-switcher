from __future__ import annotations

import unittest

from omo_slim_preset_switcher import jsonc


class JsoncTests(unittest.TestCase):
    def test_loads_comments_and_trailing_commas(self) -> None:
        value = jsonc.loads(
            """{
              // comment
              "preset": "one",
              "url": "https://example.test//path",
              "nested": {
                "value": 1,
              },
            }"""
        )
        self.assertEqual(value["preset"], "one")
        self.assertEqual(value["url"], "https://example.test//path")
        self.assertEqual(value["nested"], {"value": 1})

    def test_targeted_update_preserves_comments_and_nested_preset(self) -> None:
        original = """{
          // keep
          "preset": "old",
          "nested": {
            "preset": "nested",
          },
        }
        """
        updated = jsonc.set_top_level_string(original, "preset", "new")

        self.assertIn("// keep", updated)
        self.assertIn('"preset": "new"', updated)
        self.assertIn('"preset": "nested"', updated)
        self.assertEqual(jsonc.loads(updated)["preset"], "new")

    def test_removes_top_level_preset_and_preserves_comments(self) -> None:
        original = """{
          // keep this comment
          "preset": "local",
          "companion": {
            "enabled": true,
          },
        }"""
        updated = jsonc.remove_top_level_string(original, "preset")

        self.assertIn("// keep this comment", updated)
        self.assertNotIn('"preset": "local"', updated)
        self.assertEqual(
            jsonc.loads(updated),
            {"companion": {"enabled": True}},
        )

    def test_removes_preset_when_intervening_comment_contains_comma(self) -> None:
        original = """{
          "preset": "local" /* comment, with comma */,
          "companion": {"enabled": true},
        }"""
        updated = jsonc.remove_top_level_string(original, "preset")

        self.assertEqual(
            jsonc.loads(updated),
            {"companion": {"enabled": True}},
        )

    def test_removes_last_top_level_preset_without_breaking_previous_comma(self) -> None:
        original = """{
          "companion": {"enabled": true},
          // local selection
          "preset": "local"
        }"""
        updated = jsonc.remove_top_level_string(original, "preset")

        self.assertIn("// local selection", updated)
        self.assertEqual(
            jsonc.loads(updated),
            {"companion": {"enabled": True}},
        )

    def test_remove_last_preset_preserves_previous_trailing_comment(self) -> None:
        original = """{
          "companion": {"enabled": true}, // keep this explanation
          "preset": "local",
        }
        """
        updated = jsonc.remove_top_level_string(original, "preset")

        self.assertIn("// keep this explanation", updated)
        parsed = jsonc.loads(updated)
        self.assertNotIn("preset", parsed)
        self.assertEqual(parsed["companion"], {"enabled": True})

    def test_inserts_missing_preset(self) -> None:
        updated = jsonc.set_top_level_string(
            """{
              // config
              "presets": {},
            }""",
            "preset",
            "new",
        )
        self.assertEqual(jsonc.loads(updated)["preset"], "new")
        self.assertIn("// config", updated)


if __name__ == "__main__":
    unittest.main()
