import os
import re
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# =========================================================
# TREND RADAR V2
# - 5분마다 실행
# - 매시간 사이트별 TOP 30 텔레그램 전송
# - 신규/급상승 감시
# - 수집 실패도 텔레그램 보고
# =========================================================

STATE_FILE = Path("data/state.json")
STATE_FILE.parent.mkdir(exist_ok=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-S948N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


# =========================================================
# 공통
# =========================================================

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def number(text):
    if not text:
        return None

    text = clean(text).replace(",", "")

    m = re.search(r"([\d.]+)\s*(만|천)?", text)

    if not m:
        return None

    try:
        value = float(m.group(1))
    except ValueError:
        return None

    if m.group(2) == "만":
        value *= 10000

    if m.group(2) == "천":
        value *= 1000

    return int(value)


def get(url):
    r = session.get(url, timeout=20)
    print("GET", r.status_code, url)

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    return BeautifulSoup(r.text, "lxml")


def send(text):
    if not TOKEN or not CHAT_ID:
        print("텔레그램 설정 없음")
        return

    # 텔레그램 메시지 길이 안전하게 분할
    chunks = []

    while len(text) > 3800:
        cut = text.rfind("\n", 0, 3800)

        if cut < 1000:
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
            timeout=20,
        )

        print("TELEGRAM", r.status_code)
        r.raise_for_status()
        time.sleep(0.7)


def item(source, title, url, rank, views=None, reactions=None):
    return {
        "source": source,
        "title": clean(title)[:200],
        "url": url,
        "rank": rank,
        "views": views,
        "reactions": reactions,
    }


# =========================================================
# 1. 네이버 뉴스
# =========================================================

def fetch_naver_news():

    url = "https://news.naver.com/main/ranking/popularDay.naver"

    soup = get(url)

    result = []
    seen = set()

    selectors = [
        "a.list_title",
        "a[href*='/article/']",
    ]

    for selector in selectors:

        for a in soup.select(selector):

            title = clean(a.get_text(" ", strip=True))
            href = a.get("href", "")

            if not title or not href:
                continue

            link = urljoin(url, href)

            if "/article/" not in link:
                continue

            # 중복 기사 제거
            key = re.sub(r"[?#].*$", "", link)

            if key in seen:
                continue

            seen.add(key)

            result.append(
                item(
                    "네이버 뉴스",
                    title,
                    link,
                    len(result) + 1,
                )
            )

            if len(result) >= 30:
                return result

    return result


# =========================================================
# 2. 네이버 스포츠
# =========================================================

