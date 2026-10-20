import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import curated_report as c
import report_request
from report_timing import hourly_key
from telegram_editor import PrivateState, DeliveryUncertain
from test_curated_report import HOUR, HOUR_TEXT, NOW, EMPTY, pick, edition


class ScheduledFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        for field, filename in (("PROGRESS_FILE", "progress.json"), ("DECISIONS_FILE", "decisions.json"),
                                ("STATE_FILE", "state.json"), ("ATTEMPT_FILE", "status.json"),
                                ("HISTORY_FILE", "history.json")):
            p = patch.object(c, field, self.path / filename)
            p.start()
            self.addCleanup(p.stop)

    def complete(self, number):
        p = pick(number)
        p["readiness"] = {"mode": "major_news", "event_date": "2026-10-17",
                          "observation": "공식 발표의 확정된 영향을 확인했다.", "checked_materials": [],
                          "outline": ["확정 사실과 규모", "실제 바뀌는 결과"]}
        return p

    def save_progress(self):
        good, expired, malformed = self.complete(1), self.complete(2), pick(3)
        expired["verified_at"] = NOW - 76*60
        rows = []
        for p in (good, expired, malformed):
            cov = edition([p])["coverage"]
            rows.append({"status": "reviewed", "pick": p, "coverage": cov})
        rows.append({"status": "needs_visual", "pick": self.complete(4),
                     "coverage": edition([self.complete(4)])["coverage"]})
        c.PROGRESS_FILE.write_text(json.dumps({"version": 1, "items": rows}))
        return good

    def test_only_complete_fresh_reviews_are_reused_without_bumping_verified_time(self):
        good = self.save_progress()
        result = c.load_progress_edition(HOUR, NOW)
        self.assertEqual([p["event_key"] for p in result["picks"]], [good["event_key"]])
        self.assertEqual(result["picks"][0]["verified_at"], good["verified_at"])
        self.assertEqual(result["coverage"]["queries"], edition([good])["coverage"]["queries"])

    def test_missing_ai_request_sends_fresh_saved_pick_or_zero_status_once(self):
        for available in (True, False):
            with self.subTest(available=available):
                if available:
                    self.save_progress()
                elif c.PROGRESS_FILE.exists():
                    c.PROGRESS_FILE.unlink()
                if c.DECISIONS_FILE.exists():
                    c.DECISIONS_FILE.unlink()
                private = PrivateState("synthetic-token", "-123456", self.path / f"fallback-{available}.enc")
                client = Mock(send=Mock(return_value=333))
                with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                        patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private):
                    args = dict(recover_hour=HOUR_TEXT, scheduled_fallback=True)
                    self.assertEqual(c.main(**args), 0)
                    self.assertEqual(c.main(**args), 0)
                client.send.assert_called_once()
                report = json.loads(c.STATE_FILE.read_text())["report"]
                self.assertEqual((report["stories"], report["messages"]), (int(available), 1))
                self.assertEqual(report["missing"], 10-int(available))
                self.assertEqual(report["trigger"], "scheduled_fallback")
                self.assertTrue(private.data["reports"][hourly_key(HOUR)]["done"])

    def test_missing_request_falls_back_only_in_a_regular_current_hour(self):
        path = self.path / "request.json"
        sender = Mock(return_value=0)
        self.assertEqual(report_request.run(path, NOW, sender, scheduled_check=True), 0)
        sender.assert_called_once_with(recover_hour=HOUR_TEXT, scheduled_fallback=True)
        sender.reset_mock()
        self.assertEqual(report_request.run(path, HOUR+3600+100, sender, scheduled_check=True), 0)
        sender.assert_not_called()

    def test_uncertain_status_report_is_not_retried(self):
        private = PrivateState("synthetic-token", "-123456", self.path / "uncertain.enc")
        client = Mock(send=Mock(side_effect=DeliveryUncertain("synthetic")))
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private):
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, scheduled_fallback=True), 1)
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, scheduled_fallback=True), 1)
        client.send.assert_called_once()
