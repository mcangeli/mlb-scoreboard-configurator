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

if __name__ == "__main__":
    unittest.main()
