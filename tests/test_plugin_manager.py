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


    def test_update_from_github(self):
        from unittest.mock import patch, Mock
        fake=Mock(returncode=0, stdout="ok", stderr="")
        with patch.object(pm, "pip_executable", return_value=Path("/venv/bin/pip")), \
             patch.object(pm.subprocess, "run", return_value=fake) as run:
            result=pm.update_plugin("package-name","https://github.com/example/plugin")
        cmd=run.call_args.args[0]
        self.assertIn("--force-reinstall", cmd)
        self.assertIn("git+https://github.com/example/plugin.git", cmd)
        self.assertEqual(result["repository"], "https://github.com/example/plugin.git")

    def test_repository_catalog(self):
        self.assertIsInstance(pm.repository_plugins(), list)

if __name__ == "__main__":
    unittest.main()
