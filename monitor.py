import argparse
import os
import re
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


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
    m = re.search(r"(\d+)", text)

    if not m:
        return 0

    try:
        return int(m.group(1))
    except Exception:
        return 0


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
    views=0,
    reactions=0,
):
    return {
        "source": source,
        "title": clean(title),
        "link": link,
        "rank": rank,
        "views": views,
        "reactions": reactions,
    }


# =========================================================
# 텔레그램
# =========================================================

def telegram(text):

    if not TOKEN or not CHAT_ID:
        print("TELEGRAM SECRET MISSING")
        return

    chunks = []

    while len(text) > 3800:

        cut = text.rfind("\n", 0, 3800)

        if cut < 100:
            cut = 3800

        chunks.append(text[:cut])
        text = text[cut:].lstrip()

    if text:
        chunks.append(text)

    for chunk in chunks:

        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=TIMEOUT,
        )

        print("TELEGRAM", r.status_code)
        time.sleep(0.3)


# =========================================================
# 1. 네이버 뉴스
# =========================================================

def fetch_naver_news():

    url = "https://news.naver.com/main/ranking/popularDay.naver"

    soup = get_html(url)

    result = []
    seen = set()

    for a in soup.select("a[href]"):

        href = a.get("href", "")

        title = clean(
            a.get("title")
            or a.get_text(" ", strip=True)
        )

        if len(title) < 8:
            continue

        link = urljoin(url, href)

        if "/article/" not in link:
            continue

        key = re.sub(r"[?#].*$", "", link)

        if key in seen:
            continue

        seen.add(key)

        result.append(
            make_item(
                "네이버 뉴스",
                title,
                link,
                len(result) + 1,
            )
        )

        if len(result) >= TOP_LIMIT:
            break

    return result


# =========================================================
# 2. 네이트 스포츠
# =========================================================

def fetch_nate_sports():

    urls = [
        "https://sports.news.nate.com/",
        "https://sports.news.nate.com/general",
        "https://sports.news.nate.com/soccer",
        "https://sports.news.nate.com/baseball",
    ]

    result = []
    seen = set()

    for base in urls:

        try:
            soup = get_html(base)

        except Exception as e:
            print("NATE ERROR:", e)
            continue

        heading = None

        for tag in soup.find_all(
            ["h2", "h3", "h4", "strong", "dt", "div"]
        ):

            text = clean(
                tag.get_text(" ", strip=True)
            )

            if "스포츠 조회순 랭킹뉴스" in text:
                heading = tag
                break

        candidates = []

        if heading:

            parent = heading.parent

            for _ in range(4):

                if parent:

                    candidates.extend(
                        parent.select("a[href]")
                    )

                    parent = parent.parent

        if not candidates:
            candidates = soup.select("a[href]")

        for a in candidates:

            href = a.get("href", "")

            title = clean(
                a.get("title")
                or a.get_text(" ", strip=True)
            )

            if len(title) < 8:
                continue

            link = urljoin(base, href)

            if "sports.news.nate.com" not in link:
                continue

            if not (
                "/view/" in link
                or "view?" in link
                or "/article/" in link
            ):
                continue

            key = re.sub(r"[?#].*$", "", link)

            if key in seen:
                continue

            seen.add(key)

            result.append(
                make_item(
                    "네이트 스포츠",
                    title,
                    link,
                    len(result) + 1,
                )
            )

            if len(result) >= TOP_LIMIT:
                return result

    return result


# =========================================================
# 3. 디시 실베
# =========================================================

