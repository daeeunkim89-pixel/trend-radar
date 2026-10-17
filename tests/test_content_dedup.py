import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import editorial as e
import monitor
from telegram_editor import (CONTENT_RETENTION, DeliveryUncertain, PrivateState, TelegramError,
                             deliver_report, story_content_keys, unreported_stories)
from test_editorial import CHAT, EMPTY, NOW, TOKEN, row


class ContentDedupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "editor.enc"
        self.private = PrivateState(TOKEN, CHAT, self.path)
        self.client = Mock(send=Mock(return_value=99))
        self.old = row(title="장원영 새로운 인터뷰 내용 공개", views=100)
        self.stories, self.history = e.observe({"디시 실베": [self.old]}, EMPTY, NOW)
        self.story = self.stories[0]
        self.keys = story_content_keys(self.story)

    def send_old(self):
        deliver_report(self.client, ["old report"], self.private, "old", NOW,
                       numbers={"1": self.story["id"]}, content_keys=self.keys)

    def test_collection_history_alone_does_not_mark_content_as_delivered(self):
        self.assertEqual(unreported_stories(self.stories, self.history, self.private, NOW + 3600), self.stories)
        self.assertEqual(self.private.data["content_history"], {})

    def test_legacy_numbers_migrate_sent_partial_and_uncertain_reports_but_not_rejections(self):
        for flags, excluded in (({"done": True}, True), ({"message_ids": [10]}, True),
                                ({"uncertain": True}, True), ({"done": False}, False)):
            with self.subTest(flags=flags):
                private = Mock(data={"reports": {"legacy": {"started_at": NOW,
                                   "numbers": {"1": self.story["id"]}, **flags}}})
                fresh = unreported_stories(self.stories, self.history, private, NOW + 3600)
                self.assertEqual(len(fresh), 0 if excluded else 1)
                self.assertEqual(bool(self.keys.intersection(private.data["content_history"])), excluded)

    def test_sent_url_remains_excluded_after_title_metric_and_address_changes(self):
        self.send_old()
        changed = {**self.old, "title": "수정된 기사 제목입니다", "views": 100000,
                   "link": "https://m.dcinside.com/board/dcbest/123456?utm_source=tracking"}
        stories, history = e.observe({"디시 실베": [changed]}, self.history, NOW + 3600)
        private = PrivateState(TOKEN, CHAT, self.path)
        self.assertEqual(unreported_stories(stories, history, private, NOW + 3600), [])

    def test_identical_headline_on_new_source_is_excluded_after_short_ledgers_expire(self):
        self.send_old()
        self.private.data["reports"] = {}
        self.private.save()
        private = PrivateState(TOKEN, CHAT, self.path)
        same = row(source="네이버 뉴스", title="[영상] 장원영 새로운 인터뷰 내용 공개", post=456789)
        followup = row(title="장원영 다음 공연 일정과 장소 발표", post=456790)
        stories, history = e.observe({"네이버 뉴스": [same], "디시 실베": [followup]}, EMPTY, NOW + 4 * 86400)
        fresh = unreported_stories(stories, history, private, NOW + 4 * 86400)
        self.assertEqual([x["lead"]["title"] for x in fresh], [followup["title"]])

    def test_uncertain_delivery_cannot_reappear_in_a_later_hour_after_restart(self):
        self.client.send.side_effect = DeliveryUncertain("synthetic uncertain delivery")
        with self.assertRaises(DeliveryUncertain):
            self.send_old()
        private = PrivateState(TOKEN, CHAT, self.path)
        private.data["reports"] = {}
        private.save()
        reopened = PrivateState(TOKEN, CHAT, self.path)
        self.assertEqual(unreported_stories(self.stories, EMPTY, reopened, NOW + 3600), [])

    def test_explicit_rejection_does_not_hide_an_unsent_candidate(self):
        self.client.send.side_effect = TelegramError("synthetic explicit rejection")
        with self.assertRaises(TelegramError):
            self.send_old()
        private = PrivateState(TOKEN, CHAT, self.path)
        self.assertEqual(unreported_stories(self.stories, self.history, private, NOW + 3600), self.stories)

    def test_completed_hour_does_not_record_new_content_that_was_never_sent(self):
        self.send_old()
        self.client.send.reset_mock()
        deliver_report(self.client, ["different report"], self.private, "old", NOW + 10,
                       content_keys={"item:never-sent"})
        self.client.send.assert_not_called()
        self.assertNotIn("item:never-sent", self.private.data["content_history"])

    def test_content_retention_is_seven_days_and_does_not_refresh_from_older_reports(self):
        self.send_old()
        private = PrivateState(TOKEN, CHAT, self.path)
        self.assertEqual(unreported_stories(self.stories, self.history, private, NOW + CONTENT_RETENTION - 1), [])
        self.assertEqual(unreported_stories(self.stories, self.history, private, NOW + CONTENT_RETENTION + 1), self.stories)
        self.assertEqual(private.data["content_history"], {})

    def test_hourly_pipeline_only_renders_and_numbers_new_candidates_then_a_short_empty_report(self):
        self.send_old()
        new = row(title="카리나 새로운 신곡 무대 공개", post=987654)
        data = {"디시 실베": [self.old, new]}
        for offset, expected_new, expected_duplicates in ((3600, 1, 1), (7200, 0, 2)):
            with self.subTest(offset=offset), \
                    patch.object(monitor.time, "time", return_value=NOW + offset + 600), \
                    patch.object(monitor, "scheduled_target", return_value=NOW // 3600 * 3600 + offset), \
                    patch.object(monitor, "wait_for_target", return_value=True), \
                    patch.object(monitor, "collect", return_value=(data, {})), \
                    patch.object(monitor, "load_history", return_value=self.history), \
                    patch.object(monitor, "TelegramClient", return_value=self.client), \
                    patch.object(monitor, "PrivateState", return_value=self.private), \
                    patch.object(monitor, "process_commands"), patch.object(monitor, "enrich"), \
                    patch.object(monitor, "atomic_json"), patch.object(monitor, "save_state") as save:
                self.client.send.reset_mock()
                self.assertEqual(monitor.main(scheduled=True), 0)
                self.client.send.assert_called_once()
                message = self.client.send.call_args.args[0]
                self.assertNotIn(self.old["title"], message)
                report = save.call_args.args[2]
                self.assertEqual(report["stories"], expected_new)
                self.assertEqual(report["duplicates_excluded"], expected_duplicates)
                self.assertEqual(report["messages"], 1)
                latest = max(self.private.data["reports"].values(), key=lambda x: x["started_at"])
                if expected_new:
                    self.assertIn(new["title"], message)
                    self.assertEqual(latest["numbers"], {"1": e.item_id(new["link"])})
                    self.assertIn("실베 1", message)
                else:
                    self.assertNotIn('<a href="', message)
                    self.assertIn("새로 보낼 소재가 없습니다", message)
                    self.assertIn("중복 2개 제외", message)
                    self.assertIn("실베 0", message)
                    self.assertEqual(latest["numbers"], {})


if __name__ == "__main__":
    unittest.main()
