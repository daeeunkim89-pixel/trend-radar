import os
import unittest
from unittest.mock import patch
import curated_report as c
from test_curated_report import NOW

class BoundedDeliveryTests(unittest.TestCase):
    def test_deployed_no_wait_mode_exits_before_telegram_for_a_future_slot(self):
        with patch.dict(os.environ, {"BTP_NO_PREHOUR_WAIT": "1"}), \
                patch.object(c.time, "time", return_value=NOW), \
                patch.object(c, "prepared_target", return_value=NOW + 1800), \
                patch.object(c, "TelegramClient") as telegram, \
                patch.object(c, "wait_for_target") as wait:
            self.assertEqual(c.main(prepared_hour="2026101711"), 2)
            telegram.assert_not_called()
            wait.assert_not_called()
