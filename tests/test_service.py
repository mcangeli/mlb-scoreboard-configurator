import unittest
from unittest.mock import patch, Mock
import mlb_scoreboard_configurator.service as service


class ServiceTests(unittest.TestCase):
    def test_scoreboard_status_uses_scoreboard_unit(self):
        fake=Mock(returncode=0, stdout="ActiveState=active\nSubState=running\nUnitFileState=enabled\n", stderr="")
        with patch.object(service, "_run", return_value=fake) as run:
            result=service.status("scoreboard")
        self.assertIn("mlb-led-scoreboard.service", run.call_args.args[0])
        self.assertEqual(result["active_state"], "active")

    def test_configurator_action_uses_configurator_unit(self):
        fake=Mock(returncode=0, stdout="", stderr="")
        with patch.object(service, "_run", return_value=fake) as run:
            ok,_=service.action("restart","configurator")
        self.assertTrue(ok)
        self.assertEqual(
            run.call_args.args[0],
            ["systemctl","restart","mlb-scoreboard-configurator.service"]
        )


if __name__ == "__main__":
    unittest.main()
