"""Observed community layouts and publication/deduplication boundaries."""
import unittest
from copy import deepcopy
from datetime import datetime
from unittest.mock import Mock

from bs4 import BeautifulSoup

import communities as c
import editorial as e
import telegram_editor as t
from selection import ARTICLE_LIMIT, context_candidates, qualify, select_stories
from test_editorial import EMPTY, NOW


def candidate(title, n=1, source="더쿠 HOT", detail=None):
    community = source == "더쿠 HOT"
    row = {"source": source, "title": title, "link": f"https://theqoo.net/hot/{4378000000+n}" if community else f"https://news.nate.com/view/20261017n{10000+n}",
           "rank": n, "views": 20000, "reactions": None, "comments": 50}
    stories, _ = e.observe({source: [row]}, EMPTY, NOW)
    story = stories[0]
    if detail is not None:
        story["detail"] = detail
    return story


class CommunityLayouts(unittest.TestCase):
    def rows(self, html, source, base):
        return c.parse_board(BeautifulSoup(html, "html.parser"), base, source, NOW)

    def test_theqoo_skips_notices_and_comment_links_and_keeps_real_views(self):
        stamp = datetime.fromtimestamp(NOW - 3600, c.KST).strftime("%Y%m%d%H%M%S")
        html = f'''<table><tr class="notice"><td class="title"><a href="/hot/4378000000">공지 안내입니다</a></td></tr>
          <tr data-regdate="{stamp}"><td class="title"><a href="/hot/4378000001">반영 빠르다는 레드벨벳</a>
          <a class="replyNum" href="/hot/4378000001#comment">120</a></td><td class="cate">유머</td><td class="m_no">32,000</td></tr></table>'''
        rows = self.rows(html, "더쿠 HOT", "https://theqoo.net/hot")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["views"], rows[0]["comments"], rows[0]["reactions"]), (32000, 120, None))
        self.assertEqual(rows[0]["content_kind"], "community")

    def test_dogdrip_popular_list_has_recommendations_not_invented_views(self):
        html = '''<li><h5><a class="title-link" data-document-srl="730000001" href="/dogdrip/730000001?sort_index=popular&page=1">손흥민 팬서비스 반응</a><span>32</span></h5>
          <div><span><span><i class="fa-thumbs-up"></i></span><span>120</span></span>
          <span><i class="fa-clock"></i>1 시간 전</span></div></li>'''
        rows = self.rows(html, "개드립 인기", "https://www.dogdrip.net")
        self.assertEqual(rows[0]["reactions"], 120)
        self.assertIsNone(rows[0]["views"])
        self.assertEqual(rows[0]["link"], "https://www.dogdrip.net/730000001")

    def test_ruliweb_removes_rank_and_comment_suffix_and_does_not_mix_hot_deals(self):
        html = '''<table><tr><td><a class="subject_link" href="/best/board/300143/read/77054350?m=humor"><span>1</span><strong class="text_over">반영 빠르다는 레드벨벳</strong><span class="num_reply">(94)</span></a></td>
          <td class="hit">30,100</td><td class="recomd">109</td><td class="time">16:00</td></tr>
          <tr><td><a class="subject_link" href="/market/board/1020/read/108112">핫딜 만두</a></td><td class="time">16:00</td></tr></table>'''
        rows = self.rows(html, "루리웹 베스트", "https://bbs.ruliweb.com")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "반영 빠르다는 레드벨벳")
        self.assertEqual(rows[0]["views"], 30100)
        self.assertEqual(rows[0]["link"], "https://bbs.ruliweb.com/community/board/300143/read/77054350")

    def test_boba_preserves_post_identity_and_only_source_counters(self):
        html = '''<tr><td><a class="bsubject" href="/view?code=best&No=1040513&vdate=">반영 빠르다는 레드벨벳</a><strong class="totreply">12</strong></td>
          <td class="date">16:00</td><td class="count">13,766</td><td class="recomm">139</td></tr>'''
        rows = self.rows(html, "보배드림 베스트", "https://www.bobaedream.co.kr")
        self.assertEqual(rows[0]["views"], 13766)
        self.assertEqual(rows[0]["reactions"], 139)
        self.assertEqual(e.canonical_url("https://m.bobaedream.co.kr/board/bbs_view/best/1040513/1"), rows[0]["link"])

    def test_instiz_green_list_separates_comments_from_title(self):
        html = '''<tr id="detour"><td class="listsubject"><a href="https://www.instiz.net/pt/7914412?green=1"><span>반영 빠르다는 걸그룹 레드벨벳<span class="cmt3">42</span></span></a></td>
          <td class="listno">16:00</td><td class="listno">29,565</td><td class="listno">4</td></tr>'''
        rows = self.rows(html, "인스티즈 이슈", "https://www.instiz.net/pt")
        self.assertEqual(rows[0]["title"], "반영 빠르다는 걸그룹 레드벨벳")
        self.assertEqual(rows[0]["comments"], 42)
        self.assertEqual(rows[0]["link"], "https://www.instiz.net/pt/7914412")

    def test_mlb_best_cards_are_not_confused_with_latest_bullpen_chat(self):
        html = '''<ul class="lists_today"><li><div class="date">3시간전</div><div class="title"><a href="https://mlbpark.donga.com/mp/b.php?b=mlbtown&id=202610160119484576&m=view">오타니 역대 최초 대기록</a></div></li></ul>'''
        rows = self.rows(html, "엠팍 BEST", "https://mlbpark.donga.com")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["list_category"], "야구")
        self.assertIsNone(rows[0]["views"])

    def test_stale_undated_foreign_host_and_logo_links_do_not_become_posts(self):
        for stamp, href in [("20250101120000", "/hot/4378000001"), ("", "/hot/4378000001"),
                            ("20261016160000", "https://theqoo.net.evil.example/hot/4378000001")]:
            html = f'<tr data-regdate="{stamp}"><td class="title"><a href="{href}">반영 빠르다는 레드벨벳</a></td></tr>'
            self.assertEqual(self.rows(html, "더쿠 HOT", "https://theqoo.net"), [])


