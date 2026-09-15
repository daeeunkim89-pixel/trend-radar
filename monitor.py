=import json
import os
import re
import time
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

STATE = Path("data/state.json")
STATE.parent.mkdir(exist_ok=True)

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

SOURCES = {
    "네이버 뉴스": "https://news.naver.com/main/ranking/popularDay.naver",
    "네이버 스포츠": "https://m.sports.naver.com/",
    "디시 실베": "https://gall.dcinside.com/board/lists/?id=dcbest",
    "펨코 포텐": "https://www.fmkorea.com/best",
}


def num(s):
    if not s:
        return None

    s = s.replace(",", "")
    m = re.search(r"([\d.]+)\s*(만|천)?", s)

    if not m:
        return None

    try:
        n = float(m.group(1))
    except ValueError:
        return None

    if m.group(2) == "만":
        n *= 10000
    elif m.group(2) == "천":
        n *= 1000

    return int(n)


def get_soup(url):
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def make_item(source, title, url, views=None, reactions=None, rank=None):
    key = hashlib.sha1(url.encode()).hexdigest()[:16]

    return {
        "source": source,
        "id": key,
        "title": title[:180],
        "url": url,
        "views": views,
        "reactions": reactions,
        "rank": rank,
    }


# --------------------------------------------------
# 네이버 뉴스
# --------------------------------------------------

def naver_news():
    base = SOURCES["네이버 뉴스"]
    s = get_soup(base)

    out = []
    seen = set()

    selectors = [
        "a.list_title",
        "a[href*='/article/']",
    ]

    for selector in selectors:
        for a in s.select(selector):

            title = " ".join(a.stripped_strings).strip()
            url = urljoin(base, a.get("href", ""))

            if not title:
                continue

            if "/article/" not in url:
                continue

            if url in seen:
                continue

            seen.add(url)

            out.append(
                make_item(
                    "네이버 뉴스",
                    title,
                    url,
                    rank=len(out) + 1,
                )
            )

    return out[:100]


# --------------------------------------------------
# 네이버 스포츠
# --------------------------------------------------

def naver_sports():
    base = SOURCES["네이버 스포츠"]
    s = get_soup(base)

    out = []
    seen = set()

    for a in s.select("a[href]"):

        title = " ".join(a.stripped_strings).strip()
        url = urljoin(base, a.get("href", ""))

        if len(title) < 8:
            continue

        if not (
            "/wfootball/article/" in url
            or "/kfootball/article/" in url
            or "/baseball/article/" in url
            or "/basketball/article/" in url
            or "/volleyball/article/" in url
            or "/general/article/" in url
        ):
            continue

        if url in seen:
            continue

        seen.add(url)

        out.append(
            make_item(
                "네이버 스포츠",
                title,
                url,
                rank=len(out) + 1,
            )
        )

    return out[:100]


# --------------------------------------------------
# 디시 실시간 베스트
# --------------------------------------------------

def dc_best():
    base = SOURCES["디시 실베"]
    s = get_soup(base)

    out = []

    for tr in s.select("tr.ub-content"):

        a = tr.select_one("td.gall_tit a[href]")

        if not a:
            continue

        title = " ".join(a.stripped_strings).strip()

        if not title:
            continue

        url = urljoin(base, a["href"])

        views_el = tr.select_one("td.gall_count")
        rec_el = tr.select_one("td.gall_recommend")

        views = num(views_el.get_text(strip=True)) if views_el else None
        reactions = num(rec_el.get_text(strip=True)) if rec_el else None

        out.append(
            make_item(
                "디시 실베",
                title,
                url,
                views,
                reactions,
                len(out) + 1,
            )
        )

    return out[:100]


# --------------------------------------------------
# 펨코
# GitHub IP가 차단될 경우 오류만 기록
# --------------------------------------------------

def fmkorea():
    base = SOURCES["펨코 포텐"]

    try:
        s = get_soup(base)
    except Exception as e:
        print("펨코 접근 실패:", repr(e))
        return []

    out = []
    seen = set()

    for a in s.select("a[href]"):

        title = " ".join(a.stripped_strings).strip()
        url = urljoin(base, a.get("href", ""))

        if len(title) < 8:
            continue

        if "fmkorea.com" not in urlparse(url).netloc:
            continue

        if not re.search(r"/\d{5,}", url):
            continue

        if url in seen:
            continue

        seen.add(url)

        out.append(
            make_item(
                "펨코 포텐",
                title,
                url,
                rank=len(out) + 1,
            )
        )

    return out[:100]


