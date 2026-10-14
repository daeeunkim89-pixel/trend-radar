"""로컬 HTTP 서버로 검증한다. 실제 펨코 접속은 별도 CLI 검사에서 수행한다."""
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright

import monitor


POSTS = """<html><body>
<a href="https://www.fmkorea.com/1000001">브라우저 테스트 게시물</a>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status = 200
        if self.path == "/recover":
            status = 430
            body = """<html><body>브라우저 확인 중
            <script>setTimeout(() => location.href = '/posts', 100)</script></body></html>"""
        elif self.path == "/blocked":
            status = 430
            body = "<html><body>비정상 접속이 의심되어 차단되었습니다.</body></html>"
        elif self.path == "/empty":
            body = "<html><body>게시물 없음</body></html>"
        else:
            body = POSTS
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


@unittest.skipUnless(os.environ.get("TREND_RADAR_BROWSER_TESTS") == "1", "Chromium integration is opt-in")
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True, args=["--no-sandbox"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def test_browser_executes_redirect_after_initial_430(self):
        items = monitor.read_fmkorea_page(self.page, self.base + "/recover", wait_ms=3000)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "브라우저 테스트 게시물")

    def test_persistent_block_is_failure(self):
        with self.assertRaisesRegex(RuntimeError, "HTTP 430.*접속을 차단"):
            monitor.read_fmkorea_page(self.page, self.base + "/blocked", wait_ms=3000)

    def test_200_without_posts_is_failure(self):
        with self.assertRaisesRegex(RuntimeError, "게시물 0개"):
            monitor.read_fmkorea_page(self.page, self.base + "/empty", wait_ms=200)


if __name__ == "__main__":
    unittest.main()
