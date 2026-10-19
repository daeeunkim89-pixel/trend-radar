import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import candidate_snapshot
import curated_report as c
import editorial as e
import report_request
from report_timing import hourly_key, prepared_target
from telegram_editor import DeliveryUncertain, PrivateState, story_content_keys

NOW = 1792235100
HOUR = NOW // 3600 * 3600
HOUR_TEXT = hourly_key(HOUR).removeprefix("hourly-")
EMPTY = {"version": 1, "items": {}}


def pick(number=1):
    url = f"https://example.org/story/{number}"
    return {"title": f"선수의 뜻밖의 행동과 확인된 변화 {number}", "category": "축구", "url": url,
            "source": "공개 원문", "kind": "community", "event_key": f"confirmed-event-{number}",
            "why": "경기 결과보다 예상과 다른 행동이 한 장면으로 드러난다.",
            "angle": "선수의 행동과 상대 반응을 순서대로 배치한다.",
            "why_now": "이번 시간 원문에서 공개된 장면을 확인했다.", "verified_at": NOW,
            "published_at": NOW - 120, "evidence": [{"url": url, "note": "본문에서 행동과 반응 확인"}],
            "materials": [{"url": url, "kind": "source", "label": "원문 자료"}], "caution": ""}


def edition(picks=None, hour=HOUR_TEXT):
    picks = [pick()] if picks is None else picks
    return {"version": 1, "hour_utc": hour, "reviewer": "ChatGPT", "generated_at": NOW,
            "coverage": {"queries": ["축구 장면", "아이돌 팬 반응", "시사 영향", "스포츠 주요 소식"],
                         "opened_urls": list({p["url"] for p in picks}), "unavailable": []},
            "picks": picks, "empty_reason": "새로 추천할 만큼 확인된 소재가 없었다." if not picks else ""}


class EditorialEditionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory / "picks.json"

    def write(self, value):
        self.path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def test_agent_judgment_survives_old_keyword_gate_and_renders_actionable_first_pick(self):
        value = edition([pick(1), pick(2)])
        self.write(value)
        reviewed = c.load_edition(self.path, HOUR, NOW)
        stories, history = c.build_stories(reviewed, EMPTY, NOW)
        self.assertEqual([s["lead"]["title"] for s in stories], [p["title"] for p in value["picks"]])
        self.assertIsNone(__import__("selection").qualify(stories[0]))
        message = c.render_edition(stories, HOUR, "")[0]
        self.assertIn("🔥 지금 1순위", message)
        for p in value["picks"]:
            self.assertIn(p["why"], message)
            self.assertIn(p["angle"], message)
            self.assertIn(p["url"], message)
        self.assertLess(e.message_units(message), 3900)
        self.assertEqual(len(history["items"]), 2)
        record = history["items"][stories[0]["lead"]["item_id"]]
        info = e.render_info(record, stories[0]["id"])
        self.assertIn(value["picks"][0]["why_now"], info)
        self.assertIn("확인 출처", info)

    def test_wrong_hour_stale_review_and_early_preparation_are_rejected(self):
        for value, target, now in ((edition(hour="2026101710"), HOUR, NOW),
                                   (edition(), HOUR, NOW + 75 * 60 + 1),
                                   (edition(hour=hourly_key(HOUR + 7200)[7:]), HOUR + 7200, NOW)):
            with self.subTest(target=target, now=now):
                self.write(value)
                with self.assertRaises(ValueError):
                    c.load_edition(self.path, target, now)

    def production_edition(self, mode="scene"):
        value = edition()
        value["version"] = 2
        p = value["picks"][0]
        p["materials"][0]["kind"] = "image" if mode == "scene" else "source"
        p["readiness"] = {"mode": mode, "event_date": "2026-10-17",
                          "observation": "선수가 세리머니를 끝내기 전에 주심이 경고 카드를 꺼낸 화면을 확인했다.",
                          "checked_materials": [p["url"]] if mode == "scene" else [],
                          "outline": ["첫 장에 세리머니와 경고를 나란히 놓는다.", "다음 장에 경기 상황과 판정 결과를 설명한다."]}
        return value

    def test_production_review_retains_observed_scene_date_and_concrete_outline(self):
        value = self.production_edition()
        self.write(value)
        reviewed = c.load_edition(self.path, HOUR, NOW)
        stories, history = c.build_stories(reviewed, EMPTY, NOW)
        record = history["items"][stories[0]["lead"]["item_id"]]
        info = e.render_info(record, stories[0]["id"])
        self.assertIn("사건·새 발표 날짜: 2026-10-17", info)
        self.assertIn(value["picks"][0]["readiness"]["observation"], info)
        self.assertIn(value["picks"][0]["readiness"]["outline"][1], info)

    def test_uninspected_scene_cannot_pass_as_ready_via_a_source_link(self):
        bad = []
        value = self.production_edition(); value["picks"][0]["readiness"]["checked_materials"] = []; bad.append(value)
        value = self.production_edition(); value["picks"][0]["materials"][0]["kind"] = "source"; bad.append(value)
        value = self.production_edition(); value["picks"][0]["readiness"]["checked_materials"] = ["https://other.example/unseen.jpg"]; bad.append(value)
        value = self.production_edition(); del value["picks"][0]["readiness"]; bad.append(value)
        value = self.production_edition(); value["picks"][0]["readiness"]["event_date"] = "2026-10-18"; bad.append(value)
        value = self.production_edition(); value["picks"][0]["readiness"]["outline"] = ["한 장만"]; bad.append(value)
        for value in bad:
            with self.subTest(pick=value["picks"][0]):
                self.write(value)
                with self.assertRaises(ValueError):
                    c.load_edition(self.path, HOUR, NOW)

    def test_confirmed_major_news_can_use_a_fact_card_without_claiming_video_review(self):
        value = self.production_edition("major_news")
        value["picks"][0]["readiness"]["observation"] = "공식 발표에서 적용 대상과 시행일을 확인했다. 영향을 받는 범위를 첫 장의 숫자로 설명한다."
        self.write(value)
        reviewed = c.load_edition(self.path, HOUR, NOW)
        self.assertEqual(reviewed["picks"][0]["readiness"]["checked_materials"], [])

    def test_production_info_over_telegram_limit_is_rejected_before_transport(self):
        value = self.production_edition()
        p = value["picks"][0]
        p.update(title="🔥" * 90, why="🔥" * 180, angle="🔥" * 150, why_now="🔥" * 180, caution="🔥" * 150)
        p["evidence"] *= 3
        for evidence in p["evidence"]:
            evidence["note"] = "🔥" * 220
        p["readiness"].update(observation="🔥" * 240, outline=["🔥" * 120] * 4)
        self.write(value)
        with self.assertRaisesRegex(ValueError, "single-message"):
            c.load_edition(self.path, HOUR, NOW)

    def test_delivery_job_allows_full_preparation_wait_and_setup(self):
        import re
        target = HOUR + 3600
        earliest = target - 60 * 60
        self.assertEqual(prepared_target(hourly_key(target)[7:], earliest), target)
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/delivery-request.yml").read_text()
        minutes = int(re.search(r"timeout-minutes:\s*(\d+)", workflow).group(1))
        self.assertGreaterEqual(minutes * 60, target - earliest + 5 * 60)

    def test_missing_evidence_unopened_material_and_same_event_are_not_accepted(self):
        bad = []
        value = edition(); value["picks"][0]["evidence"] = []; bad.append(value)
        value = edition(); value["picks"][0]["materials"][0]["url"] = "https://other.example/unchecked"; bad.append(value)
        value = edition([pick(1), pick(2)]); value["picks"][1]["event_key"] = value["picks"][0]["event_key"]; bad.append(value)
        value = edition(); value["picks"][0]["url"] = "http://127.0.0.1/private"; bad.append(value)
        value = edition(); value["coverage"]["queries"] = ["one field only"]; bad.append(value)
        for value in bad:
            self.write(value)
            with self.assertRaises(ValueError):
                c.load_edition(self.path, HOUR, NOW)

    def test_maximum_edition_stays_one_message_and_escapes_html(self):
        value = edition([pick(i) for i in range(10)])
        for number, p in enumerate(value["picks"]):
            p.update(title=f"<b>{number} " + "제" * 75, why="이" * 180, angle="각" * 150, caution="주" * 150)
        self.write(value)
        stories, _ = c.build_stories(c.load_edition(self.path, HOUR, NOW), EMPTY, NOW)
        parts = c.render_edition(stories, HOUR, "")
        self.assertEqual(len(parts), 1)
        self.assertIn("&lt;b&gt;", parts[0])
        self.assertIn("추천 10/10", parts[0])
        self.assertLessEqual(e.message_units(parts[0]), 3900)

    def test_ten_recommendations_with_emoji_fit_and_full_details_survive_compaction(self):
        value = edition([pick(i) for i in range(10)])
        for number, p in enumerate(value["picks"]):
            p.update(title=f"{number} " + "⚽" * 85, why="🔥" * 180, angle="🎬" * 150, caution="❗" * 150)
        stories, history = c.build_stories(value, EMPTY, NOW)
        parts = c.render_edition(stories, HOUR, "")
        self.assertLessEqual(e.message_units(parts[0]), 3900)
        self.assertIn("10/10", parts[0])
        record = history["items"][stories[0]["lead"]["item_id"]]
        self.assertIn(value["picks"][0]["why"], e.render_info(record, stories[0]["id"]))

    def test_reviewed_reserves_fill_ten_slots_after_content_deduplication(self):
        value = edition([pick(i) for i in range(16)])
        self.write(value)
        private = PrivateState("synthetic-token", "-123456", self.directory / "reserves.enc")
        client = Mock(send=Mock(return_value=125))
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private), \
                patch.object(c, "unreported_stories", side_effect=lambda stories, *args: stories[6:]), \
                patch.object(c, "atomic_json") as write, patch.object(c, "wait_for_target", return_value=True):
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 0)
            client.send.assert_called_once()
            saved = [call.args[1] for call in write.call_args_list if call.args[0] == c.STATE_FILE][0]
            self.assertEqual(saved["report"]["stories"], 10)
            self.assertEqual(saved["report"]["duplicates_excluded"], 6)
            self.assertEqual(len(private.data["reports"][hourly_key(HOUR)]["numbers"]), 10)

    def test_short_edition_reports_actual_count_instead_of_claiming_ten(self):
        stories, _ = c.build_stories(edition([pick(1), pick(2)]), EMPTY, NOW)
        message = c.render_edition(stories, HOUR, "핵심 자료를 확인한 새 후보가 부족했습니다.")[0]
        self.assertIn("추천 2/10", message)
        self.assertIn("10개 중 2개 확보", message)
        self.assertNotIn("추천 10/10", message)

    def test_pinned_hash_catches_edits_after_request_and_preview_never_connects(self):
        self.write(edition())
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.path.write_text(self.path.read_text() + " ")
        with self.assertRaises(ValueError):
            c.load_edition(self.path, HOUR, NOW, digest)
        self.write(edition())
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient") as client, patch.object(c, "PrivateState") as private, \
                patch.object(c, "atomic_json") as write:
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path, preview=True), 0)
            client.assert_not_called(); private.assert_not_called(); write.assert_not_called()

    def test_event_identity_blocks_reworded_cross_site_repost_and_shared_material(self):
        p1, p2 = pick(1), pick(2)
        value = edition([p1]); self.write(value)
        old, history = c.build_stories(c.load_edition(self.path, HOUR, NOW), EMPTY, NOW)
        keys = story_content_keys(old[0])
        p2["event_key"] = p1["event_key"]
        new, _ = c.build_stories(edition([p2]), history, NOW + 3600)
        self.assertTrue(keys.intersection(story_content_keys(new[0])))
        p2["event_key"] = "different-event"; p2["materials"] = p1["materials"]
        together, _ = c.build_stories(edition([p1, p2]), EMPTY, NOW)
        self.assertEqual(len(c.same_event_filter(together)), 1)

    def test_actual_delivery_once_then_no_second_send_and_no_mock_counts_as_status(self):
        self.write(edition([pick(i) for i in range(10)]))
        private = PrivateState("synthetic-token", "-123456", self.directory / "editor.enc")
        client = Mock(send=Mock(return_value=123))
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private), \
                patch.object(c, "atomic_json") as write, patch.object(c, "wait_for_target", return_value=True):
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 0)
            client.send.assert_called_once()
            saved = [call.args[1] for call in write.call_args_list if call.args[0] == c.STATE_FILE]
            self.assertEqual(saved[0]["report"]["delivery"], "sent")
            self.assertEqual(saved[0]["report"]["ai"], "chatgpt_web_research")
            self.assertEqual(len(private.data["reports"][hourly_key(HOUR)]["numbers"]), 10)
            self.assertEqual(private.data["reports"][hourly_key(HOUR)]["numbers"]["1"], e.item_id(pick(0)["url"]))
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 0)
            client.send.assert_called_once()

    def test_uncertain_delivery_cannot_be_automatically_retried(self):
        self.write(edition([pick(i) for i in range(10)]))
        private = PrivateState("synthetic-token", "-123456", self.directory / "editor.enc")
        client = Mock(send=Mock(side_effect=DeliveryUncertain("synthetic uncertain result")))
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private), \
                patch.object(c, "atomic_json"), patch.object(c, "wait_for_target", return_value=True):
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 1)
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 1)
            client.send.assert_called_once()

    def test_explicit_on_demand_edition_sends_once_without_reopening_hourly_ledger(self):
        self.write(edition([pick(i) for i in range(10)]))
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        private = PrivateState("synthetic-token", "-123456", self.directory / "manual.enc")
        private.data["reports"][hourly_key(HOUR)] = {"done": True, "message_ids": [100],
                                                   "started_at": NOW, "content_keys": []}
        client = Mock(send=Mock(return_value=124))
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private), \
                patch.object(c, "atomic_json"), patch.object(c, "wait_for_target", return_value=True):
            kwargs = {"recover_hour": HOUR_TEXT, "picks_file": self.path,
                      "expected_sha256": digest, "user_requested": True}
            self.assertEqual(c.main(**kwargs), 0)
            self.assertEqual(c.main(**kwargs), 0)
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 0)
            client.send.assert_called_once()
            self.assertEqual(private.data["reports"][hourly_key(HOUR)]["message_ids"], [100])
            self.assertTrue(private.data["reports"]["user-curated-" + digest]["done"])

    def test_on_demand_request_is_pinned_current_hour_and_preserves_content_deduplication(self):
        self.write(edition([pick(i) for i in range(10)]))
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        request = {"version": 3, "mode": "user_requested", "hour_utc": HOUR_TEXT, "editorial_sha256": digest}
        request_path = self.directory / "manual-request.json"
        request_path.write_text(json.dumps(request))
        sender = Mock(return_value=0)
        self.assertEqual(report_request.run(request_path, NOW, sender, self.path), 0)
        sender.assert_called_once_with(recover_hour=HOUR_TEXT, expected_sha256=digest, user_requested=True)
        sender.reset_mock()
        self.assertEqual(report_request.run(request_path, HOUR + 3600, sender, self.path), 2)
        sender.assert_not_called()
        private = PrivateState("synthetic-token", "-123456", self.directory / "manual.enc")
        client = Mock()
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private), \
                patch.object(c, "unreported_stories", return_value=[]), patch.object(c, "atomic_json"):
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path,
                                    expected_sha256=digest, user_requested=True), 0)
            client.send.assert_not_called()

    def test_underfilled_review_never_opens_transport_or_overwrites_confirmed_send(self):
        for count in (0, 4, 6, 9):
            with self.subTest(count=count):
                self.write(edition([pick(i) for i in range(count)]))
                with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                        patch.object(c, "TelegramClient") as client, patch.object(c, "PrivateState") as private, \
                        patch.object(c, "atomic_json") as write:
                    self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 2)
                    client.assert_not_called(); private.assert_not_called()
                    attempt = [call.args[1] for call in write.call_args_list if call.args[0] == c.ATTEMPT_FILE][0]
                    self.assertEqual(attempt["status"], "insufficient_new_material")
                    self.assertEqual(attempt["ready"], count)
                    self.assertEqual(attempt["missing"], 10 - count)
                    self.assertFalse(any(call.args[0] == c.STATE_FILE for call in write.call_args_list))

    def test_duplicate_filter_shortfall_does_not_reserve_hour_or_send_partial_message(self):
        self.write(edition([pick(i) for i in range(13)]))
        private = PrivateState("synthetic-token", "-123456", self.directory / "shortfall.enc")
        client = Mock()
        with patch.object(c.time, "time", return_value=NOW), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private), \
                patch.object(c, "unreported_stories", side_effect=lambda stories, *args: stories[4:]), \
                patch.object(c, "atomic_json") as write:
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 2)
            client.send.assert_not_called()
            self.assertNotIn(hourly_key(HOUR), private.data["reports"])
            attempt = [call.args[1] for call in write.call_args_list if call.args[0] == c.ATTEMPT_FILE][0]
            self.assertEqual((attempt["ready"], attempt["missing"], attempt["duplicates_excluded"]), (9, 1, 4))
            self.assertFalse(any(call.args[0] == c.STATE_FILE for call in write.call_args_list))

    def test_review_expiring_while_waiting_for_the_hour_cannot_be_sent(self):
        self.write(edition([pick(i) for i in range(10)]))
        private = PrivateState("synthetic-token", "-123456", self.directory / "expired.enc")
        client = Mock()
        clock = Mock(return_value=NOW)
        def wait(target):
            clock.return_value = NOW + 76 * 60
            return True
        with patch.object(c.time, "time", clock), patch.object(c, "load_history", return_value=EMPTY), \
                patch.object(c, "TelegramClient", return_value=client), patch.object(c, "PrivateState", return_value=private), \
                patch.object(c, "atomic_json"), patch.object(c, "wait_for_target", side_effect=wait):
            self.assertEqual(c.main(recover_hour=HOUR_TEXT, picks_file=self.path), 1)
            client.send.assert_not_called()
            self.assertNotIn(hourly_key(HOUR), private.data["reports"])

    def test_discovery_all_sources_empty_remains_a_failure(self):
        with patch.object(candidate_snapshot, "load_history", return_value=EMPTY), \
                patch.object(candidate_snapshot, "fetch_public_videos", return_value=[]), \
                patch.object(candidate_snapshot, "collect", return_value=({"차단 소스": []}, {"차단 소스": "HTTP 430"})), \
                patch.object(candidate_snapshot, "enrich"), patch.object(candidate_snapshot, "atomic_json") as write:
            self.assertEqual(candidate_snapshot.run(), 1)
            snapshot = [call.args[1] for call in write.call_args_list if call.args[0] == candidate_snapshot.SNAPSHOT_FILE][0]
            self.assertEqual(snapshot["status"], "unavailable")
            self.assertIn("차단 소스", snapshot["errors"])

    def test_empty_edition_has_no_junk_filler(self):
        self.write(edition([]))
        reviewed = c.load_edition(self.path, HOUR, NOW)
        parts = c.render_edition([], HOUR, reviewed["empty_reason"])
        self.assertEqual(len(parts), 1)
        self.assertNotIn('<a href="', parts[0])
        self.assertIn("강하게 추천할 새 소재는 없습니다", parts[0])

    def test_prepared_request_is_bound_to_content_and_only_imminent_hour(self):
        target = HOUR + 3600
        self.assertEqual(prepared_target(hourly_key(target)[7:], target - 1200), target)
        for clock in (target - 3601, target + 3600):
            with self.assertRaises(ValueError):
                prepared_target(hourly_key(target)[7:], clock)
        self.write(edition())
        request = {"version": 2, "hour_utc": HOUR_TEXT,
                   "editorial_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest()}
        request_path = self.directory / "request.json"
        request_path.write_text(json.dumps(request))
        sender = Mock(return_value=0)
        self.assertEqual(report_request.run(request_path, NOW, sender, self.path), 0)
        sender.assert_called_once_with(prepared_hour=HOUR_TEXT, expected_sha256=request["editorial_sha256"])
        sender.reset_mock(); self.path.write_text("changed")
        self.assertEqual(report_request.run(request_path, NOW, sender, self.path), 2)
        sender.assert_not_called()

    def test_discovery_refresh_writes_only_public_inputs_and_never_uses_telegram(self):
        row = {"source": "공개 목록", "title": "새로운 경기 장면", "link": "https://example.org/new", "rank": 1,
               "views": None, "reactions": None}
        with patch.object(candidate_snapshot, "load_history", return_value=EMPTY), \
                patch.object(candidate_snapshot, "fetch_public_videos", return_value=[]), \
                patch.object(candidate_snapshot, "collect", return_value=({"공개 목록": [row]}, {"차단 소스": "HTTP 430"})), \
                patch.object(candidate_snapshot, "enrich"), patch.object(candidate_snapshot, "atomic_json") as write, \
                patch("monitor.TelegramClient") as client:
            self.assertEqual(candidate_snapshot.run(), 0)
            self.assertEqual({call.args[0] for call in write.call_args_list}, {candidate_snapshot.DISCOVERY_HISTORY_FILE, candidate_snapshot.SNAPSHOT_FILE})
            snapshot = [call.args[1] for call in write.call_args_list if call.args[0] == candidate_snapshot.SNAPSHOT_FILE][0]
            self.assertEqual(snapshot["status"], "degraded")
            self.assertIn("차단 소스", snapshot["errors"])
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()