class CommunityBodies(unittest.TestCase):
    def test_body_media_excludes_comments_sidebar_avatars_and_article_og_image(self):
        markup = '''<meta property="og:image" content="https://cdn.example/logo.jpg"><div class="xe_content">
          <p>팬 댓글 요청을 반영한 자막 비교</p><img src="https://cdn.example/before.webp"><img src="https://cdn.example/after.webp"></div>
          <div class="xe_content comment"><img src="https://cdn.example/unrelated.jpg"></div>'''
        detail = e.parse_detail(markup, "https://theqoo.net/hot/4378000001", "레드벨벳")
        self.assertEqual(len(detail["media"]), 2)
        self.assertEqual(detail["format"], "이미지")
        self.assertNotIn("unrelated", str(detail))

    def test_plain_x_post_is_preserved_as_original_without_inventing_a_video(self):
        detail = e.parse_detail('<div class="xe_content"><p>https://x.com/fan/status/1234567890?s=46</p>8회 말 역전 홈런</div>',
                                "https://theqoo.net/hot/4378000001", "KBO 장면")
        self.assertEqual(detail["source_links"][0]["url"], "https://x.com/fan/status/1234567890")
        self.assertEqual(detail["format"], "원본 SNS")
        self.assertEqual(detail["media"], [])

    def test_native_video_and_instiz_images_are_detected_without_body_text(self):
        for html, url, expected in [('<div id="contentDetail"><video><source src="https://cdn.example/clip.mp4"></video></div>',
                                    "https://mlbpark.donga.com/mp/b.php", "영상"),
                                   ('<div id="memo_content_1"><img src="https://cdn.instiz.net/file3/abcdef"></div>',
                                    "https://www.instiz.net/pt/7914412", "이미지")]:
            detail = e.parse_detail(html, url, "제목")
            self.assertEqual(detail["format"], expected)
            self.assertEqual(len(detail["media"]), 1)

    def test_a_news_redirect_cannot_escape_the_detail_host_allowlist(self):
        self.assertFalse(e.allowed_detail("https://127.0.0.1/private"))
        self.assertFalse(e.allowed_detail("https://theqoo.net.evil.example/hot/1234567"))
        self.assertTrue(e.allowed_detail("https://www.instiz.net/pt/7914412"))


