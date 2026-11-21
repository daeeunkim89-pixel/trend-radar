import unittest
from quick_scan import inbox
NOW = 1792764000

class QuickScanTests(unittest.TestCase):
    def row(self, title, suffix, **fields):
        return dict(title=title, link="https://example.org/" + suffix, observed_at=NOW, **fields)

    def test_concrete_football_story_is_discovered_before_generic_awards(self):
        rows = [self.row("축구 월드컵 우승 확정", "result"),
                self.row("흐비차, 부상 중 트위치 스트리머로 전환", "action"),
                self.row("전국 통신망 대규모 마비", "public"),
                self.row("국내 배구팀 1라운드 우승 기록", "sport")]
        out = inbox({"items": rows}, NOW)
        self.assertEqual([r["url"].rsplit("/",1)[-1] for r in out["candidates"]],
                         ["action","result","public","sport"])
        self.assertFalse(out["budget"]["extend_until_target"])
        self.assertEqual(out["budget"]["recommendations_target"],10)

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

    def test_daily_queue_keeps_yesterday_daytime_without_refreshing_publication(self):
        for key in ("source_published_at","video_published_at","listed_at"):
            row=self.row("축구 선수의 새 인터뷰",key,**{key:NOW-20*3600})
            result=inbox({"items":[row]},NOW)
            self.assertEqual(result["candidates"][0]["published_metadata"],NOW-20*3600)
            self.assertEqual(result["budget"]["initial_freshness_hours"],24)
            self.assertEqual(result["extended_candidates"],[])
            row[key]=NOW-24*3600-1
            self.assertEqual(inbox({"items":[row]},NOW)["candidates"],[])

    def test_btp_football_subjects_are_not_lost_as_general_news(self):
        from quick_scan import lane
        for title in ("흐비차 근황","호날두 엄마의 불만","호나우지뉴 볼 터치",
                      "모리야스의 고별전","안첼로티의 인터뷰","박항서 징계","오현규 이적 보도"):
            self.assertEqual(lane(self.row(title,title)),"football")
        self.assertEqual(lane(self.row("생소한 선수의 이야기","metadata",list_category="해외축구")),"football")

    def test_community_index_is_not_claimed_as_early_discovery_or_popularity_proof(self):
        row=self.row("호날두 어머니의 인터뷰","indexed",origin="펨코",source="펨코 간접",
                     discovery_observed_at=NOW-600,discovery_timestamp_kind="post_listed")
        item=inbox({"items":[row]},NOW)["candidates"][0]
        self.assertTrue(item["already_in_fmkorea_index"])
        self.assertEqual(item["discovery_observed_at"],NOW-600)
        self.assertFalse(item["video_viewed"])
        self.assertNotIn("predicted_views",item)
        self.assertNotIn("preemptive",item)

    def test_future_and_older_than_two_days_are_excluded(self):
        rows = [dict(self.row("축구 우승", "future"), observed_at=NOW+1),
                self.row("축구 우승", "old", source_published_at=NOW-49*3600)]
        result = inbox({"items": rows}, NOW)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["extended_candidates"], [])

    def test_shortfall_recovery_is_one_bounded_round_for_missing_stories(self):
        budget = inbox({}, NOW)["budget"]
        self.assertEqual((budget["shortfall_recovery_searches"], budget["shortfall_recovery_opens"], budget["max_shortfall_recoveries"]), (4, 12, 1))
        self.assertEqual((budget["max_total_searches"], budget["max_total_opens"]), (14, 44))
        self.assertFalse(budget["extend_until_target"])
        self.assertTrue(budget["stop_when_target_ready"])
