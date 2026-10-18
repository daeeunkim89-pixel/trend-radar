import unittest
from sports_video import parse_videos

NOW = 1792348200

class PublicSportsVideoTests(unittest.TestCase):
    def row(self, **changes):
        return {"sportsVideoId": 1545893, "upperSectionId": "kfootball", "title": "막판 역전 장면 공개",
                "produceDateTime": "2026-10-18T21:01:04", "naverTvChannel": {"channelName": "SBS뉴스"}, **changes}

    def parse(self, rows):
        return parse_videos({"code": 200, "result": {"videos": rows}}, NOW)

    def test_public_metadata_retains_provider_and_never_claims_the_video_was_viewed(self):
        result = self.parse([self.row()])[0]
        self.assertEqual(result["link"], "https://m.sports.naver.com/kfootball/video/1545893")
        self.assertEqual(result["video_provider"], "SBS뉴스")
        self.assertFalse(result["video_viewed"])
        self.assertIsNone(result["views"])
        self.assertNotIn("verified_at", result)

    def test_old_unknown_date_future_and_unknown_sections_do_not_look_fresh(self):
        rows = [self.row(produceDateTime="2026-10-15T22:00:00"), self.row(produceDateTime="bad"),
                self.row(produceDateTime="2026-10-20T22:00:00"), self.row(upperSectionId="../accounts"),
                self.row(sportsVideoId=True)]
        self.assertEqual(self.parse(rows), [])

    def test_duplicate_video_does_not_fill_multiple_candidate_slots(self):
        self.assertEqual(len(self.parse([self.row(), self.row()])), 1)

    def test_upstream_failure_is_not_an_empty_success(self):
        for value in ({"code": 503}, {"code": 200, "result": {}}, {"code": 200, "result": []}, []):
            with self.assertRaises(ValueError):
                parse_videos(value, NOW)
