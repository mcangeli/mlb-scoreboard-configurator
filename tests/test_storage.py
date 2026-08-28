import json
import os
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["MLB_SCOREBOARD_ROOT"] = self.temp.name
        root = Path(self.temp.name)
        (root/"colors").mkdir()
        (root/"coordinates").mkdir()
        (root/"schemas").mkdir()
        (root/"config.json").write_text('{"format":9.0}\n')
        (root/"colors"/"teams.json").write_text('{"Cubs":{"primary":[1,2,3]}}\n')
        (root/"colors"/"scoreboard.json").write_text('{"text":[255,255,255]}\n')
        (root/"coordinates"/"64x32.json").write_text('{"x":1,"y":2}\n')
    def tearDown(self):
        self.temp.cleanup()
    def test_atomic_write_and_backup(self):
        from mlb_scoreboard_configurator.storage import write_json, read_json, named_path, list_backups
        ok, errors = write_json("config", {"format":9.0,"debug":True})
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertTrue(read_json(named_path("config"))["debug"])
        self.assertTrue(list_backups("config"))
    def test_coordinate_traversal_blocked(self):
        from mlb_scoreboard_configurator.storage import named_path
        with self.assertRaises(ValueError):
            named_path("coordinates/../config.json")

if __name__ == "__main__":
    unittest.main()
