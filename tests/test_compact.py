import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import editorial as e
import monitor
import report_timing
from telegram_editor import PrivateState, TelegramError, deliver_report, process_commands

NOW = 1792137600
CHAT = "-123456789"


def candidates(count=30, title=None):
    data = {"네이버 뉴스": [], "네이트 스포츠": [], "디시 실베": [], "펨코 포텐": []}
    names = list(data)
    for index in range(count):
        source = names[index // 10]
        row = monitor.make_item(source, title or f"손흥민 새로운 기록 관련 소식 {index}",
                                f"https://news.nate.com/view/20261016n{10000 + index}", index % 10 + 1)
        data[source].append(row)
    stories, history = e.observe(data, {"version": 1, "items": {}}, NOW)
    return stories, history, {name: len(rows) for name, rows in data.items()}


class CompactReportTests(unittest.TestCase):
    def test_one_message_shows_five_and_keeps_all_other_links_inside_expandable_section(self):
        stories, _, counts = candidates()
        parts = e.render_digest(stories, counts, {}, {}, NOW)
        self.assertEqual(len(parts), 1)
        before, folded = parts[0].split("<blockquote expandable>", 1)
        self.assertEqual(before.count('<a href="'), 5)
        self.assertEqual(folded.count('<a href="'), 25)
        self.assertLess(e.message_units(before), 900)
        self.assertLessEqual(e.message_units(parts[0]), 3900)
        for story in stories:
            self.assertIn(story["lead"]["link"], parts[0])
            self.assertNotIn(story["id"], parts[0])

    def test_long_unicode_titles_and_long_urls_still_fit_one_message(self):
        stories, _, counts = candidates(40)
        for index, story in enumerate(stories):
            story["lead"]["title"] = "🏆" * 100 + str(index)
            story["lead"]["link"] += "?tracking=" + "x" * 600
        parts = e.render_digest(stories, counts, {}, {}, NOW)
        self.assertEqual(len(parts), 1)
        self.assertGreater(len(parts[0]), 4096)
        self.assertLessEqual(e.message_units(parts[0]), 3900)
        self.assertEqual(parts[0].count('<a href="'), 40)

    def test_numbering_follows_visible_order_including_completed_items(self):
        stories, _, counts = candidates(8)
        state = {"statuses": {stories[0]["id"]: {"status": "done"}}}
        numbers = e.digest_numbers(stories, state)
        self.assertEqual(numbers["8"], stories[0]["id"])
        report = e.render_digest(stories, counts, {}, state, NOW)[0]
        self.assertIn("08 ", report)

    def test_default_cli_and_preview_never_create_telegram_client_or_write_live_state(self):
        with patch.object(monitor, "main", return_value=0) as main:
            self.assertEqual(monitor.run_cli([]), 0)
            main.assert_called_once_with(commands_only=False, preview=True, scheduled=False, recover_hour=None)
        stories, _, _ = candidates(1)
        row = stories[0]["lead"]
        with patch.object(monitor, "load_history", return_value={"version": 1, "items": {}}), \
                patch.object(monitor, "collect", return_value=({row["source"]: [row]}, {})), \
                patch.object(monitor, "enrich"), patch.object(monitor, "TelegramClient") as client, \
                patch.object(monitor, "atomic_json") as save, patch.object(monitor, "save_state") as status:
            self.assertEqual(monitor.main(preview=True), 0)
            client.assert_not_called()
            save.assert_not_called()
            status.assert_not_called()

    def test_workflow_edits_and_manual_checks_cannot_send_reports(self):
        root = Path(__file__).resolve().parents[1]
        preview = (root / ".github/workflows/send-once.yml").read_text()
        connection = (root / ".github/workflows/telegram-connection.yml").read_text()
        scheduled = (root / ".github/workflows/monitor.yml").read_text()
        self.assertNotIn("push:", preview)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", preview)
        self.assertIn("python monitor.py --preview", preview)
        self.assertNotIn("push:", connection)
        self.assertNotIn("'sendMessage'", connection)
        self.assertIn('cron: "40,50,5 * * * *"', scheduled)
        self.assertIn("python -u candidate_snapshot.py", scheduled)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", scheduled)
        self.assertNotIn("--scheduled-report", scheduled)
        self.assertNotIn("workflow_dispatch:", scheduled)


class ScheduledReportTests(unittest.TestCase):
    def test_preparation_and_delayed_start_share_target_hour_but_manual_runs_cannot_send(self):
        hour = NOW // 3600 * 3600
        self.assertEqual(report_timing.scheduled_target(hour + 40 * 60, "schedule"), hour + 3600)
        self.assertEqual(report_timing.scheduled_target(hour + 50 * 60, "schedule"), hour + 3600)
        self.assertEqual(report_timing.scheduled_target(hour + 59 * 60, "schedule"), hour + 3600)
        self.assertEqual(report_timing.scheduled_target(hour + 3600 + 2 * 60, "schedule"), hour + 3600)
        self.assertEqual(report_timing.scheduled_target(hour + 3600 + 5 * 60, "schedule"), hour + 3600)
        self.assertEqual(report_timing.scheduled_target(hour + 3600 + 39 * 60, "schedule"), hour + 3600)
        self.assertIsNone(report_timing.scheduled_target(hour + 50 * 60, "workflow_dispatch"))
        with patch.object(monitor, "scheduled_target", return_value=None), \
                patch.object(monitor, "TelegramClient") as client, patch.object(monitor, "collect") as collect:
            self.assertEqual(monitor.main(scheduled=True), 0)
            client.assert_not_called()
            collect.assert_not_called()

    def test_publication_waits_for_boundary_and_accepts_delays_in_same_hour(self):
        clock = [1000.25]
        sleeps = []
        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds
        self.assertTrue(report_timing.wait_for_target(1010, lambda: clock[0], sleep))
        self.assertEqual(clock[0], 1010)
        self.assertTrue(all(0 < seconds <= 5 for seconds in sleeps))
        self.assertTrue(report_timing.wait_for_target(1010, lambda: 1031, sleep))
        self.assertFalse(report_timing.wait_for_target(1010, lambda: 4610, sleep))

    def test_explicit_recovery_rejects_old_future_and_invalid_hours(self):
        hour = NOW // 3600 * 3600
        text = report_timing.hourly_key(hour).removeprefix("hourly-")
        self.assertEqual(report_timing.recovery_target(text, hour + 600), hour)
        for value, now in [(text, hour - 1), (text, hour + 3600), ("2026130120", hour), ("202610169", hour)]:
            with self.assertRaises(ValueError):
                report_timing.recovery_target(value, now)

    def test_already_delivered_hour_does_not_collect_or_send_again(self):
        hour = NOW // 3600 * 3600
        private = Mock(data={"reports": {report_timing.hourly_key(hour): {"done": True, "message_ids": [55]}}})
        with patch.object(monitor, "scheduled_target", return_value=hour), \
                patch.object(monitor, "load_history", return_value={}), \
                patch.object(monitor, "PrivateState", return_value=private), \
                patch.object(monitor, "TelegramClient") as client, \
                patch.object(monitor, "collect") as collect, patch.object(monitor, "process_commands") as commands:
            self.assertEqual(monitor.main(scheduled=True), 0)
            collect.assert_not_called()
            commands.assert_not_called()
            client.return_value.send.assert_not_called()

    def test_previous_multi_message_report_is_not_resumed(self):
        private = Mock(data={"reports": {"hourly": {"done": False, "message_ids": [99],
                        "parts": ["old one", "old two"], "next": 1, "started_at": NOW}}})
        client = Mock()
        self.assertEqual(deliver_report(client, ["new compact"], private, "hourly", NOW), 0)
        client.send.assert_not_called()


class NumberCommandTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.private = PrivateState("synthetic-key-only", CHAT, Path(directory.name) / "editor.enc")
        self.private.data["offset"] = 1
        self.stories, self.history, _ = candidates(2)
        self.first, self.second = [s["id"] for s in self.stories]
        self.private.data["reports"] = {
            "old": {"started_at": NOW - 3600, "done": True, "numbers": {"1": self.first}, "message_ids": [100]},
            "new": {"started_at": NOW, "done": True, "numbers": {"1": self.second}, "message_ids": [200]},
        }
        self.client = Mock(chat_id=CHAT, username="test_bot")

    def update(self, text, reply_id=None):
        message = {"chat": {"id": int(CHAT)}, "from": {"is_bot": False}, "date": NOW, "text": text}
        if reply_id:
            message["reply_to_message"] = {"message_id": reply_id}
        self.client.call.return_value = [{"update_id": 1, "message": message}]

    def test_short_number_selects_latest_report_item(self):
        self.update("/pick 01")
        process_commands(self.client, self.private, self.history, NOW)
        self.assertEqual(self.private.data["statuses"][self.second]["status"], "pick")
        self.assertNotIn(self.first, self.private.data["statuses"])

    def test_reply_to_older_report_uses_older_number_mapping(self):
        self.update("/pick 01", reply_id=100)
        process_commands(self.client, self.private, self.history, NOW)
        self.assertEqual(self.private.data["statuses"][self.first]["status"], "pick")
        self.assertNotIn(self.second, self.private.data["statuses"])

    def test_unknown_reply_does_not_silently_select_a_different_report_item(self):
        self.update("/pick 01", reply_id=999)
        process_commands(self.client, self.private, self.history, NOW)
        self.assertEqual(self.private.data["statuses"], {})

    def test_details_are_sent_only_when_requested_and_do_not_select_material(self):
        self.update("/info 01")
        process_commands(self.client, self.private, self.history, NOW)
        self.assertEqual(self.private.data["statuses"], {})
        self.assertIn("원문 미리보기", self.client.send.call_args.args[0])
        self.assertIn(self.second, self.client.send.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
