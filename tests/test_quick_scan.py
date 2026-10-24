import unittest
from quick_scan import inbox

NOW = 1792764000
class QuickScanTests(unittest.TestCase):
    def test_bounded_diverse_shortlist_does_not_claim_verification(self):
        rows = [{"title": t, "link": f"https://example.org/{i}", "observed_at": NOW}
                for i, t in enumerate(["축구 실수", "에스파 자막", "황당한 사건"] * 20)]
        result = inbox({"items": rows}, NOW)
        self.assertEqual(len(result["candidates"]), 20)
        self.assertEqual(result["budget"]["recommendations_target"], 10)
        self.assertEqual({r["lane"] for r in result["candidates"]}, {"football", "idol", "community"})
        self.assertTrue(all(not r["video_viewed"] and r["published_metadata"] is None for r in result["candidates"]))

    def test_old_video_and_future_observation_are_not_new_candidates(self):
        rows = [{"title": "축구 실수", "link": "https://example.org/old", "observed_at": NOW,
                 "video_published_at": NOW - 13 * 3600},
                {"title": "에스파 자막", "link": "https://example.org/future", "observed_at": NOW + 1}]
        self.assertEqual(inbox({"items": rows}, NOW)["candidates"], [])
