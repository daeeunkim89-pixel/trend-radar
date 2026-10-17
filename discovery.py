"""Bounded public discovery lists. Index counters are never source view counts."""
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DISCOVERY_LIMIT = 60
COMMUNITY_URL = "https://www.issuelink.co.kr/community"


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def parse_nate_topic(soup, base, source, topic=None, now=None, limit=DISCOVERY_LIMIT):
    now = int(now or time.time())
    today = datetime.fromtimestamp(now, KST).date()
    ranked = "rank/interest" in base
    anchors = soup.select(".postRankSubjectList a.lt1[href], #postRankSubject .mduRankSubject a[href]") if ranked else soup.select(
        ".mduCluster a[href], .postSubject a[href], .postSubjectList a[href]")
    rows, seen = [], set()
    for anchor in anchors:
        url = urljoin(base, anchor["href"])
        parsed = urlsplit(url)
        match = re.fullmatch(r"/view/(\d{8})n\d+", parsed.path)
        if parsed.hostname not in {"sports.news.nate.com", "news.nate.com"} or not match:
            continue
        try:
            url_day = datetime.strptime(match[1], "%Y%m%d").date()
        except ValueError:
            continue
        if not 0 <= (today - url_day).days <= 1:
            continue
        headline = anchor.select_one("h2, dt, .tit, strong")
        title = clean(headline.get_text(" ", strip=True) if headline else anchor.get("title") or anchor.get_text(" ", strip=True))
        url = "https://" + parsed.hostname + parsed.path
        if len(title) < 8 or url in seen:
            continue
        seen.add(url)
        item = {"source": source, "parser_revision": 3, "title": title[:220], "link": url,
                "rank": len(rows) + 1, "views": None, "reactions": None, "article_date": match[1]}
        if topic:
            item["topic_hint"] = topic
        if ranked:
            item["rank_kind"] = "nate_" + ("ent" if "sc=ent" in base else "spo") + "_interest_100"
        rows.append(item)
        if len(rows) >= limit:
            break
    return rows


def parse_community_index(soup, now=None, limit=100):
    now = int(now or time.time())
    rows, seen = [], set()
    for anchor in soup.select(".first_title .title a[href]"):
        parsed = urlsplit(anchor["href"])
        match = re.fullmatch(r"/community/go/([a-z0-9]+)/([0-9]+)", parsed.path)
        if parsed.hostname != "www.issuelink.co.kr" or not match:
            continue
        tr = anchor.find_parent("tr")
        stamp = tr.select_one(".second_date span") if tr else None
        try:
            listed_at = int(datetime.strptime(stamp.get_text(strip=True), "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST).timestamp())
        except (AttributeError, TypeError, ValueError):
            continue
        if not now - 86400 <= listed_at <= now + 300:
            continue
        site, post = match.groups()
        # FMKorea IDs are supplied by the public index; no protected body is fetched.
        url = f"https://www.fmkorea.com/{post}" if site == "fmkorea" else anchor["href"]
        title = re.sub(r"\s*\[\d+\]\s*$", "", clean(anchor.get_text(" ", strip=True)))
        if len(title) < 4 or url in seen:
            continue
        origin = tr.select_one("td.rank_bg small")
        seen.add(url)
        rows.append({"source": "커뮤니티 인기", "parser_revision": 3, "title": title[:220], "link": url,
                     "rank": len(rows) + 1, "views": None, "reactions": None,
                     "origin": clean(origin.get_text()) if origin else site,
                     "discovery": "이슈링크 공개목록", "discovery_url": COMMUNITY_URL, "listed_at": listed_at})
        if len(rows) >= limit:
            break
    return rows


def fetch_football(get_html):
    rows, seen, errors = [], set(), []
    for url in ("https://sports.news.nate.com/soccer/", "https://sports.news.nate.com/abrsoccer/"):
        try:
            for row in parse_nate_topic(get_html(url), url, "국내·해외축구", "football", limit=30):
                if row["link"] not in seen:
                    seen.add(row["link"])
                    rows.append(row)
        except Exception as error:
            errors.append(str(error))
    if not rows:
        raise RuntimeError(" / ".join(errors) or "축구 후보 0개")
    return rows


def fetch_entertainment(get_html):
    url = "https://news.nate.com/rank/interest?sc=ent"
    return parse_nate_topic(get_html(url), url, "네이트 연예")


def fetch_community(get_html):
    return parse_community_index(get_html(COMMUNITY_URL))
