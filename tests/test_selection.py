import unittest
from collections import Counter

from bs4 import BeautifulSoup

import discovery
import editorial as e
import monitor
from selection import CATEGORIES, qualify, select_stories
from test_editorial import EMPTY, NOW, row


def story(title, post=100000, source="디시 실베", views=None):
    stories, _ = e.observe({source: [row(source=source, title=title, post=post, views=views)]}, EMPTY, NOW)
    return stories[0]


class SelectionTests(unittest.TestCase):
    def test_user_red_velvet_example_passes_as_an_idol_change_story(self):
        candidate = story("반영 빠르다는 레드벨벳 ㄷㄷㄷ")
        candidate["lead"]["link"] = "https://www.fmkorea.com/10454601662"
        chosen = select_stories([candidate])
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0]["category"], "아이돌")
        self.assertIn("전후 변화", chosen[0]["review_reason"])

    def test_concrete_material_from_each_requested_field_can_pass(self):
        cases = {
            "전국 통신망 먹통에 결제 서비스 전면 마비": "시사",
            "은행 주담대 변동금리 6% 줄줄이 돌파": "시사",
            "허위 경력 들통난 백악관 대변인 최단명 해임": "시사",
            "[번리vs울버햄튼] 제이미 바디 번리 데뷔골": "축구",
            "전북 현대 K리그 우승 확정": "축구",
            "오타니 MLB 역대 최초 기록 달성": "메이저 스포츠",
            "안세영 59승 1패 신기록 달성": "메이저 스포츠",
            "BTS 팬 댓글 요청 반영해 커진 자막": "아이돌",
            "제니 무대 돌발 상황에 깜짝 대처": "아이돌",
        }
        for title, category in cases.items():
            with self.subTest(title=title):
                self.assertEqual(qualify(story(title))[0], category)

    def test_actual_low_value_feed_patterns_and_plain_names_are_rejected(self):
        titles = (
            "[로갤] 스압)) 로아 민심 폭발한 과정을 알아보자...jpg",
            "[싱갤] 떡볶이 피하려다 떡라면에 잡힘.jpg",
            "[싱갤] 밥 존나 먹는 일본 주갤러 근황...jpg",
            "[날씨] 파란 쪽빛 하늘, 한강 나들이",
            "추미애 순직 소방관 빈소 조문", "경찰 흉기 난동범 주거지 압수수색",
            "한국체대 총장 병역특례 학생 선수 위해 필요", "[준PO 1차전] 톨허스트 1K",
            "김민재 대표팀에서는 여포, 뮌헨에서는 새색시 같아",
            "아스널 김민재 관심 겨울 이적시장에서 영입하나",
            "김민재 대반전 아스널 535억에 러브콜 EPL 우승 위해 필요해",
            "손흥민 우승 정조준 66년 숙원 이룰까",
            "카리나 인터뷰 공개", "장원영 취향 공개", "카리나 공항패션 공개",
            "아이브 신곡 챌린지 댄서 시미즈 제이미 인규에 이은",
            "아이브 몸매 직캠 화제", "빅뱅 우주 관측 최초 기록",
        )
        for title in titles:
            with self.subTest(title=title):
                self.assertIsNone(qualify(story(title, views=1000000)))

    def test_big_view_counts_and_topic_scores_cannot_fill_the_report_with_junk(self):
        candidates = [story("카리나 인터뷰 공개", post=100001, views=1000000),
                      story("장원영 취향 공개", post=100002, views=1000000)]
        self.assertEqual(select_stories(candidates), [])

    def test_same_player_performance_is_not_repeated_under_different_headlines(self):
        a = story("오현규 2골 1도움 신기록 달성", post=100001)
        b = story("오현규 멀티골 폭발 대기록 달성", post=100002)
        chosen = select_stories([a, b])
        self.assertEqual(len(chosen), 1)

    def test_selection_caps_volume_and_preserves_each_available_qualifying_field(self):
        titles = [f"손흥민 새로운 신기록 달성 소식 {i}" for i in range(15)]
        titles += [f"레드벨벳 팬 댓글 반영 변화 {i}" for i in range(5)]
        titles += ["전국 은행 서비스 먹통 대란", "오타니 MLB 역대 최초 기록"]
        rows = [row(title=t, post=100000 + i) for i, t in enumerate(titles)]
        stories, _ = e.observe({"디시 실베": rows}, EMPTY, NOW)
        chosen = select_stories(stories)
        counts = Counter(s["category"] for s in chosen)
        self.assertLessEqual(len(chosen), 10)
        self.assertEqual(set(counts), set(CATEGORIES))
        self.assertTrue(all(n <= 4 for n in counts.values()))
        mapping = e.digest_numbers(chosen, {})
        self.assertEqual(set(mapping.values()), {s["id"] for s in chosen})
        parts = e.render_digest(chosen, counts, {}, {}, NOW)
        self.assertEqual(len(parts), 1)
        self.assertLessEqual(e.message_units(parts[0]), 3900)


