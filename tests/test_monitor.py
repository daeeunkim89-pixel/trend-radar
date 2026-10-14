import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup

import monitor


POSTS = """<html><title>포텐</title><body>
<h3 class="title"><a href="https://www.fmkorea.com/1000001">테스트 게시물 제목</a></h3>
</body></html>"""
BLOCKED = """<html><title>에펨코리아 보안 시스템</title><body>
비정상 접속이 의심되어 차단되었습니다.</body></html>"""


class Page:
    def __init__(self, status=200, html=POSTS, recovered=None, timeout=False):
        self.main_frame = object()
        self.status = status
        self.html = html
        self.recovered = recovered
        self.timeout = timeout
        self.listeners = []
        self.waited = False

    def on(self, event, callback):
        self.listeners.append(callback)

    def remove_listener(self, event, callback):
        self.listeners.remove(callback)

    def emit(self, status):
        response = SimpleNamespace(
            status=status,
            frame=self.main_frame,
            request=SimpleNamespace(is_navigation_request=lambda: True),
        )
        for callback in self.listeners:
            callback(response)
        return response

    def goto(self, url, **kwargs):
        return self.emit(self.status)

    def content(self):
        return self.html

    def wait_for_function(self, script, **kwargs):
        self.waited = True
        if self.timeout:
            raise monitor.PlaywrightTimeoutError("synthetic timeout")
        if self.recovered:
            self.status, self.html = self.recovered
            self.emit(self.status)