def fetch_naver_sports():

    urls = [
        "https://m.sports.naver.com/",
        "https://sports.naver.com/",
    ]

    result = []
    seen = set()

    for base in urls:

        try:
            soup = get(base)
        except Exception as e:
            print("NAVER SPORTS URL FAIL", base, repr(e))
            continue

        for a in soup.select("a[href]"):

            title = clean(
                a.get("aria-label")
                or a.get("title")
                or a.get_text(" ", strip=True)
            )

            href = a.get("href", "")

            if len(title) < 8:
                continue

            link = urljoin(base, href)

            # 네이버 스포츠 기사 주소 유형
            if not (
                "/article/" in link
                or "sports.news.naver.com" in link
            ):
                continue

            if link in seen:
                continue

            seen.add(link)

            result.append(
                item(
                    "네이버 스포츠",
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

    url = (
        "https://gall.dcinside.com/board/lists/"
        "?id=dcbest&page=1&list_num=100"
    )

    soup = get(url)

    result = []
    seen = set()

    # 현재 PC 목록
    rows = soup.select("tr.ub-content")

    print("DC ROWS", len(rows))

    for row in rows:

        title_cell = row.select_one("td.gall_tit")

        if not title_cell:
            continue

        links = title_cell.select("a[href]")

        a = None

        for candidate in links:
            href = candidate.get("href", "")

            if "view" in href or "no=" in href:
                a = candidate
                break

        if not a and links:
            a = links[0]

        if not a:
            continue

        title = clean(a.get_text(" ", strip=True))

        if not title:
            continue

        # 공지 제외
        if "공지" in title and len(result) == 0:
            continue

        link = urljoin(url, a.get("href", ""))

        if link in seen:
            continue

        seen.add(link)

        view_el = row.select_one("td.gall_count")
        rec_el = row.select_one("td.gall_recommend")

        views = number(
            view_el.get_text(strip=True)
            if view_el else ""
        )

        reactions = number(
            rec_el.get_text(strip=True)
            if rec_el else ""
        )

        result.append(
            item(
                "디시 실베",
                title,
                link,
                len(result) + 1,
                views,
                reactions,
            )
        )

        if len(result) >= 30:
            break

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
            or a.get_text(" ", strip=True)
        )

        if len(title) < 8:
            continue

        link = urljoin(base, href)

        # 게시글 번호 포함 주소
        if not re.search(r"/\d{5,}", link):
            continue

        if link in seen:
            continue

        # 이미지/메뉴성 텍스트 제거
        lowered = title.lower()

        if lowered in {
            "로그인",
            "회원가입",
            "검색",
        }:
            continue

        seen.add(link)

        result.append(
            item(
                "펨코 포텐",
                title,
                link,
                len(result) + 1,
            )
        )

        if len(result) >= 30:
            break

    return result


def fetch_fmkorea():

    # 여러 주소 순차 시도
    candidates = [
        "https://www.fmkorea.com/best",
        "https://m.fmkorea.com/best",
    ]

    errors = []

    for url in candidates:

        try:
            soup = get(url)

            result = parse_fmkorea(soup, url)

            if result:
                return result

        except Exception as e:
            errors.append(f"{url} = {e}")
            print("FM FAIL", url, repr(e))

    raise RuntimeError(
        " / ".join(errors)
        if errors
        else "게시물을 찾지 못함"
    )


# =========================================================
# 전체 수집
# =========================================================

FETCHERS = [
    ("네이버 뉴스", fetch_naver_news),
    ("네이버 스포츠", fetch_naver_sports),
    ("디시 실베", fetch_dc),
    ("펨코 포텐", fetch_fmkorea),
]


def collect():

    data = {}
    errors = {}

    for name, func in FETCHERS:

        try:
            rows = func()
            data[name] = rows

            print(
                "RESULT",
                name,
                len(rows),
            )

            if len(rows) == 0:
                errors[name] = "게시물 0개"

        except Exception as e:

            print(
                "ERROR",
                name,
                repr(e),
            )

            data[name] = []
            errors[name] = str(e)

    return data, errors


# =========================================================
# STATE
# =========================================================

def load_state():

    try:
        return json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )

    except Exception:
        return {}


def save_state(state):

    STATE_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# =========================================================
# TOP 30 보고서
# =========================================================

def report_source(name, rows):

    lines = [
        f"📡 {name} TOP {len(rows)}",
        "",
    ]

    if not rows:
        lines.append("⚠️ 수집된 게시물이 없습니다.")
        return "\n".join(lines)

    for x in rows[:30]:

        extra = []

        if x.get("views") is not None:
            extra.append(
                f"조회 {x['views']:,}"
            )

        if x.get("reactions") is not None:
            extra.append(
                f"추천 {x['reactions']:,}"
            )

        stat = ""

        if extra:
            stat = " · " + " / ".join(extra)

        lines.append(
            f"{x['rank']}. {x['title']}{stat}"
        )

        lines.append(
            x["url"]
        )

        lines.append("")

    return "\n".join(lines)


# =========================================================
# 급상승 감지
# =========================================================

def make_key(x):
    return x["source"] + "|" + x["url"]