def fetch_dc():

    urls = [
        "https://gall.dcinside.com/board/lists/?id=dcbest",
        "https://m.dcinside.com/board/dcbest",
    ]

    result = []
    seen = set()

    for base in urls:

        try:
            soup = get_html(base)

        except Exception as e:
            print("DC ERROR:", e)
            continue

        # PC
        for row in soup.select("tr"):

            chosen = None

            for a in row.select("a[href]"):

                href = a.get("href", "")

                if (
                    "dcbest" in href
                    and (
                        "no=" in href
                        or "/view" in href
                    )
                ):
                    chosen = a
                    break

            if not chosen:
                continue

            title = clean(
                chosen.get_text(" ", strip=True)
            )

            if len(title) < 4:
                continue

            link = urljoin(
                base,
                chosen.get("href", ""),
            )

            m = re.search(
                r"(?:no=|/)(\d{4,})",
                link,
            )

            key = (
                m.group(1)
                if m
                else re.sub(r"[?#].*$", "", link)
            )

            if key in seen:
                continue

            views = 0
            reactions = 0

            count_cell = row.select_one(
                ".gall_count, td.gall_count"
            )

            recommend_cell = row.select_one(
                ".gall_recommend, td.gall_recommend"
            )

            if count_cell:
                views = number(
                    count_cell.get_text()
                )

            if recommend_cell:
                reactions = number(
                    recommend_cell.get_text()
                )

            seen.add(key)

            result.append(
                make_item(
                    "디시 실베",
                    title,
                    link,
                    len(result) + 1,
                    views,
                    reactions,
                )
            )

            if len(result) >= TOP_LIMIT:
                return result

        # 모바일 fallback
        for a in soup.select("a[href]"):

            href = a.get("href", "")

            title = clean(
                a.get_text(" ", strip=True)
            )

            if len(title) < 4:
                continue

            if "dcbest" not in href:
                continue

            m = re.search(r"(\d{4,})", href)

            if not m:
                continue

            key = m.group(1)

            if key in seen:
                continue

            seen.add(key)

            result.append(
                make_item(
                    "디시 실베",
                    title,
                    urljoin(base, href),
                    len(result) + 1,
                )
            )

            if len(result) >= TOP_LIMIT:
                return result

    return result


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
# TOP10 전송
# =========================================================

def send_top10(name, items):

    items = items[:TOP_LIMIT]

    if not items:

        telegram(
            f"📡 {name} TOP 0\n\n"
            "⚠️ 수집 실패 또는 게시물이 없습니다."
        )

        return

    lines = [
        f"📡 {name} TOP {len(items)}",
        "",
    ]

    for x in items:

        text = (
            f"{x['rank']}. "
            f"{x['title']}"
        )

        metrics = []

        if x.get("views"):
            metrics.append(
                f"조회 {x['views']:,}"
            )

        if x.get("reactions"):
            metrics.append(
                f"추천 {x['reactions']:,}"
            )

        if metrics:
            text += (
                "\n"
                + " · ".join(metrics)
            )

        text += "\n" + x["link"]

        lines.append(text)
        lines.append("")

    telegram(
        "\n".join(lines)
    )


# =========================================================
# 상태 저장
# =========================================================

def save_state(data, errors=None):

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

def main():

    print("TREND RADAR HOURLY V4 START")

    data, errors = collect()

    status = [
        "📡 TREND RADAR 시간별 보고",
        "",
        f"네이버 뉴스: "
        f"{len(data.get('네이버 뉴스', []))}/{TOP_LIMIT}",
        f"네이트 스포츠: "
        f"{len(data.get('네이트 스포츠', []))}/{TOP_LIMIT}",
        f"디시 실베: "
        f"{len(data.get('디시 실베', []))}/{TOP_LIMIT}",
        f"펨코 포텐: "
        f"{len(data.get('펨코 포텐', []))}/{TOP_LIMIT}",
    ]

    telegram(
        "\n".join(status)
    )

    for name in [
        "네이버 뉴스",
        "네이트 스포츠",
        "디시 실베",
        "펨코 포텐",
    ]:

        send_top10(
            name,
            data.get(name, []),
        )

    if errors:

        lines = [
            "⚠️ 수집 상태",
            "",
        ]

        for name, error in errors.items():

            lines.append(
                f"{name}: {error}"
            )

        telegram(
            "\n".join(lines)
        )

    save_state(data, errors)

    print("TREND RADAR HOURLY V4 COMPLETE")

    for name, items in data.items():

        print(
            name,
            len(items),
        )

    if errors:
        print(
            "ERRORS:",
            errors,
        )

    return 1 if errors else 0


def run_cli(argv=None):
    parser = argparse.ArgumentParser(description="Trend Radar 수집기")
    parser.add_argument(
        "--check-fmkorea",
        action="store_true",
        help="펨코 수집만 검사 (텔레그램 전송/상태 저장 없음)",
    )
    args = parser.parse_args(argv)
    return check_fmkorea() if args.check_fmkorea else main()


if __name__ == "__main__":
    raise SystemExit(run_cli())

