import unittest

import editorial as e
from selection import select_stories
from test_editorial import EMPTY, NOW, row


class IdolRankingTests(unittest.TestCase):
    def assess(self, title):
        item = row(title=title)
        return e.assess({"lead": item, "members": [item]})

    def test_group_aliases_and_distinctive_member_names_are_editorial_candidates(self):
        for title in ("아이브 근황 공개", "IVE interview", "aespa interview",
                      "르세라핌 인터뷰 공개", "아일릿 근황 공개", "블랙핑크 인터뷰",
                      "장원영 취향 공개", "카리나 인터뷰", "여자 아이돌 인터뷰"):
            with self.subTest(title=title):
                result = self.assess(title)
                self.assertIn("여자 아이돌", result["tags"])
                self.assertEqual(result["score"], self.assess("손흥민 인터뷰")["score"])

    def test_ambiguous_names_require_music_context_and_general_words_do_not_match(self):
        for title in ("LIVE 현장 중계", "라이브 방송 중계", "DRIVE 신제품 공개",
                      "윈터 타이어 출시", "지수 급등", "로제 와인 출시",
                      "여자친구와 여행", "외모는 제니인데 리시브는 아쉽네…현대건설 조던"):
            with self.subTest(title=title):
                self.assertNotIn("여자 아이돌", self.assess(title)["tags"])
        for title in ("윈터 신곡 직캠 공개", "제니 무대 공개", "지수 컴백 인터뷰", "있지 신곡 공개"):
            with self.subTest(title=title):
                self.assertIn("여자 아이돌", self.assess(title)["tags"])

    def test_visual_material_gets_priority_without_double_counting_generic_culture(self):
        ordinary = self.assess("블랙핑크 인터뷰")
        visual = self.assess("블랙핑크 챌린지 공개")
        self.assertGreater(visual["score"], ordinary["score"])
        self.assertEqual(visual["score"], self.assess("블랙핑크 챌린지 예능 화제")["score"])
        self.assertIn("영상 구성", " ".join(visual["reasons"]))

    def test_view_and_reaction_growth_each_affect_order_within_the_same_source(self):
        titles = ("장원영 인터뷰 반응 정리", "카리나 인터뷰 반응 정리", "안유진 인터뷰 반응 정리")
        before = [row(title=t, post=1000 + i, views=1000, reactions=100) for i, t in enumerate(titles)]
        # A high cumulative count alone must not outrank actual growth.
        before[2]["views"], before[2]["reactions"] = 1000000, 10000
        _, history = e.observe({"디시 실베": before}, EMPTY, NOW)
        after = [dict(x) for x in before]
        for item, views, reactions in zip(after, (10, 100, 5), (100, 1, 5)):
            item["views"] += views
            item["reactions"] += reactions
        stories, _ = e.observe({"디시 실베": after}, history, NOW + 1800)
        self.assertEqual([s["lead"]["title"] for s in stories], [titles[1], titles[0], titles[2]])
        self.assertIn("조회 증가 속도가 상위권", " ".join(stories[0]["reasons"]))
        self.assertIn("추천 증가 속도가 상위권", " ".join(stories[1]["reasons"]))

    def test_growth_is_compared_per_source_and_not_by_cross_site_counts(self):
        before = {source: [row(source=source, title=f"장원영 인터뷰 {source} {i}",
                               post=2000 + n * 10 + i, reactions=100) for i in range(2)]
                  for n, source in enumerate(("디시 실베", "펨코 포텐"))}
        _, history = e.observe(before, EMPTY, NOW)
        after = {source: [dict(x) for x in items] for source, items in before.items()}
        for source, increases in (("디시 실베", (2, 1)), ("펨코 포텐", (2000, 1000))):
            for item, increase in zip(after[source], increases):
                item["reactions"] += increase
        stories, _ = e.observe(after, history, NOW + 3600)
        boosted = [s for s in stories if s["score"] > e.assess(s)["score"]]
        self.assertEqual({s["lead"]["source"] for s in boosted}, set(before))
        self.assertTrue(all(s["lead"]["title"].endswith(" 0") for s in boosted))

    def test_missing_stale_and_reset_counters_cannot_promote_an_idol_story(self):
        initial = row(title="장원영 인터뷰 공개", views=100, reactions=10)
        _, history = e.observe({"디시 실베": [initial]}, EMPTY, NOW)
        for views, reactions, elapsed in ((None, None, 3600), (90, 5, 3600),
                                           (200, 20, 7 * 3600), (200, 20, 60)):
            with self.subTest(views=views, reactions=reactions, elapsed=elapsed):
                current = {**initial, "views": views, "reactions": reactions}
                stories, _ = e.observe({"디시 실베": [current]}, history, NOW + elapsed)
                self.assertEqual(stories[0]["score"], e.assess(stories[0])["score"])
        stories, _ = e.observe({"디시 실베": [initial]}, EMPTY, NOW)
        self.assertEqual(stories[0]["score"], e.assess(stories[0])["score"])

    def test_merged_story_gets_each_growth_bonus_once_and_single_sample_is_not_top_ranked(self):
        before = {source: [row(source=source, title="장원영 새로운 인터뷰 내용 공개", post=3000 + n,
                               views=100, reactions=10)]
                  for n, source in enumerate(("디시 실베", "펨코 포텐"))}
        _, history = e.observe(before, EMPTY, NOW)
        after = {source: [{**items[0], "views": 200, "reactions": 20}] for source, items in before.items()}
        stories, _ = e.observe(after, history, NOW + 3600)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["score"] - e.assess(stories[0])["score"], 25)
        self.assertNotIn("상위권", " ".join(stories[0]["reasons"]))

    def test_topic_ranking_alone_cannot_bypass_publication_gate(self):
        items = [row(title=f"일반 소식 관련 인터뷰 {i}", post=4000 + i) for i in range(7)]
        idol = row(title="장원영 취향 공개", post=4999)
        items.append(idol)
        stories, _ = e.observe({"디시 실베": items}, EMPTY, NOW)
        self.assertEqual(stories[0]["lead"]["title"], idol["title"])
        self.assertEqual(select_stories(stories), [])


if __name__ == "__main__":
    unittest.main()
