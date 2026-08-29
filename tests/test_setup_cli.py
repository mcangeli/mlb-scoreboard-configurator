import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class SetupCliTests(unittest.TestCase):
    def test_detect_root_from_cwd(self):
        from mlb_scoreboard_configurator.setup_cli import detect_scoreboard_root
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/"config.json").write_text("{}")
            (p/"coordinates").mkdir()
            old = os.getcwd()
            try:
                os.chdir(p)
                self.assertEqual(detect_scoreboard_root(), p.resolve())
            finally:
                os.chdir(old)

    def test_detect_explicit_root(self):
        from mlb_scoreboard_configurator.setup_cli import detect_scoreboard_root
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(detect_scoreboard_root(td), Path(td).resolve())

    def test_detect_venv_prefers_invoked_console_script(self):
        from mlb_scoreboard_configurator.setup_cli import detect_venv
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "scoreboard"
            bindir = root / "venv" / "bin"
            bindir.mkdir(parents=True)
            for name in ("mlb-scoreboard-configurator", "mlb-scoreboard-hotspot-watch",
                         "mlb-scoreboard-configurator-setup"):
                (bindir / name).write_text("")
            with patch("sys.argv", [str(bindir / "mlb-scoreboard-configurator-setup")]), \
                 patch("sys.executable", "/usr/bin/python3"):
                self.assertEqual(detect_venv(root), bindir.resolve())


    def test_setup_initializes_missing_color_files(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "mlb_scoreboard_configurator" / "setup_cli.py").read_text()
        self.assertIn('os.environ["MLB_SCOREBOARD_ROOT"] = str(root)', source)
        self.assertIn("created_color_files = ensure_color_files()", source)

if __name__ == "__main__":
    unittest.main()
