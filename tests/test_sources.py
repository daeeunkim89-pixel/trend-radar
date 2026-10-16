"""Fixtures preserve the desktop/mobile structures observed during live validation."""
import unittest

from bs4 import BeautifulSoup

import editorial
import monitor


class SourceLayoutTests(unittest.TestCase):
    def soup(self, text):
        return BeautifulSoup(text, "html.parser")

    def test_naver_mobile_title_excludes_rank_age_and_video_label(self):
        soup = self.soup('''<a href="https://n.news.naver.com/article/001/1234567890?ntype=RANKING">
          <em class="list_ranking_num">1</em><div class="list_content">
          <strong class="list_title">스포츠 선수의 새로운 기록 소식</strong><span class="list_time">3시간전</span></div>
          <span class="blind">동영상 뉴스</span></a>''')
        item = monitor.parse_naver_news(soup, "https://m.news.naver.com/rankingList")[0]
        self.assertEqual(item["title"], "스포츠 선수의 새로운 기록 소식")
        self.assertIsNone(item["views"])

    def test_naver_desktop_image_duplicate_and_foreign_links_are_excluded(self):
        soup = self.soup('''<a href="https://n.news.naver.com/article/001/1234567890" class="list_title">스포츠 선수의 새로운 기록 소식</a>
        <a href="https://n.news.naver.com/article/001/1234567890" class="list_img"><img></a>
        <a href="https://n.news.naver.com.evil.example/article/001/1234567891">외부 링크는 수집하지 않음</a>''')
        self.assertEqual(len(monitor.parse_naver_news(soup, "https://news.naver.com")), 1)

    def test_nate_uses_sports_interest_ranking_instead_of_general_news_or_main_cards(self):
        soup = self.soup('''<a href="//sports.news.nate.com/view/20261016n10000"><h2 class="subj">메인 기사 제목입니다</h2><span class="parag">기사 설명을 제목에 섞으면 안 됩니다</span></a>
        <div id="intNews1"><div id="sisa1"><ol><li><a href="//news.nate.com/view/20261016n10001">일반 뉴스 랭킹입니다</a></li></ol></div></div>
        <div id="intNews2"><div id="sport1"><ol><li><a href="//sports.news.nate.com/view/20261016n10002" title="손흥민 스포츠 급상승 기사입니다">축약된 표시 제목</a></li></ol></div></div>''')
        items = monitor.parse_nate_sports(soup, "https://sports.news.nate.com/")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "손흥민 스포츠 급상승 기사입니다")
        self.assertEqual(items[0]["rank_kind"], "nate_sports_interest")

    def test_nate_fallback_does_not_treat_summary_as_headline_or_invent_rank(self):
        soup = self.soup('''<a href="//news.nate.com/view/20261016n10000"><h2 class="subj">스포츠 메인 기사 제목입니다</h2><span class="parag">기사 본문 미리보기입니다</span></a>''')
        item = monitor.parse_nate_sports(soup, "https://sports.news.nate.com/")[0]
        self.assertEqual(item["title"], "스포츠 메인 기사 제목입니다")
        self.assertNotIn("rank_kind", item)

    def dc_mobile(self, views=100, reactions=0):
        return self.soup(f'''<div><a class="lt" href="https://m.dcinside.com/board/dcbest/30638"><span class="ntc-line-orange">공지</span>이용 안내</a></div>
        <div class="gall-detail-lnktb"><a class="lt" href="https://m.dcinside.com/board/dcbest/470001">
        <span class="subject-add"><span class="sp-lst">이미지</span><span class="subjectin"><b>[스포츠]</b> 선수의 새로운 기록 소식</span></span>
        <ul class="ginfo"><li class="list-nick">작성자</li><li>16:00</li><li>조회 {views}</li><li class="up-add">추천 <span>{reactions}</span></li></ul></a>
        <a href="https://m.dcinside.com/board/dcbest/470001#comment_box">15</a></div>''')

    def test_dc_mobile_skips_notices_and_comments_and_extracts_metrics(self):
        items = monitor.parse_dc(self.dc_mobile(), "https://m.dcinside.com/board/dcbest")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "[스포츠] 선수의 새로운 기록 소식")
        self.assertEqual(items[0]["views"], 100)
        self.assertEqual(items[0]["reactions"], 0)

    def test_dc_desktop_still_reads_metric_cells_and_skips_notice(self):
        soup = self.soup('''<table><tr><td class="gall_num">공지</td><td class="gall_tit"><a href="/board/view/?id=dcbest&amp;no=30638">이용 안내 공지</a></td></tr>
        <tr><td class="gall_num">123</td><td class="gall_tit"><a href="/board/view/?id=dcbest&amp;no=470001">스포츠 새로운 기록 소식</a></td><td class="gall_count">1,234</td><td class="gall_recommend">12</td></tr></table>''')
        items = monitor.parse_dc(soup, "https://gall.dcinside.com")
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["views"], items[0]["reactions"]), (1234, 12))

    def test_mobile_metric_changes_do_not_change_title_and_do_generate_real_growth(self):
        before = monitor.parse_dc(self.dc_mobile(), "https://m.dcinside.com")
        after = monitor.parse_dc(self.dc_mobile(600, 8), "https://m.dcinside.com")
        _, history = editorial.observe({"디시 실베": before}, {"version": 1, "items": {}}, 100000)
        stories, _ = editorial.observe({"디시 실베": after}, history, 103600)
        item = stories[0]["lead"]
        self.assertFalse(item["title_changed"])
        self.assertEqual(item["change"]["views"], 500)
        self.assertEqual(item["change"]["reactions"], 8)

    def test_rank_comparison_requires_same_explicit_ranking_scope(self):
        before = monitor.make_item("네이트 스포츠", "스포츠 선수의 새로운 기록 소식", "https://sports.news.nate.com/view/20261016n10000", 8)
        before["rank_kind"] = "nate_sports_interest"
        _, history = editorial.observe({"네이트 스포츠": [before]}, {"version": 1, "items": {}}, 100000)
        after = {**before, "rank": 2}
        stories, _ = editorial.observe({"네이트 스포츠": [after]}, history, 103600)
        self.assertEqual(stories[0]["lead"]["change"]["rank"], 6)
        after.pop("rank_kind")
        stories, _ = editorial.observe({"네이트 스포츠": [after]}, history, 103600)
        self.assertNotIn("rank", stories[0]["lead"]["change"])


if __name__ == "__main__":
    unittest.main()
