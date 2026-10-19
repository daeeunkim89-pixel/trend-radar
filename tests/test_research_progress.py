import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import candidate_snapshot as snapshot
import editorial_progress as progress

NOW = 1792375200


def candidate(number, observed=NOW, **extra):
    return dict(source="공개 목록", title=f"검토할 후보 {number}",
                link=f"https://example.org/posts/{number}", observed_at=observed, rank=number, **extra)


def note(number=1, status="needs_visual"):
    return {"event_key": f"event-{number}", "url": f"https://example.org/posts/{number}",
            "title": f"검토할 후보 {number}", "category": "축구", "status": status,
            "note": "공식 경기일은 확인했지만 핵심 장면은 아직 못 봄", "next_action": "원본 영상의 동작과 결과 확인"}


class ResearchContinuityTests(unittest.TestCase):
    def test_dropped_list_entry_survives_without_becoming_fresh_or_viewed(self):
        old = candidate(1, NOW - 3600, video_viewed=False)
        pool = snapshot.merge_pool({"items": [old]}, [candidate(2)], NOW)
        retained = next(row for row in pool if row["rank"] == 1)
        self.assertEqual(retained["observed_at"], NOW - 3600)
        self.assertEqual(retained["first_seen_at"], NOW - 3600)
        self.assertFalse(retained["video_viewed"])
        self.assertEqual(len(pool), 2)

    def test_repeat_canonical_url_keeps_first_seen_and_latest_metrics(self):
        old = candidate(1, NOW - 300, first_seen_at=NOW - 7200, views=30)
        current = candidate(1, views=50)
        current["link"] += "?utm_source=elsewhere"
        pool = snapshot.merge_pool({"items": [old]}, [current], NOW)
        self.assertEqual(len(pool), 1)
        self.assertEqual((pool[0]["first_seen_at"], pool[0]["observed_at"], pool[0]["views"]),
                         (NOW - 7200, NOW, 50))

    def test_retention_and_size_bound_keep_recent_rows(self):
        old = [candidate(1, NOW - snapshot.POOL_RETENTION - 1), candidate(2, NOW + 1)]
        with patch.object(snapshot, "POOL_LIMIT", 2):
            pool = snapshot.merge_pool({"items": old}, [candidate(n, NOW - n) for n in (3, 4, 5)], NOW)
        self.assertEqual([r["rank"] for r in pool], [3, 4])

    def test_total_refresh_failure_preserves_pool_but_remains_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            pool_path = Path(tmp) / "candidates.json"
            pool_path.write_text(json.dumps({"items": [candidate(1, NOW - 1800)]}))
            with patch.object(snapshot, "SNAPSHOT_FILE", pool_path), \
                    patch.object(snapshot, "load_history", return_value={"version": 1, "items": {}}) as history, \
                    patch.object(snapshot, "collect", return_value=({}, {"source": "HTTP 403"})), \
                    patch.object(snapshot, "fetch_public_videos", return_value=[]), \
                    patch.object(snapshot, "enrich"), patch.object(snapshot, "atomic_json") as write, \
                    patch.object(snapshot.time, "time", return_value=NOW):
                self.assertEqual(snapshot.run(), 1)
                history.assert_called_once_with(snapshot.DISCOVERY_HISTORY_FILE)
                value = next(call.args[1] for call in write.call_args_list if call.args[0] == pool_path)
                self.assertEqual((value["status"], value["fresh_count"], value["retained_count"]), ("unavailable", 0, 1))

    def test_only_sent_or_uncertain_history_excludes_a_discovered_candidate(self):
        history = {"editions": [{"delivery": delivery, "at": NOW, "picks":
                    [{"event_key": f"event-{i}", "url": f"https://example.org/posts/{i}"}]} for i, delivery in
                    ((1, "sent"), (2, "uncertain"), (3, "collected"))]}
        result = progress.summarize({"items": [candidate(i) for i in (1, 2, 3, 4)]}, {}, history, NOW)
        self.assertEqual(result["unreviewed_count"], 2)
        self.assertEqual([r["title"] for r in result["unreviewed_sample"]], ["검토할 후보 3", "검토할 후보 4"])

    def test_incomplete_work_is_saved_without_claiming_delivery_or_updating_pick_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.json"
            attempt = progress.save_progress(path, "2026101902", NOW, {}, [note()])
            saved = json.loads(path.read_text())
            self.assertEqual((attempt["status"], attempt["ready"], attempt["missing"], attempt["unfinished"]),
                             ("research_incomplete", 0, 10, 1))
            self.assertEqual(saved["items"][0]["next_action"], note()["next_action"])
            self.assertNotIn("pick", saved["items"][0])
            with self.assertRaises(ValueError):
                progress.save_progress(path, "2026101902", NOW, {}, stage="submitted")
            with self.assertRaises(ValueError):
                progress.save_progress(path, "2026101902", NOW, {}, [dict(note(), status="reviewed")])

    def test_expired_review_is_resumed_but_never_made_ready_by_saving_again(self):
        reviewed = dict(note(), status="reviewed", recorded_at=NOW,
                        pick={"verified_at": NOW - progress.REVIEW_TTL - 1})
        original = copy.deepcopy(reviewed)
        result = progress.summarize({"items": []}, {"items": [reviewed]}, {}, NOW)
        self.assertEqual(result["reviewed_available"], 0)
        self.assertEqual(result["resume"][0]["status"], "needs_recheck")
        self.assertEqual(reviewed, original)

    def test_completed_reviews_and_held_work_survive_the_next_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.json"
            edition = {"version": 2, "coverage": {"opened_urls": ["https://example.org/posts/2"]},
                       "picks": [{"event_key": "event-2", "url": "https://example.org/posts/2", "title": "확인 완료 후보",
                                  "category": "아이돌", "verified_at": NOW - 30}]}
            progress.save_progress(path, "2026101902", NOW, {}, [note()], edition)
            attempt = progress.save_progress(path, "2026101905", NOW + 60, {}, [note(3, "needs_date")])
            saved = json.loads(path.read_text())
            self.assertEqual((attempt["ready"], attempt["missing"], attempt["unfinished"]), (1, 9, 2))
            self.assertEqual(next(r["pick"]["verified_at"] for r in saved["items"] if r["status"] == "reviewed"), NOW - 30)
            self.assertEqual(len(saved["attempts"]), 2)


if __name__ == "__main__":
    unittest.main()
