import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import mlb_scoreboard_configurator.plugin_manager as pm

class PluginManagerTests(unittest.TestCase):
    def test_normalize_github_url(self):
        self.assertEqual(pm.normalize_github_url("https://github.com/example/plugin"), "https://github.com/example/plugin.git")
        self.assertEqual(pm.normalize_github_url("git+https://github.com/example/plugin.git"), "https://github.com/example/plugin.git")

    def test_rejects_unsafe_urls(self):
        for value in ("", "https://example.com/plugin.git", "file:///tmp/plugin", "https://github.com/example/plugin?x=1", "https://github.com/example/plugin/extra"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    pm.normalize_github_url(value)

    def test_pip_path_uses_scoreboard_venv(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            pip=root/"venv"/"bin"/"pip"
            pip.parent.mkdir(parents=True)
            pip.write_text("#!/bin/sh\n")
            with patch.dict("os.environ", {"MLB_SCOREBOARD_ROOT": str(root)}, clear=False):
                self.assertEqual(pm.pip_executable(), pip.resolve())

    def test_rejects_bad_distribution_name(self):
        for value in ("", "../bad", "name;rm", "a b"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): pm._safe_distribution_name(value)

if __name__ == "__main__":
    unittest.main()
