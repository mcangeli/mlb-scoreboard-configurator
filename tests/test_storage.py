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



class ColorFileInitializationTests(unittest.TestCase):
    def test_creates_missing_live_files_from_examples(self):
        import tempfile
        import json
        from pathlib import Path
        from unittest.mock import patch
        import mlb_scoreboard_configurator.storage as storage

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            colors = root / "colors"
            colors.mkdir()
            teams_data = {"ATL": {"primary": {"r": 1, "g": 2, "b": 3}}}
            scoreboard_data = {"default": {"r": 4, "g": 5, "b": 6}}
            (colors / "teams.example.json").write_text(json.dumps(teams_data))
            (colors / "scoreboard.example.json").write_text(json.dumps(scoreboard_data))

            with patch.object(storage, "scoreboard_root", return_value=root):
                created = storage.ensure_color_files()

            self.assertEqual(
                sorted(created),
                ["colors/scoreboard.json", "colors/teams.json"],
            )
            self.assertEqual(
                json.loads((colors / "teams.json").read_text()),
                teams_data,
            )
            self.assertEqual(
                json.loads((colors / "scoreboard.json").read_text()),
                scoreboard_data,
            )

    def test_does_not_overwrite_existing_live_file(self):
        import tempfile
        import json
        from pathlib import Path
        from unittest.mock import patch
        import mlb_scoreboard_configurator.storage as storage

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            colors = root / "colors"
            colors.mkdir()
            existing = {"keep": True}
            (colors / "teams.json").write_text(json.dumps(existing))
            (colors / "teams.example.json").write_text(json.dumps({"replace": True}))
            (colors / "scoreboard.example.json").write_text(json.dumps({"new": True}))

            with patch.object(storage, "scoreboard_root", return_value=root):
                storage.ensure_color_files()

            self.assertEqual(json.loads((colors / "teams.json").read_text()), existing)
            self.assertEqual(json.loads((colors / "scoreboard.json").read_text()), {"new": True})

    def test_missing_example_raises_clear_error(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import mlb_scoreboard_configurator.storage as storage

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "colors").mkdir()

            with patch.object(storage, "scoreboard_root", return_value=root):
                with self.assertRaises(FileNotFoundError):
                    storage.ensure_color_files()


if __name__ == "__main__":
    unittest.main()
