"""FMKorea discovery through public indexes; never fetch the protected FM body."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from communities import fmkorea_url
from discovery import COMMUNITY_URL, clean, parse_community_index

LOLUS_URL = "https://www.lolus.dev/"
FM_INDEX_URL = "https://www.issuelink.co.kr/community/listview/fmkorea/24/adj/_self/blank/blank/blank"
INDIRECT_LIMIT = 120
MAX_SNAPSHOT_AGE = 24 * 3600
CACHE_FIELDS = ("origin", "discovery", "discovery_url", "discovery_observed_at", "discovery_timestamp_kind",
                "discovery_label", "listed_at", "content_kind")


def _fresh(stamp, now):
    return isinstance(stamp, (int, float)) and now - MAX_SNAPSHOT_AGE <= stamp <= now + 300


def parse_lolus(soup, now=None):
    now = int(now or time.time())
    rows, seen = [], set()
    for card in soup.select('.post-card[data-site="fmkorea"]'):
        a, clock = card.select_one('a.post-title[href]'), card.select_one('time[datetime]')
        if not a or not clock:
            continue
        url = fmkorea_url(a["href"])
        try:
            dt = datetime.fromisoformat(clock["datetime"].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                continue
            observed_at = int(dt.timestamp())
        except (ValueError, TypeError):
            continue
        if not url or url in seen or not _fresh(observed_at, now):
            continue
        title = clean(a.get_text(" ", strip=True))
        if len(title) < 4:
            continue
        seen.add(url)
        # The timestamp is explicitly labelled collection time by LL. Its
        # counters and scores are not current FMKorea view/recommendation data.
        rows.append({"source": "펨코 간접", "parser_revision": 6, "title": title[:220], "link": url,
                     "rank": len(rows) + 1, "views": None, "reactions": None, "comments": None,
                     "content_kind": "community", "origin": "펨코", "discovery": "LL 공개목록",
                     "discovery_url": LOLUS_URL, "discovery_observed_at": observed_at,
                     "discovery_timestamp_kind": "index_observed", "discovery_label": "펨코·간접"})
    return rows


def parse_issuelink(soup, url=COMMUNITY_URL, now=None):
    rows = []
    for row in parse_community_index(soup, now=now):
        original = fmkorea_url(row["link"])
        if not original:
            continue
        rows.append({**row, "source": "펨코 간접", "link": original, "content_kind": "community",
                     "parser_revision": 6, "origin": "펨코", "discovery_url": url,
                     "discovery_observed_at": row["listed_at"], "discovery_timestamp_kind": "post_listed",
                     "discovery_label": "펨코·간접"})
    return rows


def recent_cache(history, now):
    rows = []
    for record in (history or {}).get("items", {}).values():
        url = fmkorea_url(record.get("link", ""))
        stamp = record.get("discovery_observed_at")
        if (not url or not _fresh(stamp, now) or record.get("discovery_url") not in {LOLUS_URL, COMMUNITY_URL, FM_INDEX_URL}
                or record.get("discovery_timestamp_kind") not in {"post_listed", "index_observed"}):
            continue
        rows.append({**{key: record[key] for key in CACHE_FIELDS if key in record},
                     "source": "펨코 간접", "parser_revision": 6, "title": record["title"], "link": url,
                     "rank": len(rows) + 1, "views": None, "reactions": None, "comments": None,
                     "content_kind": "community", "discovery_cache": True})
    return rows


def fetch_fmkorea_indirect(get_html, history=None, now=None):
    now = int(now or time.time())
    sources = ((FM_INDEX_URL, parse_issuelink), (COMMUNITY_URL, parse_issuelink), (LOLUS_URL, parse_lolus))
    diagnostics, found = [], []

    def read(source):
        url, parser = source
        try:
            soup = get_html(url)
            rows = parser(soup, url=url, now=now) if parser is parse_issuelink else parser(soup, now=now)
            return rows, {"url": url, "count": len(rows), "status": "ok" if rows else "no_fresh_items"}
        except Exception as error:
            return [], {"url": url, "count": 0, "status": "unavailable", "error": str(error)[:220]}

    with ThreadPoolExecutor(max_workers=2) as pool:
        for rows, diagnostic in pool.map(read, sources):
            found.extend(rows)
            diagnostics.append(diagnostic)
    # A server outage must not discard still-valid public discoveries. Never
    # refresh their original timestamp, or resurrect an old row using last_seen.
    cached = recent_cache(history, now) if any(d["status"] != "ok" for d in diagnostics) else []
    found.sort(key=lambda r: -r["discovery_observed_at"])
    unique = {}
    for row in found + cached:
        if row["link"] not in unique:
            unique[row["link"]] = row
    result = sorted(unique.values(), key=lambda r: -r["discovery_observed_at"])[:INDIRECT_LIMIT]
    for index, row in enumerate(result, 1):
        row["rank"] = index
    print("FMKOREA_INDIRECT", json.dumps({"total": len(result), "cached": sum(bool(r.get("discovery_cache")) for r in result),
                                        "sources": diagnostics}, ensure_ascii=False))
    if not result:
        raise RuntimeError("펨코 공개목록·유효한 캐시에서 새로 확인할 후보 0개")
    return result


if __name__ == "__main__":
    import requests
    from bs4 import BeautifulSoup

    def get_html(url):
        response = requests.get(url, timeout=(5, 10), headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR"})
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    try:
        rows = fetch_fmkorea_indirect(get_html)
        for row in rows[:5]:
            print("FMKOREA_INDIRECT_ITEM", json.dumps({k: row[k] for k in ("title", "link", "discovery", "discovery_observed_at", "discovery_timestamp_kind")}, ensure_ascii=False))
    except RuntimeError as error:
        print("FMKOREA_INDIRECT_UNAVAILABLE", str(error))
        raise SystemExit(1)
