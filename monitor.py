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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-S948N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
}

TIMEOUT = 20


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


def make_item(source, title, link, rank, views=0, reactions=0):

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

    # 텔레그램 길이 제한 대비
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

    url = "https://news.naver.com/main/ranking/popularDay.naver"

    soup = get_html(url)

    result = []
    seen = set()

    selectors = [
        "a.list_title",
        "a[href*='/article/']",
    ]

    for selector in selectors:

        for a in soup.select(selector):

            title = clean(
                a.get("title")
                or a.get_text(" ", strip=True)
            )

            href = a.get("href", "")

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
            soup = get_html(base)

        except Exception as e:
            print("NAVER SPORTS ERROR:", e)
            continue

        for a in soup.select("a[href]"):

            href = a.get("href", "")

            title = clean(
                a.get("aria-label")
                or a.get("title")
                or a.get_text(" ", strip=True)
            )

            if len(title) < 8:
                continue

            link = urljoin(base, href)

            # 스포츠 기사로 보이는 주소만 허용
            if not (
                "/article/" in link
                or "/news/" in link
                or "sports.news.naver.com" in link
            ):
                continue

            key = re.sub(r"[?#].*$", "", link)

            if key in seen:
                continue

            seen.add(key)

            result.append(
                make_item(
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

        # PC 목록
        rows = soup.select("tr")

        for row in rows:

            anchors = row.select("a[href]")

            chosen = None

            for a in anchors:

                href = a.get("href", "")

                if "dcbest" in href and (
                    "no=" in href
                    or "/view" in href
                ):
                    chosen = a
                    break

            if not chosen:
                continue

            title = clean(chosen.get_text(" ", strip=True))

            if len(title) < 4:
                continue

            link = urljoin(base, chosen.get("href", ""))

            key_match = re.search(r"(?:no=|/)(\d{4,})", link)

            key = (
                key_match.group(1)
                if key_match
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
                views = number(count_cell.get_text())

            if recommend_cell:
                reactions = number(recommend_cell.get_text())

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

        # 모바일 페이지 fallback
        for a in soup.select("a[href]"):

            href = a.get("href", "")
            title = clean(a.get_text(" ", strip=True))

            if len(title) < 4:
                continue

            if "dcbest" not in href:
                continue

            if not re.search(r"\d+", href):
                continue

            link = urljoin(base, href)

            key_match = re.search(r"(\d{4,})", href)

            if not key_match:
                continue

            key = key_match.group(1)

            if key in seen:
                continue

            seen.add(key)

            result.append(
                make_item(
                    "디시 실베",
                    title,
                    link,
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
            or a.get_text(" ", strip=True)
        )

        if len(title) < 5:
            continue

        # 펨코 게시글 번호가 들어간 주소
        match = re.search(
            r"(?:document_srl=|/)(\d{6,})",
            href,
        )

        if not match:
            continue

        key = match.group(1)

        if key in seen:
            continue

        link = urljoin(base, href)

        seen.add(key)

        result.append(
            make_item(
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

    urls = [
        "https://www.fmkorea.com/best",
        "https://m.fmkorea.com/best",
    ]

    errors = []

    for url in urls:

        try:
            soup = get_html(url)

            result = parse_fmkorea(soup, url)

            if result:
                return result

            errors.append(f"{url} = 게시물 0개")

        except Exception as e:
            errors.append(f"{url} = {e}")

    raise RuntimeError(" / ".join(errors))


# =========================================================
# 전체 수집
# =========================================================

def collect():

    sources = {
        "네이버 뉴스": fetch_naver_news,
        "네이버 스포츠": fetch_naver_sports,
        "디시 실베": fetch_dc,
        "펨코 포텐": fetch_fmkorea,
    }

    data = {}
    errors = {}

    for name, func in sources.items():

        try:

            items = func()

            data[name] = items[:30]

            print(name, len(data[name]))

            if not items:
                errors[name] = "게시물 0개"

        except Exception as e:

            data[name] = []
            errors[name] = str(e)

            print(name, "FAILED:", e)

    return data, errors


# =========================================================
# 상태 파일
# =========================================================

def load_state():

    try:

        if STATE_FILE.exists():

            with STATE_FILE.open(
                "r",
                encoding="utf-8",
            ) as f:

                state = json.load(f)

                if isinstance(state, dict):
                    return state

    except Exception as e:
        print("STATE LOAD ERROR:", e)

    return {}


def save_state(state):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
# TOP 30 보고
# =========================================================

def send_top30(name, items):

    if not items:

        telegram(
            f"📡 {name} TOP 0\n\n"
            f"⚠️ 수집된 게시물이 없습니다."
        )

        return

    lines = [
        f"📡 {name} TOP {len(items)}",
        "",
    ]

    for x in items:

        line = (
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
            line += "\n" + " · ".join(metrics)

        line += "\n" + x["link"]

        lines.append(line)
        lines.append("")

    telegram("\n".join(lines))


# =========================================================
# 급상승 감지
# =========================================================

def snapshot(data):

    result = {}

    for source, items in data.items():

        result[source] = {}

        for x in items:

            result[source][x["link"]] = {
                "rank": x["rank"],
                "views": x.get("views", 0),
                "reactions": x.get(
                    "reactions",
                    0,
                ),
                "title": x["title"],
            }

    return result


def detect_trends(data, old_snapshot):

    alerts = []

    for source, items in data.items():

        old_source = old_snapshot.get(
            source,
            {},
        )

        for x in items:

            old = old_source.get(x["link"])

            if not old:
                continue

            score = 0
            reasons = []

            old_rank = old.get("rank", 999)
            new_rank = x["rank"]

            jump = old_rank - new_rank

            if jump >= 10:
                score += 50
                reasons.append(
                    f"순위 +{jump}"
                )

            elif jump >= 5:
                score += 30
                reasons.append(
                    f"순위 +{jump}"
                )

            view_diff = (
                x.get("views", 0)
                - old.get("views", 0)
            )

            if view_diff >= 5000:
                score += 50
                reasons.append(
                    f"조회 +{view_diff:,}"
                )

            elif view_diff >= 1500:
                score += 30
                reasons.append(
                    f"조회 +{view_diff:,}"
                )

            reaction_diff = (
                x.get("reactions", 0)
                - old.get("reactions", 0)
            )

            if reaction_diff >= 100:
                score += 40
                reasons.append(
                    f"추천 +{reaction_diff:,}"
                )

            elif reaction_diff >= 30:
                score += 20
                reasons.append(
                    f"추천 +{reaction_diff:,}"
                )

            if score >= 50:

                alerts.append(
                    {
                        "score": score,
                        "source": source,
                        "title": x["title"],
                        "link": x["link"],
                        "rank": new_rank,
                        "reasons": reasons,
                    }
                )

    alerts.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return alerts


# =========================================================
# 실행
# =========================================================

def main():

    print("TREND RADAR START")

    now = int(time.time())

    state = load_state()

    old_snapshot = state.get(
        "snapshot",
        {},
    )

    data, errors = collect()

    # -------------------------
    # 급상승
    # -------------------------

    alerts = detect_trends(
        data,
        old_snapshot,
    )

    sent_alerts = state.get(
        "sent_alerts",
        {},
    )

    for alert in alerts[:10]:

        key = alert["link"]

        last_sent = sent_alerts.get(
            key,
            0,
        )

        # 같은 글 30분 중복 방지
        if now - last_sent < 1800:
            continue

        reasons = ", ".join(
            alert["reasons"]
        )

        telegram(
            "🚨 급상승 감지\n\n"
            f"[{alert['source']}]\n"
            f"{alert['title']}\n\n"
            f"현재 {alert['rank']}위\n"
            f"{reasons}\n"
            f"Trend Score "
            f"{alert['score']}\n\n"
            f"{alert['link']}"
        )

        sent_alerts[key] = now

    # -------------------------
    # 한국 시간 기준 시간별 보고
    # -------------------------

    korea = time.gmtime(
        now + 9 * 3600
    )

    hour_key = time.strftime(
        "%Y-%m-%d-%H",
        korea,
    )

    last_hour = state.get(
        "last_hour_report"
    )

    if last_hour != hour_key:

        status = [
            "📡 TREND RADAR 시간별 보고",
            "",
        ]

        for name in [
            "네이버 뉴스",
            "네이버 스포츠",
            "디시 실베",
            "펨코 포텐",
        ]:

            count = len(
                data.get(name, [])
            )

            status.append(
                f"{name}: {count}/30"
            )

        telegram(
            "\n".join(status)
        )

        for name in [
            "네이버 뉴스",
            "네이버 스포츠",
            "디시 실베",
            "펨코 포텐",
        ]:

            send_top30(
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

        state["last_hour_report"] = (
            hour_key
        )

    # -------------------------
    # 상태 저장
    # -------------------------

    # 오래된 중복 알림 기록 삭제
    sent_alerts = {
        k: v
        for k, v in sent_alerts.items()
        if now - v < 86400
    }

    state["sent_alerts"] = sent_alerts
    state["snapshot"] = snapshot(data)
    state["updated_at"] = now

    save_state(state)

    print("TREND RADAR COMPLETE")

    for name, items in data.items():
        print(name, len(items))

    if errors:
        print("ERRORS:", errors)


if __name__ == "__main__":
    main()
