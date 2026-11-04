import unittest
from quick_scan import inbox
NOW = 1792764000

class QuickScanTests(unittest.TestCase):
    def row(self, title, suffix, **fields):
        return dict(title=title, link="https://example.org/" + suffix, observed_at=NOW, **fields)

    def test_sports_major_news_precedes_small_incidents_and_fan_banter(self):
        rows = [self.row("황당한 도로 시비 벌금", "minor"),
                self.row("토트넘 훈련 중 농담", "banter"),
                self.row("전국 통신망 대규모 마비", "public"),
                self.row("축구 월드컵 우승 확정", "sport")]
        out = inbox({"items": rows}, NOW)
        self.assertEqual([r["url"].rsplit("/", 1)[-1] for r in out["candidates"]],
                         ["sport", "public", "banter", "minor"])
        self.assertEqual(out["budget"]["recommendations_target"], 5)
        self.assertTrue(out["budget"]["extend_until_target"])

    def test_entertainment_details_are_excluded_and_major_public_issue_stays_a_lead(self):
        rows = [self.row("아이브 자막 반전", "subtitles"),
                self.row("에스파 화보 공개", "photo"),
                self.row("유명 배우 예능 농담", "show", source="네이트 연예"),
                self.row("엔터 산업 대규모 임금 체불 정부 조사", "major", source="네이트 연예")]
        result = inbox({"items": rows}, NOW)["candidates"]
        self.assertEqual([r["url"].rsplit("/", 1)[-1] for r in result], ["major"])
        self.assertEqual(result[0]["lane"], "current_affairs")
        self.assertFalse(result[0]["video_viewed"])

    def test_original_only_wins_ties_without_inventing_ownership(self):
        rows = [dict(self.row("축구 월드컵 우승 확정", "repost"), link="https://www.youtube.com/watch?v=abcdefghijk"),
                self.row("축구 월드컵 우승 확정 발표", "official", source_role="original")]
        result = inbox({"items": rows}, NOW)["candidates"]
        self.assertTrue(result[0]["url"].endswith("/official"))
        self.assertEqual(result[1]["source_role"], "lead")

    def test_shortlist_is_bounded_without_claiming_verification(self):
        rows = [self.row("축구 우승 확정 " + str(i), str(i)) for i in range(60)]
        result = inbox({"items": rows}, NOW)
        self.assertEqual((len(result["candidates"]), len(result["reserves"])), (20, 10))
        self.assertTrue(all(not r["video_viewed"] and r["published_metadata"] is None for r in result["candidates"]))

    def test_same_title_reposts_only_take_one_slot(self):
        rows = [self.row("축구 우승 확정!", "first"), self.row("축구 우승 확정", "repost")]
        self.assertEqual(len(inbox({"items": rows}, NOW)["candidates"]), 1)

    def test_known_old_publication_never_becomes_new_on_observation(self):
        for key in ("source_published_at", "video_published_at", "listed_at"):
            row = self.row("축구 월드컵 우승 확정", key, **{key: NOW-13*3600})
            result = inbox({"items": [row]}, NOW)
            self.assertEqual(result["candidates"], [])
            self.assertEqual(result["extended_candidates"][0]["published_metadata"], NOW-13*3600)

    def test_future_and_older_than_two_days_are_excluded(self):
        rows = [dict(self.row("축구 우승", "future"), observed_at=NOW+1),
                self.row("축구 우승", "old", source_published_at=NOW-49*3600)]
        result = inbox({"items": rows}, NOW)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["extended_candidates"], [])
