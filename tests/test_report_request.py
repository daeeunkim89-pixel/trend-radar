import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from report_request import run
from report_timing import hourly_key

HOUR = 1792144800


class ReportRequestTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "request.json"
        self.request = {"version": 1, "hour_utc": hourly_key(HOUR).removeprefix("hourly-")}
        self.sender = Mock(return_value=0)

    def write(self, request):
        self.path.write_text(json.dumps(request), encoding="utf-8")

    def test_current_hour_uses_existing_single_report_delivery_path(self):
        self.write(self.request)
        self.assertEqual(run(self.path, HOUR + 100, self.sender), 0)
        self.sender.assert_called_once_with(recover_hour=self.request["hour_utc"])

    def test_previous_and_future_hours_are_rejected_before_sender_is_used(self):
        self.write(self.request)
        for now in (HOUR - 1, HOUR + 3600):
            self.assertEqual(run(self.path, now, self.sender), 2)
        self.sender.assert_not_called()

    def test_invalid_schema_or_unexpected_fields_cannot_trigger_delivery(self):
        for request in ([], {}, {**self.request, "version": True},
                        {**self.request, "hour_utc": 123}, {**self.request, "extra": "ignored?"}):
            self.write(request)
            self.assertEqual(run(self.path, HOUR + 100, self.sender), 2)
        self.sender.assert_not_called()

    def test_corrupt_or_missing_file_cannot_trigger_delivery(self):
        self.assertEqual(run(self.path, HOUR + 100, self.sender), 2)
        self.path.write_text("invalid JSON", encoding="utf-8")
        self.assertEqual(run(self.path, HOUR + 100, self.sender), 2)
        self.sender.assert_not_called()
