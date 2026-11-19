import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import candidate_snapshot as snapshot
import editorial_cycle as cycle
import editorial_progress as progress
from report_timing import KST, hourly_key
from test_curated_report import pick, edition


def at(hour, minute=0):
    return int(datetime(2026, 10, 19, hour, minute, tzinfo=KST).timestamp())


class DailyMorningResearchTests(unittest.TestCase):
    def test_before_0900_prepares_only_that_morning_without_authorizing_early_send(self):
        result = cycle.plan_cycle(at(8, 25))
        self.assertEqual(result["phase"], "research")
        self.assertEqual(result["target_epoch"], at(9))
        self.assertFalse(result["may_submit"])

    def test_five_minute_preparation_and_current_hour_recovery(self):
        self.assertEqual(cycle.plan_cycle(at(8,55))["phase"],"prepare")
        result=cycle.plan_cycle(at(9,45))
        self.assertEqual((result["phase"],result["target_epoch"],result["may_submit"]),
                         ("report",at(9),True))

    def test_sent_report_completes_day_without_another_research_slot(self):
        target=at(9)
        state={"updated_at":target+30,"report":{"hour_utc":hourly_key(target)[7:],
               "delivery":"sent","stories":10,"messages":1}}
        result=cycle.plan_cycle(at(9,25),state=state)
        self.assertEqual(result["phase"],"day_complete")
        self.assertIsNone(result["target_epoch"])
        self.assertFalse(result["may_submit"])

    def test_uncertain_or_partial_delivery_never_becomes_a_new_request(self):
        target=at(9);hour=hourly_key(target)[7:]
        for status in ({"hour_utc":hour,"status":"delivery_uncertain"},{}):
            state={"updated_at":target+1,"report":{"hour_utc":hour,
                   "delivery":"sent","stories":4,"messages":1}}
            result=cycle.plan_cycle(at(9,25),state=state,status=status)
            self.assertIsNone(result["target_epoch"])
            self.assertFalse(result["may_submit"])

    def test_existing_pinned_request_is_only_observed(self):
        request={"hour_utc":hourly_key(at(9))[7:]}
        result=cycle.plan_cycle(at(8,55),request=request)
        self.assertEqual(result["phase"],"await_delivery")
        self.assertIsNone(result["target_epoch"])
        self.assertEqual(result["locked_reports"][0]["reason"],"request_exists_do_not_reissue")

    def test_all_other_hours_are_off_and_no_old_slot_is_replayed(self):
        for hour in (0,1,7,10,11,14,17,20,21,23):
            self.assertEqual(cycle.plan_cycle(at(hour))["phase"],"off_hours")
        self.assertEqual(cycle.plan_cycle(at(8))["target_epoch"],at(9))
        result=cycle.plan_cycle(at(9,25),request={"hour_utc":hourly_key(at(9))[7:]})
        self.assertEqual((result["phase"],result["target_epoch"],result["may_submit"]),
                         ("await_delivery",None,False))

    def test_old_or_failed_pool_cannot_be_presented_as_live_collection(self):
        now = at(8, 25)
        for data in ({}, {"generated_at": now - 5 * 3600, "status": "ok"},
                     {"generated_at": now + 1, "status": "ok"},
                     {"generated_at": now, "status": "unavailable"}):
            self.assertTrue(cycle.plan_cycle(now, candidates=data)["discovery_refresh_needed"])
        self.assertFalse(cycle.plan_cycle(now, candidates={"generated_at": now - 600,
                                                         "status": "degraded"})["discovery_refresh_needed"])

    def test_early_working_review_is_saved_but_future_delivery_gate_stays_closed(self):
        now, target = at(8, 25), at(9)
        p = pick()
        p.update(verified_at=now - 120, published_at=now - 180)
        p["readiness"] = {"mode": "major_news", "event_date": "2026-10-19",
                          "observation": "공식 발표에서 적용 대상과 확정된 변경을 확인했다.",
                          "checked_materials": [], "outline": ["적용 대상을 표시한다.", "확정된 변화를 설명한다."]}
        value = edition([p], hour=hourly_key(now // 3600 * 3600)[7:])
        value.update(version=2, generated_at=now)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.json"
            path.write_text(json.dumps(value, ensure_ascii=False))
            checked = progress.load_research_review(path, target, now)
            self.assertEqual(checked["picks"][0]["verified_at"], now - 120)
            attempt = progress.save_progress(Path(tmp) / "progress.json", hourly_key(target)[7:],
                                             now, {}, edition=checked)
            self.assertEqual((attempt["ready"], attempt["missing"]), (1, 9))
            with self.assertRaises(ValueError):
                progress.load_edition(path, target, now)
            with self.assertRaises(ValueError):
                progress.load_research_review(path, target, now + 76 * 60)

    def test_push_checkpoint_does_not_repeat_an_already_fresh_collection(self):
        now = at(8, 25)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.json"
            path.write_text(json.dumps({"generated_at": now - 120, "status": "degraded", "fresh_count": 10}))
            with patch.object(snapshot, "SNAPSHOT_FILE", path), \
                    patch.object(snapshot.time, "time", return_value=now), \
                    patch.object(snapshot, "collect") as collect, patch.object(snapshot, "atomic_json") as write:
                self.assertEqual(snapshot.run(480), 0)
                collect.assert_not_called()
                write.assert_not_called()

    def test_recent_failed_refresh_is_retried_without_promoting_retained_items(self):
        now = at(8, 25)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.json"
            path.write_text(json.dumps({"generated_at": now - 60, "status": "unavailable",
                                       "fresh_count": 0, "items": []}))
            with patch.object(snapshot, "SNAPSHOT_FILE", path), \
                    patch.object(snapshot.time, "time", return_value=now), \
                    patch.object(snapshot, "load_history", return_value={"version": 1, "items": {}}), \
                    patch.object(snapshot, "collect", return_value=({}, {"source": "HTTP 403"})) as collect, \
                    patch.object(snapshot, "fetch_public_videos", return_value=[]), \
                    patch.object(snapshot, "enrich"), patch.object(snapshot, "atomic_json"):
                self.assertEqual(snapshot.run(480), 1)
                collect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