class DiscoveryTests(unittest.TestCase):
    def soup(self, text):
        return BeautifulSoup(text, "html.parser")

    def test_ranked_entertainment_extracts_headline_without_article_excerpt_or_fake_metrics(self):
        soup = self.soup('''<div class="postRankSubjectList"><a class="lt1" href="//news.nate.com/view/20261017n12345">
            <h2 class="tit">레드벨벳 팬 댓글 요청 반영해 커진 자막</h2><span>기사 본문 설명이 제목에 섞이면 안 됩니다</span>
            </a></div><div id="postRankSubject"><ul class="mduRankSubject"><li>
            <a href="//news.nate.com/view/20261017n12347">에스파 윈터 기묘한 자세 160만뷰 화제</a>
            </li></ul></div><a href="//news.nate.com/view/20261017n12346">사이드바 제목</a>''')
        rows = discovery.parse_nate_topic(soup, "https://news.nate.com/rank/interest?sc=ent", "네이트 연예", now=1792220400)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "레드벨벳 팬 댓글 요청 반영해 커진 자막")
        self.assertIsNone(rows[0]["views"])
        self.assertIsNone(rows[0]["reactions"])
        self.assertEqual(rows[0]["rank_kind"], "nate_ent_interest_100")

    def test_football_section_scope_excludes_old_articles_sidebar_and_foreign_hosts(self):
        soup = self.soup('''<div class="mduCluster">
          <a href="https://sports.news.nate.com/view/20261017n12345"><h2>전북 현대 우승 확정 소식</h2><span>본문 발췌</span></a>
          <a href="https://sports.news.nate.com/view/20260101n12345"><h2>손흥민 과거 신기록 소식</h2></a>
          <a href="https://evil.example/view/20261017n12345"><h2>외부 링크 제목입니다</h2></a></div>
          <a href="https://news.nate.com/view/20261017n54321">사이드바 연예 기사</a>''')
        rows = discovery.parse_nate_topic(soup, "https://sports.news.nate.com/soccer/", "국내·해외축구", "football", now=1792220400)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "전북 현대 우승 확정 소식")
        self.assertEqual(rows[0]["topic_hint"], "football")
        self.assertNotIn("rank_kind", rows[0])

    def index_row(self, post="10454601662", date="2026-10-17 06:27:00", host="www.issuelink.co.kr"):
        return f'''<tr><td class="rank_bg"><small>펨코</small></td><td>
          <div class="first_title"><span class="title"><a href="https://{host}/community/go/fmkorea/{post}">
          반영 빠르다는 레드벨벳 ㄷㄷㄷ <small>[171]</small></a></span></div>
          <div class="second_date"><span>{date}</span></div><div class="second_etc"><span class="hit">394,114</span></div>
          </td></tr>'''

    def test_public_index_preserves_original_fmkorea_link_without_claiming_source_metrics(self):
        soup = self.soup('<table>' + self.index_row() + self.index_row() + '</table>')
        rows = discovery.parse_community_index(soup, now=1792220400)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["link"], "https://www.fmkorea.com/10454601662")
        self.assertEqual(rows[0]["title"], "반영 빠르다는 레드벨벳 ㄷㄷㄷ")
        self.assertEqual(rows[0]["origin"], "펨코")
        self.assertIsNone(rows[0]["views"])
        self.assertIsNone(rows[0]["reactions"])
        stories, _ = e.observe({"커뮤니티 인기": rows}, EMPTY, 1792220400)
        chosen = select_stories(stories)
        self.assertEqual(len(chosen), 1)
        rendered = e.render_digest(chosen, {"아이돌": 1}, {}, {}, 1792220400)[0]
        self.assertIn("펨코·목록", rendered)
        self.assertNotIn("394", rendered)

    def test_stale_undated_and_foreign_index_rows_are_rejected(self):
        soup = self.soup('<table>' + self.index_row(date="2026-10-10 06:27:00")
                        + self.index_row(date="날짜 없음") + self.index_row(host="evil.example") + '</table>')
        self.assertEqual(discovery.parse_community_index(soup, now=1792220400), [])

    def test_discovery_pool_can_exceed_ten_while_default_parser_limit_stays_ten(self):
        soup = self.soup(''.join(f'<a href="https://n.news.naver.com/article/001/{1000000000+i}">새로운 뉴스 후보 제목 {i}</a>' for i in range(25)))
        self.assertEqual(len(monitor.parse_naver_news(soup, "https://news.naver.com")), 10)
        self.assertEqual(len(monitor.parse_naver_news(soup, "https://news.naver.com", limit=60)), 25)


if __name__ == "__main__":
    unittest.main()