class CommunitySelection(unittest.TestCase):
    def test_news_alone_can_never_fill_the_digest(self):
        titles = ["손흥민 신기록 달성", "오타니 역대 최초 기록", "은행 주담대 금리 인상", "제니 빌보드 최초 기록"]
        picked = select_stories([candidate(title, n + 1, "네이트 스포츠") for n, title in enumerate(titles)])
        self.assertEqual(len(picked), ARTICLE_LIMIT)

    def test_community_original_is_the_lead_even_if_news_has_the_same_headline(self):
        a = candidate("손흥민 신기록 달성", source="네이트 스포츠")["lead"]
        b = candidate("손흥민 신기록 달성")["lead"]
        stories, _ = e.observe({"네이트 스포츠": [a], "더쿠 HOT": [b]}, EMPTY, NOW)
        self.assertEqual(stories[0]["lead"]["source"], "더쿠 HOT")

    def test_post_text_can_qualify_a_short_caption_but_not_a_plain_news_name(self):
        detail = {"context": "레드벨벳 팬 댓글 요청을 반영해 자막이 커졌다는 전후 비교", "media": [{"kind": "image", "url": "https://cdn.example/comparison.webp"}]}
        story = candidate("하루만에 이렇게 바뀜", detail=detail)
        self.assertEqual(qualify(story)[0], "아이돌")
        self.assertIsNone(qualify(candidate("카리나 인터뷰 공개", source="네이트 스포츠")))

    def test_major_playoff_scene_and_public_life_incident_are_eligible(self):
        detail = {"media": [], "source_links": [{"url": "https://x.com/fan/status/12345"}]}
        for title, category in [("[KBO-준PO] KIA 김도영 멀티 홈런", "메이저 스포츠"),
                                ("시내버스 탄 할머니 경찰 불러 강제 하차", "시사")]:
            self.assertEqual(qualify(candidate(title, detail=detail))[0], category)

    def test_same_original_social_post_is_selected_once_across_different_captions(self):
        detail = {"source_links": [{"url": "https://x.com/fan/status/12345"}]}
        a = candidate("카리나 팬 댓글 요청 반영", detail=detail)
        b = candidate("레드벨벳 팬 요청 반영 변화", n=2, detail=detail)
        self.assertEqual(len(select_stories([a, b])), 1)

    def test_material_identity_also_blocks_previously_delivered_reposts(self):
        detail = {"source_links": [{"url": "https://x.com/fan/status/12345"}]}
        old = candidate("카리나 팬 댓글 요청 반영", detail=detail)
        new = candidate("레드벨벳 팬 요청 반영 변화", n=2, detail=detail)
        private = Mock(data={"reports": {}, "content_history": {key: NOW for key in t.story_content_keys(old)}})
        self.assertEqual(t.unreported_stories([new], deepcopy(EMPTY), private, NOW + 3600), [])

    def test_inspection_budget_remains_bounded_and_has_no_news(self):
        rows = [candidate(f"레드벨벳 팬 댓글 요청 반영 {n}", n + 1) for n in range(30)]
        rows += [candidate("손흥민 신기록 달성", n + 40, "네이트 스포츠") for n in range(30)]
        self.assertLessEqual(len(context_candidates(rows)), 8)
        self.assertTrue(all(x["lead"]["source"] == "더쿠 HOT" for x in context_candidates(rows)))

    def test_animal_caption_and_unverified_fan_fight_do_not_pass_as_idol_material(self):
        detail = {"context": "공원에 구경온 사람들 모두 환호하니 아이돌 인기 부럽지 않았다 ㅋㅋㅋㅋ", "media": [{"kind": "image", "url": "https://cdn.example/animal.webp"}]}
        self.assertIsNone(qualify(candidate("부캉이 구경갔다가 마주친 개꿀잼 모먼트.txt", detail=detail)))
        self.assertIsNone(qualify(candidate("[걸갤] 에스파 공연장 여성들 난투극", detail=detail)))

    def test_baseball_history_lists_and_fan_opinion_do_not_become_major_news(self):
        for title in ('역대 크보 구단의 역사를 바꾼 신인 입단 Top 10', 'KBO 이렇게 운영해서 3년동안 2우승 반박할 논리가 없을거임'):
            self.assertIsNone(qualify(candidate(title)))

    def test_same_institution_incident_is_not_repeated_in_one_report(self):
        a = candidate("현재 심각하다는 아주대 소아과 압수수색 사태")
        b = candidate("아주대 응급실 사건, 피해 때문에 생긴 사태", n=2)
        self.assertEqual(len(select_stories([a, b])), 1)

    def test_lone_generic_article_preview_is_not_a_material_identity(self):
        self.assertEqual(c.material_urls({"media": [{"label": "기사 미리보기 이미지", "url": "https://cdn.example/stock.jpg"}]}), set())

    def test_clickbait_football_quote_does_not_fill_the_news_fallback(self):
        self.assertIsNone(qualify(candidate('이강인 얼마나 더 잘해야 하나 오피셜 폭탄 발언', source="네이트 스포츠")))


if __name__ == "__main__":
    unittest.main()
