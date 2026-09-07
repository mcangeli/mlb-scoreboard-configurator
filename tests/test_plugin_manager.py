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


    def test_normal_plugin_update_uses_distribution(self):
        from unittest.mock import patch, Mock
        fake=Mock(returncode=0, stdout="ok", stderr="")
        with patch.object(pm, "pip_executable", return_value=Path("/venv/bin/pip")), \
             patch.object(pm.subprocess, "run", return_value=fake) as run:
            result=pm.update_plugin("some-plugin","https://github.com/example/plugin")
        cmd=run.call_args.args[0]
        self.assertEqual(cmd, ["/venv/bin/pip", "install", "--upgrade", "some-plugin"])
        self.assertFalse(result["self_update"])

    def test_configurator_update_reinstalls_and_runs_setup(self):
        from unittest.mock import patch, Mock
        pip_run=Mock(returncode=0, stdout="pip ok", stderr="")
        setup_run=Mock(returncode=0, stdout="setup ok", stderr="")
        with patch.object(pm, "pip_executable", return_value=Path("/venv/bin/pip")), \
             patch.object(pm, "setup_executable", return_value=Path("/venv/bin/mlb-scoreboard-configurator-setup")), \
             patch.object(pm, "scoreboard_root", return_value=Path("/scoreboard")), \
             patch.object(pm, "venv_bin", return_value=Path("/venv/bin")), \
             patch.object(pm.subprocess, "run", side_effect=[pip_run, setup_run]) as run:
            result=pm.update_plugin(
                "mlb-scoreboard-configurator",
                "https://github.com/example/configurator"
            )
        pip_cmd=run.call_args_list[0].args[0]
        setup_cmd=run.call_args_list[1].args[0]
        self.assertIn("--force-reinstall", pip_cmd)
        self.assertIn("git+https://github.com/example/configurator.git", pip_cmd)
        self.assertEqual(
            setup_cmd,
            ["/venv/bin/mlb-scoreboard-configurator-setup",
             "--root", "/scoreboard", "--venv-bin", "/venv/bin", "--no-enable"]
        )
        self.assertTrue(result["self_update"])
        self.assertTrue(result["restart_required"])

    def test_repository_catalog(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            with patch.object(pm, "scoreboard_root", return_value=Path(td)):
                self.assertIsInstance(pm.repository_plugins(), list)


    def test_save_repository_plugins(self):
        import tempfile, json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch.object(pm, "scoreboard_root", return_value=root):
                saved=pm.save_repository_plugins([{
                    "name":"Example",
                    "description":"Test",
                    "github_url":"https://github.com/example/plugin",
                    "distribution":"example-plugin",
                    "entry_point":"example_plugin",
                }])
                data=json.loads((root/".configurator"/"plugin_repository.json").read_text())
        self.assertEqual(saved[0]["github_url"],"https://github.com/example/plugin.git")
        self.assertEqual(data["plugins"][0]["name"],"Example")

    def test_repository_rejects_duplicate_entries(self):
        import tempfile
        from unittest.mock import patch
        entry={
            "name":"Example",
            "github_url":"https://github.com/example/plugin",
            "distribution":"example-plugin",
            "entry_point":"example_plugin",
        }
        with tempfile.TemporaryDirectory() as td:
            with patch.object(pm, "scoreboard_root", return_value=Path(td)):
                with self.assertRaises(ValueError):
                    pm.save_repository_plugins([entry,dict(entry)])

if __name__ == "__main__":
    unittest.main()
