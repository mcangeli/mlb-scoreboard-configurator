import ast
import unittest
from pathlib import Path

class WebVersionRegressionTests(unittest.TestCase):
    def test_web_source_parses(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "mlb_scoreboard_configurator" / "web.py").read_text()
        ast.parse(source)

    def test_version_import_is_top_level(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "mlb_scoreboard_configurator" / "web.py").read_text()
        self.assertIn("from . import __version__\nfrom .storage import (", source)

    def test_template_displays_version(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "mlb_scoreboard_configurator" / "templates" / "index.html").read_text()
        self.assertIn("v{{ configurator_version }}", template)

if __name__ == "__main__":
    unittest.main()
