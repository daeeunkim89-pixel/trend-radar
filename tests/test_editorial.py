import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import editorial as e
import monitor
from telegram_editor import (DeliveryUncertain, PrivateState, TelegramClient, TelegramError,
                             deliver_report, process_commands)

NOW = 1792110000
EMPTY = {"version": 1, "items": {}}
TOKEN = "synthetic-test-key-only"
CHAT = "-123456789"


def row(source="디시 실베", title="손흥민 역대 최다 도움 신기록 달성", post=123456, views=None, reactions=None):
    url = f"https://gall.dcinside.com/board/view/?id=dcbest&no={post}"
    return monitor.make_item(source, title, url, 1, views, reactions)


class HistoryTests(unittest.TestCase):
    def test_first_observation_has_no_invented_growth_and_missing_is_distinct_from_zero(self):
        stories, history = e.observe({"디시 실베": [row(views=0)]}, EMPTY, NOW)
        item = stories[0]["lead"]
        self.assertTrue(item["new"])
        self.assertNotIn("views", item["change"])
        self.assertIn("조회 0", e.reaction_text(item))
        self.assertNotIn("추천 0", e.reaction_text(item))
        self.assertEqual(EMPTY["items"], {})

    def test_growth_uses_actual_elapsed_time_and_canonical_url(self):
        old = row(views=100, reactions=5)
        _, history = e.observe({"디시 실베": [old]}, EMPTY, NOW)
        latest = row(views=190, reactions=8)
        latest["link"] = "https://m.dcinside.com/board/dcbest/123456?utm_source=test"
        stories, history = e.observe({"디시 실베": [latest]}, history, NOW + 1800)
        item = stories[0]["lead"]
        self.assertFalse(item["new"])
        self.assertEqual(item["change"]["views"], 90)
        self.assertEqual(item["change"]["views_hourly"], 180)
        self.assertIn("30분 전 대비 +90", e.reaction_text(item))
        self.assertEqual(len(history["items"]), 1)

    def test_missing_metric_stale_sample_and_counter_reset_do_not_generate_growth(self):
        _, history = e.observe({"디시 실베": [row(views=100, reactions=5)]}, EMPTY, NOW)
        stories, _ = e.observe({"디시 실베": [row(views=80)]}, history, NOW + 3600)
        item = stories[0]["lead"]
        self.assertTrue(item["change"]["views_reset"])
        self.assertNotIn("reactions", item["change"])
        self.assertNotIn("views_hourly", item["change"])
        stories, _ = e.observe({"디시 실베": [row(views=1000)]}, history, NOW + 7 * 3600)
        self.assertNotIn("views", stories[0]["lead"]["change"])

    def test_same_person_different_event_is_not_merged(self):
        data = {"디시 실베": [row(title="손흥민 역대 최다 도움 신기록 달성"), row(title="손흥민 다음 경기 일정 공개", post=123457)]}
        stories, _ = e.observe(data, EMPTY, NOW)
        self.assertEqual(len(stories), 2)

    def test_identical_headlines_merge_across_sources_and_keep_stable_id(self):
        first = row()
        second = row(source="네이트 스포츠", title="[속보] 손흥민 역대 최다 도움 신기록 달성", post=123457)
        stories, history = e.observe({"디시 실베": [first], "네이트 스포츠": [second]}, EMPTY, NOW)
        self.assertEqual(len(stories), 1)
        self.assertEqual(len(stories[0]["members"]), 2)
        story_id = stories[0]["id"]
        stories, _ = e.observe({"네이트 스포츠": [second]}, history, NOW + 3600)
        self.assertEqual(stories[0]["id"], story_id)

    def test_missing_counts_are_none_and_abbreviations_parse(self):
        self.assertIsNone(monitor.number("-"))
        self.assertIsNone(monitor.number("로그인 필요"))
        self.assertEqual(monitor.number("0"), 0)
        self.assertEqual(monitor.number("12,345"), 12345)
        self.assertEqual(monitor.number("1.2만"), 12000)

    def test_ambiguous_rank_is_not_reported_as_rank_growth(self):
        old = row(source="네이버 뉴스")
        _, history = e.observe({"네이버 뉴스": [old]}, EMPTY, NOW)
        old["rank"] = 10
        stories, _ = e.observe({"네이버 뉴스": [old]}, history, NOW + 3600)
        self.assertEqual(stories[0]["lead"]["change"], {"seconds": 3600})

    def test_all_forty_candidates_survive_grouping_and_telegram_chunking(self):
        data = {f"source-{n}": [row(source=f"source-{n}", post=100000 + n * 10 + k) for k in range(10)] for n in range(4)}
        stories, _ = e.observe(data, EMPTY, NOW)
        chunks = e.render_digest(stories, {s: len(rows) for s, rows in data.items()}, {}, {}, NOW)
        text = "\n".join(chunks)
        self.assertEqual(len(stories), 1)
        for rows in data.values():
            for item in rows:
                self.assertIn(str(e.item_id(item["link"])), json.dumps(e.observe(data, EMPTY, NOW)[1]))
                self.assertIn(e.html.escape(e.canonical_url(item["link"]), quote=True), text)
        self.assertTrue(all(len(c.encode("utf-16-le")) // 2 <= 3500 for c in chunks))

    def test_enrichment_caches_failures_and_success_without_dropping_candidates(self):
        stories, history = e.observe({"디시 실베": [row()]}, EMPTY, NOW)
        fetch = Mock(return_value={"unavailable": "HTTP 403", "media": []})
        e.enrich(stories, history, NOW, fetch)
        e.enrich(stories, history, NOW + 3600, fetch)
        fetch.assert_called_once()
        self.assertEqual(len(stories), 1)

    def test_no_article_timestamp_is_inferred_from_body_or_image(self):
        detail = e.parse_detail('<div id="dic_area">블랙박스 2024-01-01 12:00:00 촬영</div>', "https://n.news.naver.com/article/001/123", "제목")
        self.assertNotIn("published_at", detail)
        detail = e.parse_detail('<time datetime="2024-01-01T12:00:00">댓글 시간</time>', "https://n.news.naver.com/article/001/123", "제목")
        self.assertNotIn("published_at", detail)

    def test_excerpts_are_short_and_html_is_escaped(self):
        title = "손흥민 <b>제목</b> & 신기록"
        markup = '<meta property="article:published_time" content="2026-10-16T15:00:00+09:00"><div id="dic_area">' + "확인된 원문 내용 " * 30 + "</div>"
        detail = e.parse_detail(markup, "https://n.news.naver.com/article/001/123", title)
        self.assertLessEqual(len(title.split()) + len(detail["excerpt"].split()), 24)
        stories, _ = e.observe({"디시 실베": [row(title=title)]}, EMPTY, NOW)
        stories[0]["detail"] = detail
        rendered = e.render_card(stories[0], 1, {})
        self.assertIn("&lt;b&gt;", rendered)
        self.assertIn("기사 표기 시각", rendered)

    def test_unapproved_redirect_is_never_requested(self):
        response = Mock(status_code=302, headers={"Location": "https://127.0.0.1/private"})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(e.requests, "get", return_value=response) as get:
            result = e.fetch_detail(row())
        self.assertIn("unavailable", result)
        self.assertEqual(get.call_count, 1)


class TelegramTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "editor.enc"
        self.private = PrivateState(TOKEN, CHAT, self.path)
        self.stories, self.history = e.observe({"디시 실베": [row()]}, EMPTY, NOW)
        self.key = self.stories[0]["id"]
        self.client = Mock(chat_id=CHAT, username="test_bot")

    def update(self, update_id, text, chat=CHAT, username="user", is_bot=False):
        return {"update_id": update_id, "message": {"chat": {"id": int(chat)}, "text": text,
                "date": NOW, "from": {"username": username, "is_bot": is_bot}}}

    def test_editorial_state_roundtrip_is_encrypted_and_wrong_key_is_rejected(self):
        self.private.data["statuses"][self.key] = {"status": "pick", "updated_at": NOW}
        self.private.save()
        self.assertNotIn(b"pick", self.path.read_bytes())
        self.assertNotIn(self.key.encode(), self.path.read_bytes())
        reopened = PrivateState(TOKEN, CHAT, self.path)
        self.assertEqual(reopened.data, self.private.data)
        before = self.path.read_bytes()
        reopened.save()
        self.assertEqual(before, self.path.read_bytes())
        with self.assertRaises(TelegramError):
            PrivateState("changed-token", CHAT, self.path)

    def test_first_start_does_not_execute_old_messages(self):
        self.client.call.return_value = [self.update(10, f"/pick {self.key}")]
        self.assertEqual(process_commands(self.client, self.private, self.history, NOW), 0)
        self.assertEqual(self.private.data["offset"], 11)
        self.assertEqual(self.private.data["statuses"], {})
        self.client.send.assert_not_called()

    def test_only_target_group_human_commands_for_this_bot_are_accepted(self):
        self.private.data["offset"] = 1
        self.client.call.return_value = [
            self.update(1, f"/pick {self.key}", chat="-999"),
            self.update(2, f"/pick {self.key}", is_bot=True),
            self.update(3, f"/pick@other_bot {self.key}"),
            self.update(4, f"/pick@test_bot {self.key}"),
        ]
        self.assertEqual(process_commands(self.client, self.private, self.history, NOW), 1)
        self.assertEqual(self.private.data["statuses"][self.key]["status"], "pick")
        self.assertEqual(self.private.data["offset"], 5)
        saved = PrivateState(TOKEN, CHAT, self.path).data
        self.assertNotIn("user", json.dumps(saved))
        self.assertNotIn(CHAT, json.dumps(saved))
        self.client.send.assert_called_once()

    def test_selection_lifecycle_and_replayed_update_are_idempotent(self):
        self.private.data["offset"] = 1
        for index, status in enumerate(("pick", "hold", "doing", "done", "clear"), 1):
            update = self.update(index, f"/{status} {self.key}")
            self.client.call.return_value = [update]
            self.assertEqual(process_commands(self.client, self.private, self.history, NOW), 1)
            self.assertEqual(self.private.data["statuses"][self.key]["status"], status)
            self.assertEqual(process_commands(self.client, self.private, self.history, NOW), 0)

    def test_queue_keeps_selected_material_after_public_history_expires(self):
        self.private.data["offset"] = 1
        self.client.call.return_value = [self.update(1, f"/pick {self.key}")]
        process_commands(self.client, self.private, self.history, NOW)
        self.client.send.reset_mock()
        self.client.call.return_value = [self.update(2, "/queue")]
        process_commands(self.client, self.private, EMPTY, NOW)
        self.assertIn(self.history["items"][self.key]["title"], self.client.send.call_args.args[0])

    def test_malformed_selection_id_gets_help_instead_of_changing_state(self):
        self.private.data["offset"] = 1
        self.client.call.return_value = [self.update(1, "/pick wrong-id")]
        self.assertEqual(process_commands(self.client, self.private, self.history, NOW), 1)
        self.assertEqual(self.private.data["statuses"], {})
        self.assertIn("12자리", self.client.send.call_args.args[0])

    def test_queue_does_not_send_draft_status_to_other_groups(self):
        self.private.data["offset"] = 1
        self.client.call.return_value = [self.update(1, "/queue", chat="-999")]
        process_commands(self.client, self.private, self.history, NOW)
        self.client.send.assert_not_called()

    def test_failed_acknowledgement_does_not_reapply_command(self):
        self.private.data["offset"] = 1
        self.client.call.return_value = [self.update(1, f"/pick {self.key}")]
        self.client.send.side_effect = TelegramError("synthetic")
        with self.assertRaises(TelegramError):
            process_commands(self.client, self.private, self.history, NOW)
        self.private = PrivateState(TOKEN, CHAT, self.path)
        self.assertEqual(self.private.data["offset"], 2)
        self.assertEqual(process_commands(self.client, self.private, self.history, NOW), 0)

    def test_partial_report_resumes_only_unsent_parts_and_completed_report_is_not_resent(self):
        self.client.send.side_effect = [10, TelegramError("synthetic")]
        with self.assertRaises(TelegramError):
            deliver_report(self.client, ["one", "two"], self.private, "hourly", NOW)
        self.client.send.reset_mock(side_effect=True)
        self.client.send.return_value = 11
        self.private = PrivateState(TOKEN, CHAT, self.path)
        self.assertEqual(deliver_report(self.client, ["changed"], self.private, "hourly", NOW), 1)
        self.client.send.assert_called_once_with("two")
        self.assertEqual(deliver_report(self.client, ["changed"], self.private, "hourly", NOW), 0)
        self.assertNotIn("parts", self.private.data["reports"]["hourly"])

    def test_uncertain_network_delivery_is_not_automatically_replayed(self):
        self.client.send.side_effect = DeliveryUncertain("synthetic")
        with self.assertRaises(DeliveryUncertain):
            deliver_report(self.client, ["one"], self.private, "hourly", NOW)
        with self.assertRaises(DeliveryUncertain):
            deliver_report(self.client, ["one"], self.private, "hourly", NOW)
        self.assertEqual(self.client.send.call_count, 1)

    def test_http_200_with_api_error_is_not_success_and_errors_never_include_token(self):
        session = Mock()
        session.post.return_value = Mock(status_code=200, json=Mock(return_value={"ok": False, "error_code": 400}))
        client = TelegramClient(TOKEN, CHAT, session=session)
        with self.assertRaises(TelegramError) as error:
            client.send("test")
        self.assertNotIn(TOKEN, str(error.exception))
        session.post.side_effect = requests.Timeout("https://api.telegram.org/bot" + TOKEN)
        with self.assertRaises(DeliveryUncertain) as error:
            client.send("test")
        self.assertNotIn(TOKEN, str(error.exception))

    def test_wrong_configured_target_is_rejected_before_api_call(self):
        session = Mock()
        with self.assertRaises(TelegramError):
            TelegramClient(TOKEN, CHAT, expected_hash="wrong", session=session)
        session.post.assert_not_called()

    def test_rate_limit_retry_uses_telegram_retry_after(self):
        session = Mock()
        session.post.side_effect = [
            Mock(status_code=429, json=Mock(return_value={"ok": False, "error_code": 429, "parameters": {"retry_after": 1}})),
            Mock(status_code=200, json=Mock(return_value={"ok": True, "result": {"message_id": 1, "chat": {"id": int(CHAT)}}})),
        ]
        client = TelegramClient(TOKEN, CHAT, session=session)
        with patch("telegram_editor.time.sleep") as sleep:
            self.assertEqual(client.send("test"), 1)
        sleep.assert_called_once_with(1.2)


if __name__ == "__main__":
    unittest.main()