def detect_trends(old_state, data):

    previous = old_state.get(
        "snapshot",
        {}
    )

    alerts = []

    for source, rows in data.items():

        for x in rows:

            key = make_key(x)

            old = previous.get(key)

            if not old:
                continue

            score = 0
            reasons = []

            old_rank = old.get("rank")
            new_rank = x.get("rank")

            if old_rank and new_rank:

                jump = old_rank - new_rank

                if jump >= 10:
                    score += 50
                    reasons.append(
                        f"순위 {old_rank}→{new_rank}"
                    )

                elif jump >= 5:
                    score += 30
                    reasons.append(
                        f"순위 {old_rank}→{new_rank}"
                    )

            old_views = old.get("views")
            new_views = x.get("views")

            if (
                old_views is not None
                and new_views is not None
            ):

                diff = new_views - old_views

                if diff >= 5000:
                    score += 50
                    reasons.append(
                        f"조회 +{diff:,}"
                    )

                elif diff >= 1500:
                    score += 30
                    reasons.append(
                        f"조회 +{diff:,}"
                    )

            old_rec = old.get("reactions")
            new_rec = x.get("reactions")

            if (
                old_rec is not None
                and new_rec is not None
            ):

                diff = new_rec - old_rec

                if diff >= 100:
                    score += 40
                    reasons.append(
                        f"추천 +{diff:,}"
                    )

                elif diff >= 30:
                    score += 20
                    reasons.append(
                        f"추천 +{diff:,}"
                    )

            if score >= 50:

                alerts.append(
                    (
                        score,
                        x,
                        reasons,
                    )
                )

    return sorted(
        alerts,
        key=lambda z: z[0],
        reverse=True,
    )


def build_snapshot(data):

    snapshot = {}

    for rows in data.values():

        for x in rows:
            snapshot[make_key(x)] = x

    return snapshot


# =========================================================
# MAIN
# =========================================================

def main():

    print("===== TREND RADAR V2 =====")

    now = time.time()

    state = load_state()

    data, errors = collect()

    # -----------------------------------------
    # 급상승
    # -----------------------------------------

    trends = detect_trends(
        state,
        data,
    )

    last_alerts = state.get(
        "last_alerts",
        {}
    )

    for score, x, reasons in trends[:10]:

        key = make_key(x)

        last = last_alerts.get(
            key,
            0,
        )

        # 같은 글 30분 중복 방지
        if now - last < 1800:
            continue

        icon = (
            "🚨 폭발"
            if score >= 80
            else "🔥 급상승"
        )

        send(
            f"{icon} · TREND {min(score,100)}\n\n"
            f"[{x['source']}]\n"
            f"{x['title']}\n\n"
            f"{' / '.join(reasons)}\n"
            f"{x['url']}"
        )

        last_alerts[key] = now

    # -----------------------------------------
    # 매시간 TOP30
    # -----------------------------------------

    hour_key = time.strftime(
        "%Y-%m-%d-%H",
        time.gmtime(
            now + 9 * 3600
        ),
    )

    last_hour = state.get(
        "last_hour_report"
    )

    if last_hour != hour_key:

        send(
            "📡 TREND RADAR 시간별 보고\n\n"
            f"📰 네이버 뉴스: {len(data['네이버 뉴스'])}/30\n"
            f"⚽ 네이버 스포츠: {len(data['네이버 스포츠'])}/30\n"
            f"💬 디시 실베: {len(data['디시 실베'])}/30\n"
            f"🔥 펨코 포텐: {len(data['펨코 포텐'])}/30"
        )

        for name, rows in data.items():

            send(
                report_source(
                    name,
                    rows,
                )
            )

        # 실패한 사이트도 반드시 알려줌
        if errors:

            lines = [
                "⚠️ 수집 상태",
                "",
            ]

            for name, error in errors.items():

                lines.append(
                    f"{name}: {error}"
                )

            send(
                "\n".join(lines)
            )

        state["last_hour_report"] = hour_key

    # -----------------------------------------
    # 저장
    # -----------------------------------------

    state["snapshot"] = build_snapshot(
        data
    )

    state["last_alerts"] = last_alerts

    state["updated"] = int(now)

    save_state(state)

    print("")
    print("===== RESULT =====")

    for name, rows in data.items():
        print(
            name,
            len(rows),
        )

    print(
        "급상승",
        len(trends),
    )

    print(
        "시간보고",
        hour_key,
    )


if __name__ == "__main__":
    main()