class FMKoreaTests(unittest.TestCase):
    def test_initial_430_can_redirect_to_posts(self):
        page = Page(430, "<html>브라우저 확인 중</html>", recovered=(200, POSTS))
        items = monitor.read_fmkorea_page(page, monitor.FMKOREA_URLS[0])
        self.assertEqual(items[0]["title"], "테스트 게시물 제목")
        self.assertTrue(page.waited)
        self.assertEqual(page.listeners, [])

    def test_explicit_block_is_not_reported_as_empty_posts(self):
        page = Page(430, BLOCKED)
        with self.assertRaisesRegex(RuntimeError, "HTTP 430.*접속을 차단"):
            monitor.read_fmkorea_page(page, monitor.FMKOREA_URLS[0])
        self.assertFalse(page.waited)
        self.assertEqual(page.listeners, [])

    def test_430_without_posts_stays_a_failure(self):
        page = Page(430, "<html><title>Browser check</title></html>", timeout=True)
        with self.assertRaisesRegex(RuntimeError, "HTTP 430"):
            monitor.read_fmkorea_page(page, monitor.FMKOREA_URLS[0])
        self.assertEqual(page.listeners, [])

    def test_unfinished_human_verification_is_reported_after_waiting(self):
        html = """<html><title>에펨코리아 보안 시스템</title><body>
        사람인지 확인이 완료되면 사이트에 자동으로 접속됩니다.</body></html>"""
        page = Page(430, html, timeout=True)
        with self.assertRaisesRegex(RuntimeError, "HTTP 430.*사람 인증.*완료되지"):
            monitor.read_fmkorea_page(page, monitor.FMKOREA_URLS[0])
        self.assertTrue(page.waited)
        self.assertEqual(page.listeners, [])

    def test_empty_200_is_a_failure(self):
        page = Page(200, "<html>글 없음</html>", timeout=True)
        with self.assertRaisesRegex(RuntimeError, "HTTP 200, 게시물 0개"):
            monitor.read_fmkorea_page(page, monitor.FMKOREA_URLS[0])

    def test_title_links_are_preferred_and_document_ids_deduplicated(self):
        html = """<a href="/1000001">그림 미리보기</a>
        <h3 class="title"><a href="/best/1000001">정확한 게시물 제목</a></h3>
        <h3 class="title"><a href="/index.php?mid=best&amp;document_srl=1000001">중복 글 제목</a></h3>
        <h3 class="title"><a href="/index.php?document_srl=1000002">다음 게시물 제목</a></h3>"""
        items = monitor.parse_fmkorea(BeautifulSoup(html, "html.parser"), monitor.FMKOREA_URLS[0])
        self.assertEqual([x["title"] for x in items], ["정확한 게시물 제목", "다음 게시물 제목"])
        self.assertEqual([x["rank"] for x in items], [1, 2])
        self.assertTrue(all(x["views"] == 0 and x["reactions"] == 0 for x in items))

    def test_external_and_attachment_links_are_excluded(self):
        html = """<a href="https://fmkorea.com.evil.example/1000001">외부 사이트 링크</a>
        <a href="/files/attach/images/1000002">이미지 파일 링크</a>
        <a href="/1000003">실제 게시물 제목</a>"""
        items = monitor.parse_fmkorea(BeautifulSoup(html, "html.parser"), monitor.FMKOREA_URLS[0])
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["link"].endswith("/1000003"))

    def test_top10_limit(self):
        self.assertFalse(monitor.fmkorea_blocked(BeautifulSoup(
            POSTS + '<p>비정상 접속이 의심되어 차단</p>', 'html.parser'
        )))
        html = "".join(f'<a href="/{1000000 + n}">게시물 제목 {n}</a>' for n in range(40))
        items = monitor.parse_fmkorea(BeautifulSoup(html, "html.parser"), monitor.FMKOREA_URLS[0])
        self.assertEqual(len(items), 10)
        self.assertEqual(items[-1]["rank"], 10)

    def test_state_preserves_failure_reason_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data/state.json"
            with patch.object(monitor, "STATE_FILE", path):
                monitor.save_state({"펨코 포텐": []}, {"펨코 포텐": "HTTP 430"})
                state = json.loads(path.read_text())
                self.assertEqual(state["status"], "degraded")
                self.assertEqual(state["counts"]["펨코 포텐"], 0)
                self.assertEqual(state["errors"]["펨코 포텐"], "HTTP 430")
                monitor.save_state({"펨코 포텐": [{"title": "복구"}]})
                state = json.loads(path.read_text())
                self.assertEqual(state["status"], "ok")
                self.assertEqual(state["errors"], {})

    def test_hourly_run_reports_failure_and_saves_diagnostics(self):
        data = {name: [] for name in ["네이버 뉴스", "네이트 스포츠", "디시 실베", "펨코 포텐"]}
        errors = {"펨코 포텐": "HTTP 430"}
        with patch.object(monitor, "collect", return_value=(data, errors)), \
                patch.object(monitor, "telegram"), patch.object(monitor, "save_state") as save:
            self.assertEqual(monitor.main(), 1)
            save.assert_called_once_with(data, errors)

    def test_diagnostic_cli_never_sends_or_saves(self):
        with patch.object(monitor, "fetch_fmkorea", side_effect=RuntimeError("HTTP 430")), \
                patch.object(monitor, "telegram") as telegram, \
                patch.object(monitor, "save_state") as save, \
                patch.object(monitor, "main") as main:
            self.assertEqual(monitor.run_cli(["--check-fmkorea"]), 1)
            telegram.assert_not_called()
            save.assert_not_called()
            main.assert_not_called()

    def test_fallback_errors_close_browser(self):
        browser = Mock()
        playwright = Mock()
        playwright.chromium.launch.return_value = browser
        manager = Mock()
        manager.__enter__ = Mock(return_value=playwright)
        manager.__exit__ = Mock(return_value=False)
        with patch.object(monitor, "sync_playwright", return_value=manager), \
                patch.object(monitor, "read_fmkorea_page", side_effect=RuntimeError("HTTP 430")) as read:
            with self.assertRaisesRegex(RuntimeError, "HTTP 430"):
                monitor.fetch_fmkorea()
            self.assertEqual(read.call_count, 2)
            browser.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
