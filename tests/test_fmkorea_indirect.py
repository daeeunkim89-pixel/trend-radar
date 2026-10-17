import unittest
from datetime import datetime

from bs4 import BeautifulSoup

import editorial as e
import fmkorea_indirect as f
import telegram_editor as t
from communities import fmkorea_url
from selection import select_stories
from test_communities import candidate
from test_editorial import EMPTY, NOW


class FMKoreaIndirectTests(unittest.TestCase):
    def card(self, at=NOW, url="https://m.fmkorea.com/best2/10454601662", site="fmkorea"):
        stamp = datetime.fromtimestamp(at, e.KST).isoformat()
        return f'''<div class="post-card" data-site="{site}"><time datetime="{stamp}" title="수집 시각"></time>
          <a class="post-title" href="{url}">반영 빠르다는 레드벨벳 ㄷㄷㄷ</a><div class="post-stats">조회 551,273 댓글 227 점수 1559</div></div>'''

    def soup(self, markup):
        return BeautifulSoup(markup, "html.parser")

    def test_lolus_discovers_original_without_inventing_current_metrics_or_post_date(self):
        rows = f.parse_lolus(self.soup(self.card()), now=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["link"], "https://www.fmkorea.com/10454601662")
        self.assertEqual(rows[0]["discovery_timestamp_kind"], "index_observed")
        self.assertEqual(rows[0]["discovery_observed_at"], NOW)
        self.assertIsNone(rows[0]["views"])
        self.assertIsNone(rows[0]["reactions"])
        self.assertNotIn("published_at", rows[0])
        self.assertNotIn("listed_at", rows[0])

    def test_stale_future_missing_or_unzoned_time_and_foreign_hosts_are_rejected(self):
        markup = self.card(NOW - 86401) + self.card(NOW + 301)
        markup += self.card(url="https://www.fmkorea.com.evil.example/10454601662")
        markup += self.card(site="clien")
        markup += self.card().replace('datetime="' + datetime.fromtimestamp(NOW, e.KST).isoformat() + '"', 'datetime="2026-10-16T12:00:00"')
        self.assertEqual(f.parse_lolus(self.soup(markup), now=NOW), [])

    def test_all_supported_fm_post_variants_have_one_identity(self):
        for url in ("http://fmkorea.com/10454601662", "https://m.fmkorea.com/best/10454601662/", "https://www.fmkorea.com/best2/10454601662",
                    "https://m.fmkorea.com/index.php?mid=humor&document_srl=10454601662&cpage=2"):
            self.assertEqual(fmkorea_url(url), "https://www.fmkorea.com/10454601662")
            self.assertEqual(e.canonical_url(url), "https://www.fmkorea.com/10454601662")
        self.assertIsNone(fmkorea_url("https://www.fmkorea.com/files/attach/images/10454601662"))
        self.assertIsNone(fmkorea_url("https://www.fmkorea.com.evil.example/10454601662"))

    def test_one_public_index_failure_does_not_drop_the_other_source(self):
        def get(url):
            if url == f.LOLUS_URL:
                return self.soup(self.card())
            raise RuntimeError("HTTP 503")
        rows = f.fetch_fmkorea_indirect(get, now=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["discovery"], "LL 공개목록")

    def test_cache_never_refreshes_its_snapshot_using_current_last_seen(self):
        row = f.parse_lolus(self.soup(self.card()), now=NOW)[0]
        history = {"items": {"one": {**row, "last_seen_at": NOW + 86402}}}
        self.assertEqual(f.recent_cache(history, NOW + 86402), [])
        row.pop("discovery_observed_at")
        self.assertEqual(f.recent_cache({"items": {"one": row}}, NOW), [])

    def test_valid_public_cache_survives_a_temporary_index_outage(self):
        row = f.parse_lolus(self.soup(self.card()), now=NOW)[0]
        def broken(url):
            raise RuntimeError("HTTP 503")
        rows = f.fetch_fmkorea_indirect(broken, history={"items": {"one": row}}, now=NOW + 3600)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["discovery_cache"])
        self.assertEqual(rows[0]["discovery_observed_at"], NOW)

    def test_observation_preserves_discovery_metadata_for_later_fallback(self):
        row = f.parse_lolus(self.soup(self.card()), now=NOW)[0]
        _, history = e.observe({"펨코 간접": [row]}, EMPTY, NOW)
        cached = f.recent_cache(history, NOW + 3600)
        self.assertEqual(cached[0]["link"], row["link"])
        self.assertEqual(cached[0]["discovery_timestamp_kind"], "index_observed")

    def test_only_body_and_explicit_citations_supply_fm_origins(self):
        markup = '''<div class="view_content">레드벨벳 팬 댓글 요청 반영</div>
          <div class="source_url">출처 <a href="https://m.fmkorea.com/best2/10454601662">원문</a></div>
          <div class="comment"><a href="https://www.fmkorea.com/9999999999">댓글의 다른 글</a></div>
          <aside><a href="https://www.fmkorea.com/8888888888">추천 글</a></aside>'''
        detail = e.parse_detail(markup, "https://bbs.ruliweb.com/community/board/300143/read/77054350", "레드벨벳")
        self.assertEqual(detail["fmkorea_links"], [{"label": "펨코 출처", "url": "https://www.fmkorea.com/10454601662"}])
        self.assertIn("item:" + e.item_id("https://www.fmkorea.com/10454601662"), t.story_content_keys(candidate("레드벨벳 팬 댓글 요청 반영", detail=detail)))

    def test_repost_and_index_pointing_to_same_fm_id_do_not_take_two_slots(self):
        detail = {"fmkorea_links": [{"label": "펨코 출처", "url": "https://www.fmkorea.com/10454601662"}]}
        repost = candidate("카리나 팬 댓글 요청 반영", detail=detail)
        original = candidate("레드벨벳 팬 요청 반영 변화", n=2)
        original["lead"]["link"] = "https://www.fmkorea.com/10454601662"
        self.assertEqual(len(select_stories([repost, original])), 1)

    def test_report_labels_direct_access_failure_separately_from_indirect_discovery(self):
        row = f.parse_lolus(self.soup(self.card()), now=NOW)[0]
        stories, history = e.observe({"펨코 간접": [row]}, EMPTY, NOW)
        chosen = select_stories(stories)
        rendered = e.render_digest(chosen, {"아이돌": 1}, {"펨코 포텐": "HTTP 430"}, {}, NOW)[0]
        self.assertIn("펨코 직접", rendered)
        self.assertIn("펨코·간접", rendered)
        info = e.render_info(next(iter(history["items"].values())), "test")
        self.assertIn("외부 목록 관측", info)
        self.assertIn("사건 발생일 아님", info)


if __name__ == "__main__":
    unittest.main()