def fetch_all():

    funcs = [
        ("네이버 뉴스", naver_news),
        ("네이버 스포츠", naver_sports),
        ("디시 실베", dc_best),
        ("펨코 포텐", fmkorea),
    ]

    result = []

    for name, func in funcs:

        try:
            items = func()

            print(name, len(items))

            result.extend(items)

        except Exception as e:
            print("ERROR", name, repr(e))

    return result


# --------------------------------------------------
# 텔레그램
# --------------------------------------------------

def telegram(msg):

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat:
        print("텔레그램 설정 없음")
        return

    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat,
            "text": msg,
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    r.raise_for_status()


def main():

    now = int(time.time())

    try:
        state = json.loads(
            STATE.read_text(encoding="utf-8")
        )
    except Exception:
        state = {
            "items": {},
            "alerts": {},
            "initialized": False,
        }

    state.setdefault("items", {})
    state.setdefault("alerts", {})

    first_run = not state.get("initialized", False)

    current = fetch_all()

    new_items = []
    trend_alerts = []

    for x in current:

        key = x["source"] + "|" + x["id"]

        old = state["items"].get(key)

        # ------------------------------------------
        # 신규 인기글
        # ------------------------------------------

        if old is None and not first_run:

            new_items.append(x)

        # ------------------------------------------
        # 기존 글 급상승 검사
        # ------------------------------------------

        score = 0
        reasons = []

        if old:

            minutes = max(
                (now - old.get("ts", now)) / 60,
                1,
            )

            if (
                x["views"] is not None
                and old.get("views") is not None
            ):

                diff = x["views"] - old["views"]
                rate = diff / minutes

                if diff >= 500 and rate >= 100:

                    score += min(
                        55,
                        20 + rate / 20,
                    )

                    reasons.append(
                        f"조회 +{diff:,} ({rate:,.0f}/분)"
                    )

            if (
                x["reactions"] is not None
                and old.get("reactions") is not None
            ):

                diff = (
                    x["reactions"]
                    - old["reactions"]
                )

                rate = diff / minutes

                if diff >= 15 and rate >= 3:

                    score += min(
                        40,
                        15 + rate * 2,
                    )

                    reasons.append(
                        f"반응 +{diff:,} ({rate:,.1f}/분)"
                    )

            if (
                x["rank"]
                and old.get("rank")
                and old["rank"] - x["rank"] >= 8
            ):

                jump = old["rank"] - x["rank"]

                score += min(
                    35,
                    10 + jump,
                )

                reasons.append(
                    f"순위 {old['rank']}→{x['rank']}"
                )

        last_alert = state["alerts"].get(key, 0)

        if (
            score >= 35
            and now - last_alert >= 1800
        ):

            trend_alerts.append(
                (score, x, reasons)
            )

            state["alerts"][key] = now

        state["items"][key] = {
            **x,
            "ts": now,
        }

    # ------------------------------------------
    # 신규 기사 전송
    # 한 번에 너무 많이 보내지 않도록 최대 10개
    # ------------------------------------------

    for x in new_items[:10]:

        telegram(
            "🆕 신규 인기글\n"
            f"[{x['source']}]\n"
            f"{x['title']}\n"
            f"{x['url']}"
        )

        time.sleep(0.5)

    # ------------------------------------------
    # 급상승 전송
    # ------------------------------------------

    for score, x, reasons in sorted(
        trend_alerts,
        reverse=True,
        key=lambda z: z[0],
    )[:10]:

        level = (
            "🚨 폭발"
            if score >= 80
            else "🔥 급상승"
        )

        telegram(
            f"{level} · TREND {min(100, int(score))}\n"
            f"[{x['source']}]\n"
            f"{x['title']}\n"
            + " / ".join(reasons)
            + f"\n{x['url']}"
        )

        time.sleep(0.5)

    state["initialized"] = True

    # 3일 지난 데이터 삭제
    state["items"] = {
        k: v
        for k, v in state["items"].items()
        if now - v.get("ts", 0) < 259200
    }

    state["alerts"] = {
        k: v
        for k, v in state["alerts"].items()
        if now - v < 259200
    }

    STATE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("신규 알림:", len(new_items))
    print("급상승 알림:", len(trend_alerts))


if __name__ == "__main__":
    main()
