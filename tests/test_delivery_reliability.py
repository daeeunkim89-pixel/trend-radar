"""Transport failures and preparation must not cause missing or duplicate reports."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import curated_report as c
import report_request
from report_timing import editorial_target, hourly_key, prepared_target
from telegram_editor import ConnectionNotEstablished, DeliveryUncertain, TelegramClient
from test_curated_report import EMPTY, HOUR, HOUR_TEXT, NOW, edition, pick


class ReliableTransportTests(unittest.TestCase):
    def test_only_connect_timeout_is_retried_for_send_and_error_urls_are_redacted(self):
        session = Mock()
        session.post.side_effect = [requests.ConnectTimeout("sensitive-request-url"),
                                   Mock(status_code=200, json=Mock(return_value={"ok": True, "result": {"id": 1}}))]
        client = TelegramClient("synthetic", "synthetic", session=session)
        with patch("telegram_editor.time.sleep"):
            self.assertEqual(client.call("sendMessage", {}), {"id": 1})
        self.assertEqual(session.post.call_count, 2)
        self.assertEqual(session.post.call_args.kwargs["timeout"], (10, 60))
        session.post.reset_mock(side_effect=True)
        session.post.side_effect = requests.ConnectTimeout("sensitive-request-url")
        with patch("telegram_editor.time.sleep"), self.assertRaises(ConnectionNotEstablished) as error:
            client.call("sendMessage", {})
        self.assertEqual(session.post.call_count, 3)
        self.assertNotIn("sensitive-request-url", str(error.exception))

    def test_read_timeout_and_ambiguous_connection_failure_are_never_retried(self):
        for kind in (requests.ReadTimeout, requests.ConnectionError):
            session = Mock(post=Mock(side_effect=kind("sensitive-request-url")))
            client = TelegramClient("synthetic", "synthetic", session=session)
            with self.assertRaises(DeliveryUncertain) as error:
                client.call("sendMessage", {})
            session.post.assert_called_once()
            self.assertIn(kind.__name__, str(error.exception))
            self.assertNotIn("sensitive-request-url", str(error.exception))

    def test_server_errors_and_malformed_success_responses_are_uncertain_not_retryable(self):
        for status, body in ((500, {"ok": False, "error_code": 500}), (200, []),
                             (200, {"ok": True, "result": None}),
                             (200, {"ok": True, "result": {"chat": []}})):
            session = Mock(post=Mock(return_value=Mock(status_code=status, json=Mock(return_value=body))))
            client = TelegramClient("synthetic", "synthetic", session=session)
            with self.assertRaises(DeliveryUncertain):
                client.send("synthetic")
            session.post.assert_called_once()


class ReliableEditionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.picks = self.directory / "picks.json"
        self.picks.write_text(json.dumps(edition([pick(i) for i in range(10)])), encoding="utf-8")
        for field, name in (("DECISIONS_FILE", "decisions.json"), ("ATTEMPT_FILE", "status.json"),
                            ("STATE_FILE", "state.json"), ("HISTORY_FILE", "history.json")):
            p = patch.object(c, field, self.directory / name)
            p.start(); self.addCleanup(p.stop)

    def test_expired_public_uncertain_and_sent_reports_are_not_reopened(self):
        for delivery, expected in (("uncertain", 1), ("sent", 0)):
            c.DECISIONS_FILE.write_text(json.dumps({"version": 1, "editions": [{
                "hour_utc": HOUR_TEXT, "delivery_key": hourly_key(HOUR),
                "delivery": delivery, "picks": [{}] * 10}]}))
            with patch.object(c.time, "time", return_value=HOUR + 3599), \
                    patch.object(c, "load_edition") as load, patch.object(c, "TelegramClient") as client:
                self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.picks), expected)
                load.assert_not_called(); client.assert_not_called()
            status = json.loads(c.ATTEMPT_FILE.read_text())
            self.assertEqual(status["status"], "delivery_uncertain" if delivery == "uncertain" else "already_sent")
            self.assertEqual(status["ready"], 10)

    def test_preparation_wait_happens_before_opening_the_telegram_connection(self):
        client = Mock()
        def wait(target):
            client.assert_not_called()
            return False
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", client), patch.object(c, "wait_for_target", side_effect=wait):
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.picks), 2)
        client.assert_not_called()

    def test_pre_send_failure_and_uncertainty_update_current_status_without_erasing_last_send(self):
        old = {"updated_at": HOUR - 10000, "report": {"delivery": "sent", "hour_utc": "older"}}
        c.STATE_FILE.write_text(json.dumps(old))
        for failure, expected in ((ConnectionNotEstablished("synthetic"), "delivery_failed"),
                                  (DeliveryUncertain("synthetic"), "delivery_uncertain")):
            client = Mock(verify=Mock(side_effect=failure))
            with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                    patch.object(c, "wait_for_target", return_value=True), patch.object(c, "TelegramClient", return_value=client):
                self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.picks), 1)
            client.send.assert_not_called()
            current = json.loads(c.ATTEMPT_FILE.read_text())
            self.assertEqual((current["hour_utc"], current["status"], current["ready"]), (HOUR_TEXT, expected, 10))
            self.assertEqual(json.loads(c.STATE_FILE.read_text()), old)
            self.assertFalse(c.DECISIONS_FILE.exists())

    def test_scheduled_recovery_consumes_only_an_existing_current_regular_request(self):
        path = self.directory / "request.json"
        sender = Mock(return_value=0)
        request = {"version": 2, "hour_utc": HOUR_TEXT,
                   "editorial_sha256": hashlib.sha256(self.picks.read_bytes()).hexdigest()}
        path.write_text(json.dumps(request))
        self.assertEqual(report_request.run(path, HOUR + 100, sender, self.picks, scheduled_check=True), 0)
        sender.assert_called_once()
        sender.reset_mock()
        for value, clock in ((request, HOUR + 3600), (request, HOUR - 1),
                             ({**request, "version": 3, "mode": "user_requested"}, HOUR + 100)):
            path.write_text(json.dumps(value))
            self.assertEqual(report_request.run(path, clock, sender, self.picks, scheduled_check=True), 0)
        sender.assert_not_called()

    def test_one_hour_preparation_preserves_six_slots_and_75_minute_review_validity(self):
        kst = timezone(timedelta(hours=9))
        base = datetime(2026, 10, 19, tzinfo=kst)
        for hour in range(24):
            now = int(base.replace(hour=hour, minute=15).timestamp())
            target = editorial_target(now)
            if hour in (8, 11, 14, 17, 20, 23):
                self.assertEqual(target, now // 3600 * 3600)
            elif hour in (7, 10, 13, 16, 19, 22):
                self.assertEqual(target, now // 3600 * 3600 + 3600)
            else:
                self.assertIsNone(target)
        self.assertEqual(prepared_target(HOUR_TEXT, HOUR - 3600), HOUR)
        with self.assertRaises(ValueError):
            prepared_target(HOUR_TEXT, HOUR - 3601)
        value = edition([pick(i) for i in range(10)])
        value["generated_at"] = HOUR - 3600
        for p in value["picks"]:
            p.update(verified_at=HOUR - 3600, published_at=HOUR - 3600)
        self.picks.write_text(json.dumps(value))
        c.load_edition(self.picks, HOUR, HOUR)
        with self.assertRaises(ValueError):
            c.load_edition(self.picks, HOUR, HOUR + 15 * 60 + 1)
