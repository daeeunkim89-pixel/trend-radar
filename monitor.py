import argparse
import os
import re
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from editorial import HISTORY_FILE, atomic_json, enrich, load_history, observe, render_digest
from telegram_editor import PrivateState, TelegramClient, TelegramError, deliver_report, process_commands


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = Path("data/state.json")
TIMEOUT = 20
TOP_LIMIT = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-S948N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
}


# =========================================================
# 공통
# =========================================================

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def number(text):
    text = clean(text).replace(",", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(만|천|[kK])?", text)
    if not match:
        return None
    scale = {"만": 10000, "천": 1000, "k": 1000, "K": 1000}.get(match[2], 1)
    return int(float(match[1]) * scale)


def get_html(url):
    r = requests.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    print("GET", r.status_code, url)

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    return BeautifulSoup(r.text, "html.parser")


def make_item(
    source,
    title,
    link,
    rank,
    views=None,
    reactions=None,
):
    return {
        "source": source,
        "parser_revision": 2,
        "title": clean(title)[:220],
        "link": link,
        "rank": rank,
        "views": views,
        "reactions": reactions,
    }


# =========================================================
# 1. 네이버 뉴스
# =========================================================

def anchor_title(anchor):
    headline = anchor.select_one(".list_title, .subjectin, .subj, h2.tit, h2.title, strong.tit")
    return clean(anchor.get("title") or (headline.get_text(" ", strip=True) if headline else anchor.get_text(" ", strip=True)))


def parse_naver_news(soup, base):
    result, seen = [], set()
    for anchor in soup.select("a[href]"):
        link = urljoin(base, anchor["href"])
        parsed = urlsplit(link)
        if parsed.hostname not in {"news.naver.com", "n.news.naver.com", "m.news.naver.com"} or not re.search(r"/article/\d+/\d+", parsed.path):
            continue
        title = anchor_title(anchor)
        key = re.sub(r"[?#].*$", "", link)
        if len(title) < 8 or key in seen:
            continue
        seen.add(key)
        result.append(make_item("네이버 뉴스", title, link, len(result) + 1))
        if len(result) >= TOP_LIMIT:
            break
    return result


def fetch_naver_news():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    return parse_naver_news(get_html(url), url)


def parse_nate_sports(soup, base):
    # The sports interest-ranking widget is distinct from the general-news ranking.
    ranking = soup.select_one("#intNews2 #sport1")
    candidates = ranking.select("ol li a[href]") if ranking else []
    if not candidates:
        headings = [node for node in soup.find_all(["h2", "h3", "h4", "strong", "dt", "div"])
                    if "스포츠 조회순 랭킹뉴스" in clean(node.get_text(" ", strip=True))]
        if headings:
            parent = min(headings, key=lambda node: len(node.get_text())).parent
            for _ in range(4):
                if not parent:
                    break
                candidates = parent.select("a[href]")
                if len(candidates) >= TOP_LIMIT:
                    break
                parent = parent.parent
        if not candidates:
            candidates = soup.select("a[href]")
    result, seen = [], set()
    for anchor in candidates:
        link = urljoin(base, anchor.get("href", ""))
        parsed = urlsplit(link)
        if parsed.hostname not in {"sports.news.nate.com", "news.nate.com"} or "/view/" not in parsed.path:
            continue
        title = anchor_title(anchor)
        key = re.sub(r"[?#].*$", "", link)
        if len(title) < 8 or key in seen:
            continue
        seen.add(key)
        item = make_item("네이트 스포츠", title, link, len(result) + 1)
        if ranking:
            item["rank_kind"] = "nate_sports_interest"
        result.append(item)
        if len(result) >= TOP_LIMIT:
            break
    return result


def fetch_nate_sports():
    errors = []
    for url in ("https://sports.news.nate.com/", "https://sports.news.nate.com/general"):
        try:
            result = parse_nate_sports(get_html(url), url)
            if result:
                return result
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError(" / ".join(errors) or "스포츠 게시물 0개")


def parse_dc(soup, base):
    result, seen = [], set()
    for anchor in soup.select(".gall_tit a[href], .gall-detail-lnktb a.lt[href], a[href]"):
        link = urljoin(base, anchor.get("href", ""))
        parsed = urlsplit(link)
        if parsed.hostname not in {"gall.dcinside.com", "m.dcinside.com"}:
            continue
        query = parse_qs(parsed.query)
        mobile = re.fullmatch(r"/board/dcbest/(\d+)/?", parsed.path)
        key = mobile[1] if mobile else (query.get("no", [""])[0] if query.get("id") == ["dcbest"] else "")
        if not re.fullmatch(r"\d{4,}", key) or key in seen or parsed.fragment:
            continue
        row = anchor.find_parent("tr")
        number_cell = row.select_one(".gall_num") if row else None
        if anchor.select_one(".ntc-line-orange") or (number_cell and not clean(number_cell.get_text()).isdigit()):
            continue
        title = anchor_title(anchor)
        if len(title) < 4 or title.startswith("공지 "):
            continue
        views, reactions = None, None
        if row:
            count = row.select_one(".gall_count")
            recommend = row.select_one(".gall_recommend")
            views = number(count.get_text()) if count else None
            reactions = number(recommend.get_text()) if recommend else None
        for field in anchor.select("ul.ginfo li"):
            text = clean(field.get_text(" ", strip=True))
            if text.startswith("조회 "):
                views = number(text.removeprefix("조회 "))
            if text.startswith("추천 "):
                reactions = number(text.removeprefix("추천 "))
        seen.add(key)
        result.append(make_item("디시 실베", title, link, len(result) + 1, views, reactions))
        if len(result) >= TOP_LIMIT:
            break
    return result


def fetch_dc():
    errors = []
    for url in ("https://gall.dcinside.com/board/lists/?id=dcbest", "https://m.dcinside.com/board/dcbest"):
        try:
            result = parse_dc(get_html(url), url)
            if result:
                return result
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError(" / ".join(errors) or "실베 게시물 0개")


# =========================================================
# 4. 펨코 포텐 - Playwright
# =========================================================

FMKOREA_URLS = (
    "https://www.fmkorea.com/best",
    "https://m.fmkorea.com/best",
)
FMKOREA_HOSTS = {"fmkorea.com", "www.fmkorea.com", "m.fmkorea.com"}

# HTTP 응답 뒤에 브라우저 검사/리다이렉트가 이어질 수 있으므로 실제 글을 기다린다.
FMKOREA_READY = """
() => {
    const text = document.body ? document.body.innerText : "";
    if (text.includes("비정상 접속이 의심되어 차단")) return true;
    return Array.from(document.querySelectorAll("a[href]")).some(a => {
        const u = new URL(a.href, location.href);
        return ["fmkorea.com", "www.fmkorea.com", "m.fmkorea.com"].includes(u.hostname)
            && (/^\\/(?:best\\/)?\\d{6,}\\/?$/.test(u.pathname)
                || /^\\d{6,}$/.test(u.searchParams.get("document_srl") || ""));
    });
}
"""


def parse_fmkorea(soup, base):
    result = []
    seen = set()

    # 제목 링크가 있는 레이아웃에서는 썸네일/추천 링크보다 제목을 우선한다.
    candidates = soup.select(".title a[href], a.title[href]") or soup.select("a[href]")

    for a in candidates:
        href = a.get("href", "")
        title = clean(a.get("title") or a.get_text(" ", strip=True))
        link = urljoin(base, href)
        parsed = urlsplit(link)

        if parsed.scheme not in {"http", "https"} or parsed.hostname not in FMKOREA_HOSTS:
            continue
        if len(title) < 5:
            continue

        key = parse_qs(parsed.query).get("document_srl", [""])[0]
        if not re.fullmatch(r"\d{6,}", key):
            match = re.fullmatch(r"/(?:best/)?(\d{6,})/?", parsed.path)
            key = match.group(1) if match else ""
        if not key or key in seen:
            continue

        seen.add(key)
        result.append(make_item("펨코 포텐", title, link, len(result) + 1))
        if len(result) >= TOP_LIMIT:
            break

    return result


def fmkorea_blocked(soup):
    # 실제 차단 문구만 판별한다. HTTP 430 자체를 IP 차단이라고 단정하지 않는다.
    text = clean(soup.get_text(" ", strip=True))
    return "비정상 접속이 의심되어 차단" in text and not parse_fmkorea(soup, FMKOREA_URLS[0])


def read_fmkorea_page(page, url, wait_ms=15000):
    navigation = {"status": 0}

    def track_response(response):
        if response.request.is_navigation_request() and response.frame == page.main_frame:
            navigation["status"] = response.status

    page.on("response", track_response)
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if response:
            navigation["status"] = response.status

        print("FMKOREA PLAYWRIGHT", navigation["status"], url)

        initial = BeautifulSoup(page.content(), "html.parser")
        if not fmkorea_blocked(initial):
            try:
                page.wait_for_function(FMKOREA_READY, timeout=wait_ms)
            except PlaywrightTimeoutError:
                # 아래에서 HTTP 상태와 최종 페이지를 함께 진단한다.
                pass

        soup = BeautifulSoup(page.content(), "html.parser")
        status = navigation["status"]

        if fmkorea_blocked(soup):
            raise RuntimeError(
                f"{url} = HTTP {status}: 펨코 보안 시스템이 접속을 차단했습니다. "
                "현재 실행 환경의 접근 허용을 확인해야 합니다."
            )

        if status != 200:
            title = clean(soup.title.get_text())[:120] if soup.title else "제목 없음"
            text = clean(soup.get_text(" ", strip=True))
            print("FMKOREA FINAL PAGE", status, title, text[:200])
            if "에펨코리아 보안 시스템" in title and "사람인지 확인" in text:
                raise RuntimeError(
                    f"{url} = HTTP {status}: 펨코의 사람 인증 보안 확인이 완료되지 않았습니다. "
                    "현재 실행 환경에서 자동 수집 가능한지 사이트 측 확인이 필요합니다."
                )
            raise RuntimeError(f"{url} = HTTP {status} (최종 페이지: {title})")

        result = parse_fmkorea(soup, url)
        print("FMKOREA ITEMS", len(result))
        if not result:
            raise RuntimeError(f"{url} = HTTP 200, 게시물 0개")

        return result
    finally:
        page.remove_listener("response", track_response)


def fetch_fmkorea():
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        try:
            # 설치된 Chromium의 기본 UA를 쓴다. Android UA와 PC 화면을 섞지 않는다.
            context = browser.new_context(
                locale="ko-KR",
                extra_http_headers={"Accept-Language": HEADERS["Accept-Language"]},
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            for url in FMKOREA_URLS:
                try:
                    return read_fmkorea_page(page, url)
                except Exception as e:
                    print("FMKOREA ERROR:", e)
                    errors.append(str(e))
        finally:
            browser.close()

    raise RuntimeError(" / ".join(errors))


def check_fmkorea():
    """수집만 검사한다. 텔레그램 전송과 운영 상태 파일 변경은 하지 않는다."""
    try:
        items = fetch_fmkorea()
    except Exception as e:
        print("FMKOREA CHECK FAILED:", e)
        return 1

    print("FMKOREA CHECK OK:", len(items), "개")
    return 0


# =========================================================
# 전체 수집
# =========================================================

def collect():

    sources = {
        "네이버 뉴스": fetch_naver_news,
        "네이트 스포츠": fetch_nate_sports,
        "디시 실베": fetch_dc,
        "펨코 포텐": fetch_fmkorea,
    }

    data = {}
    errors = {}

    for name, func in sources.items():

        try:

            items = func()

            data[name] = items[:TOP_LIMIT]

            print(
                name,
                len(data[name]),
            )

            if not items:
                errors[name] = "게시물 0개"

        except Exception as e:

            data[name] = []
            errors[name] = str(e)

            print(
                name,
                "FAILED:",
                e,
            )

    return data, errors


# =========================================================
# 상태 저장
# =========================================================

def save_state(data, errors=None, report=None):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    state = {
        "updated_at": int(time.time()),
        "status": "degraded" if errors else "ok",
        "errors": errors or {},
        "counts": {
            name: len(items)
            for name, items in data.items()
        },
    }

    if report is not None:
        state["report"] = report

    with STATE_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )


# =========================================================
# 실행
# =========================================================

def main(commands_only=False, force_report=False):
    print("TREND RADAR BTP EDITOR START")
    try:
        history = load_history()
        client = TelegramClient(TOKEN, CHAT_ID)
        client.verify()
        private = PrivateState(TOKEN, CHAT_ID)
    except (TelegramError, ValueError, OSError) as error:
        print("BTP INITIALIZATION FAILED:", str(error))
        return 1

    command_error = None
    try:
        process_commands(client, private, history)
    except TelegramError as error:
        command_error = str(error)
        print("BTP COMMANDS FAILED:", command_error)
    if commands_only:
        return 1 if command_error else 0

    data, errors = collect()
    if command_error:
        errors["텔레그램 명령"] = command_error
    now = int(time.time())
    stories, history = observe(data, history, now)
    enrich(stories, history, now)
    atomic_json(HISTORY_FILE, history)
    report = {"version": "btp-v1.1", "stories": len(stories),
              "previews": sum(bool(x.get("detail", {}).get("excerpt")) for x in stories),
              "metrics": {name: {"views": sum(x.get("views") is not None for x in rows),
                                  "reactions": sum(x.get("reactions") is not None for x in rows),
                                  "ranking": sum(bool(x.get("rank_kind")) for x in rows)} for name, rows in data.items()},
              "ai": "not_connected", "delivery": "pending"}
    parts = render_digest(stories, {name: len(rows) for name, rows in data.items()}, errors, private.data, now)
    report_key = "hourly-" + datetime.fromtimestamp(now, timezone.utc).strftime("%Y%m%d%H")
    if force_report:
        report_key = "manual-" + os.environ.get("GITHUB_RUN_ID", str(now))
    try:
        sent = deliver_report(client, parts, private, report_key, now)
        report.update(delivery="sent" if sent else "already_sent", messages=sent)
    except TelegramError as error:
        errors["텔레그램 전송"] = str(error)
        report["delivery"] = "failed"
        print("BTP DELIVERY FAILED:", str(error))
    save_state(data, errors, report)
    print("BTP REPORT", json.dumps(report, ensure_ascii=False))
    print("TREND RADAR BTP EDITOR COMPLETE")
    return 1 if errors else 0


def run_cli(argv=None):
    parser = argparse.ArgumentParser(description="Trend Radar 수집기")
    parser.add_argument(
        "--check-fmkorea",
        action="store_true",
        help="펨코 수집만 검사 (텔레그램 전송/상태 저장 없음)",
    )
    parser.add_argument("--commands-only", action="store_true", help="텔레그램 선정 명령만 점검")
    parser.add_argument("--force-report", action="store_true", help="같은 시간대에도 별도 보고서 전송")
    args = parser.parse_args(argv)
    if args.check_fmkorea:
        return check_fmkorea()
    return main(commands_only=args.commands_only, force_report=args.force_report)


if __name__ == "__main__":
    raise SystemExit(run_cli())


