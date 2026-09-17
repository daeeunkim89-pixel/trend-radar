import os
import re
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# =========================================================
# 기본 설정
# =========================================================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = Path("data/state.json")
TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
}


# =========================================================
# 공통 함수
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
# 1. 네이버 많이 본 뉴스
# =========================================================

def fetch_naver_news():

    url = (
        "https://news.naver.com/"
        "main/ranking/popularDay.naver"
    )

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

        if len(result) >= 30:
            break

    return result


# =========================================================
# 2. 네이트 스포츠 조회순
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
            print("NATE SPORTS ERROR:", e)
            continue

        # 조회순 랭킹 영역 찾기
        heading = None

        for tag in soup.find_all(
            [
                "h2",
                "h3",
                "h4",
                "strong",
                "dt",
                "div",
            ]
        ):

            text = clean(
                tag.get_text(
                    " ",
                    strip=True,
                )
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
                        parent.select(
                            "a[href]"
                        )
                    )

                    parent = parent.parent

        # 랭킹 영역 탐색 실패 시 fallback
        if not candidates:
            candidates = soup.select(
                "a[href]"
            )

        for a in candidates:

            href = a.get("href", "")

            title = clean(
                a.get("title")
                or a.get_text(
                    " ",
                    strip=True,
                )
            )

            if len(title) < 8:
                continue

            link = urljoin(base, href)

            if (
                "sports.news.nate.com"
                not in link
            ):
                continue

            if not (
                "/view/" in link
                or "view?" in link
                or "/article/" in link
            ):
                continue

            key = re.sub(
                r"[?#].*$",
                "",
                link,
            )

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

            if len(result) >= 30:
                return result

    return result


# =========================================================
# 3. 디시 실시간 베스트
# =========================================================

def fetch_dc():

    urls = [
        (
            "https://gall.dcinside.com/"
            "board/lists/?id=dcbest"
        ),
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

        # PC 페이지
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
                chosen.get_text(
                    " ",
                    strip=True,
                )
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
                else re.sub(
                    r"[?#].*$",
                    "",
                    link,
                )
            )

            if key in seen:
                continue

            views = 0
            reactions = 0

            count_cell = row.select_one(
                ".gall_count, td.gall_count"
            )

            recommend_cell = row.select_one(
                ".gall_recommend, "
                "td.gall_recommend"
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

            if len(result) >= 30:
                return result

        # 모바일 fallback
        for a in soup.select("a[href]"):

            href = a.get("href", "")

            title = clean(
                a.get_text(
                    " ",
                    strip=True,
                )
            )

            if len(title) < 4:
                continue

            if "dcbest" not in href:
                continue

            m = re.search(
                r"(\d{4,})",
                href,
            )

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

            if len(result) >= 30:
                return result

    return result


# =========================================================
# 4. 펨코 포텐
# =========================================================

def parse_fmkorea(soup, base):

    result = []
    seen = set()

    for a in soup.select("a[href]"):

        href = a.get("href", "")

        title = clean(
            a.get("title")
            or a.get_text(
                " ",
                strip=True,
            )
        )

        if len(title) < 5:
            continue

        m = re.search(
            r"(?:document_srl=|/)"
            r"(\d{6,})",
            href,
        )

        if not m:
            continue

        key = m.group(1)

        if key in seen:
            continue

        seen.add(key)

        result.append(
            make_item(
                "펨코 포텐",
                title,
                urljoin(base, href),
                len(result) + 1,
            )
        )

        if len(result) >= 30:
            break

    return result


def fetch_fmkorea():

    urls = [
        "https://www.fmkorea.com/best",
        "https://m.fmkorea.com/best",
    ]

    errors = []

    for url in urls:

        try:

            soup = get_html(url)

            result = parse_fmkorea(
                soup,
                url,
            )

            if result:
                return result

            errors.append(
                f"{url} = 게시물 0개"
            )

        except Exception as e:

            errors.append(
                f"{url} = {e}"
            )

    raise RuntimeError(
        " / ".join(errors)
    )


# =========================================================
# 전체 수집
# =========================================================

def collect():

    sources = {
        "네이버 뉴스":
            fetch_naver_news,

        "네이트 스포츠":
            fetch_nate_sports,

        "디시 실베":
            fetch_dc,

        "펨코 포텐":
            fetch_fmkorea,
    }

    data = {}
    errors = {}

    for name, func in sources.items():

        try:

            items = func()

            data[name] = items[:30]

            print(
                name,
                len(data[name]),
            )

            if not items:
                errors[name] = (
                    "게시물 0개"
                )

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
# TOP30 전송
# =========================================================

def send_top30(name, items):

    if not items:

        telegram(
            f"📡 {name} TOP 0\n\n"
            "⚠️ 수집 실패 또는 "
            "게시물이 없습니다."
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
                f"조회 "
                f"{x['views']:,}"
            )

        if x.get("reactions"):
            metrics.append(
                f"추천 "
                f"{x['reactions']:,}"
            )

        if metrics:

            text += (
                "\n"
                + " · ".join(metrics)
            )

        text += (
            "\n"
            + x["link"]
        )

        lines.append(text)
        lines.append("")

    telegram(
        "\n".join(lines)
    )


# =========================================================
# 상태 파일
# =========================================================

def save_state(data):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    state = {
        "updated_at": int(
            time.time()
        ),
        "counts": {
            name: len(items)
            for name, items
            in data.items()
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
# 메인
# =========================================================

def main():

    print(
        "TREND RADAR HOURLY START"
    )

    data, errors = collect()

    # 먼저 전체 상태
    status = [
        "📡 TREND RADAR 시간별 보고",
        "",
        (
            "네이버 뉴스: "
            f"{len(data.get('네이버 뉴스', []))}/30"
        ),
        (
            "네이트 스포츠: "
            f"{len(data.get('네이트 스포츠', []))}/30"
        ),
        (
            "디시 실베: "
            f"{len(data.get('디시 실베', []))}/30"
        ),
        (
            "펨코 포텐: "
            f"{len(data.get('펨코 포텐', []))}/30"
        ),
    ]

    telegram(
        "\n".join(status)
    )

    # 사이트별 TOP30
    for name in [
        "네이버 뉴스",
        "네이트 스포츠",
        "디시 실베",
        "펨코 포텐",
    ]:

        send_top30(
            name,
            data.get(name, []),
        )

    # 실패 원인
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

    save_state(data)

    print(
        "TREND RADAR HOURLY COMPLETE"
    )

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


if __name__ == "__main__":
    main()
