import unittest
from quick_scan import inbox

NOW = 1792764000


class QuickScanTests(unittest.TestCase):
    def row(self, title, suffix, **fields):
        return dict(title=title, link="https://example.org/" + suffix, observed_at=NOW, **fields)

    def test_bounded_shortlist_and_reserves_do_not_claim_verification(self):
        rows = [self.row(title + str(i), str(i)) for i, title in enumerate(
            ["축구 실수", "에스파 자막", "황당한 사건"] * 20)]
        result = inbox({"items": rows}, NOW)
        self.assertEqual(len(result["candidates"]), 20)
        self.assertEqual(len(result["reserves"]), 10)
        self.assertEqual(result["budget"]["recommendations_target"], 10)
        self.assertEqual({r["lane"] for r in result["candidates"]}, {"football", "idol", "community"})
        self.assertTrue(all(not r["video_viewed"] and r["published_metadata"] is None
                            for r in result["candidates"]))

    def test_known_old_publication_is_not_refreshed_by_a_new_observation(self):
        rows = [self.row("축구 실수", "old", video_published_at=NOW - 13 * 3600),
                dict(self.row("에스파 자막", "future"), observed_at=NOW + 1),
                self.row("황당한 사건", "listed", listed_at=NOW - 13 * 3600),
                self.row("아이브 자막", "source", source_published_at=NOW - 13 * 3600),
                self.row("아이브 실수", "missing-source", source_published_at=None, video_published_at=NOW - 13 * 3600)]
        self.assertEqual(inbox({"items": rows}, NOW)["candidates"], [])

    def test_specific_action_beats_generic_official_video_and_promo(self):
        rows = [self.row("아이브 Concept Photo", "promo", source_role="original"),
                self.row("토트넘 훈련", "training", source_role="original"),
                self.row("인천공항 빵 봉지에 불 시민이 소화기로 진화", "fire"),
                self.row("월급 50% 지급 선수협 항의", "salary")]
        result = inbox({"items": rows}, NOW)["candidates"]
        self.assertEqual([r["url"].rsplit("/", 1)[-1] for r in result], ["fire", "salary", "training"])

    def test_original_wins_for_equally_specific_leads_without_domain_trust(self):
        rows = [dict(self.row("여돌 농담 1", "reupload"), link="https://www.youtube.com/watch?v=abcdefghijk"),
                self.row("여돌 농담 2", "official", source_role="original")]
        result = inbox({"items": rows}, NOW)["candidates"]
        self.assertTrue(result[0]["url"].endswith("/official"))
        self.assertEqual(result[0]["source_role"], "original")
        self.assertEqual(result[1]["source_role"], "lead")

    def test_same_title_across_reposts_has_only_one_research_slot(self):
        rows = [self.row("아이브 자막 변경!", "first"), self.row("아이브 자막 변경", "repost")]
        self.assertEqual(len(inbox({"items": rows}, NOW)["candidates"]), 1)

    def test_research_lanes_are_not_forced_publication_quotas(self):
        rows = [self.row("황당한 재입사 적발 " + str(i), str(i)) for i in range(25)]
        result = inbox({"items": rows}, NOW)
        self.assertEqual(len(result["candidates"]), 20)
        self.assertEqual({r["lane"] for r in result["candidates"]}, {"community"})
