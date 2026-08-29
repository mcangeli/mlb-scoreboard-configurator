import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mlb_scoreboard_configurator.system_settings import (
    validate_hostname, read_env_file, write_auth
)

class SystemSettingsTests(unittest.TestCase):
    def test_validate_hostname(self):
        self.assertEqual(validate_hostname("mlb-scoreboard"), "mlb-scoreboard")
        for bad in ("", "-bad", "bad-", "bad_name", "a"*64):
            with self.assertRaises(ValueError):
                validate_hostname(bad)

    def test_write_auth_preserves_other_env_values(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"config.env"
            path.write_text("MLB_WIFI_INTERFACE=wlan0\nCONFIGURATOR_USERNAME=admin\nCONFIGURATOR_PASSWORD=scoreboard\n")
            write_auth("mark", "newpass123", path)
            data=read_env_file(path)
            self.assertEqual(data["MLB_WIFI_INTERFACE"], "wlan0")
            self.assertEqual(data["CONFIGURATOR_USERNAME"], "mark")
            self.assertEqual(data["CONFIGURATOR_PASSWORD"], "newpass123")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_system_routes_use_require_auth(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "mlb_scoreboard_configurator" / "web.py").read_text()
        self.assertNotIn("@auth_required", source)
        self.assertGreaterEqual(source.count("@require_auth"), 4)

if __name__ == "__main__":
    unittest.main()
