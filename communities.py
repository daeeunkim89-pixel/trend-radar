"""Public community best lists, with original post URLs and source-only counters."""
import re
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

KST = ZoneInfo("Asia/Seoul")
COMMUNITY_LIMIT = 100
COMMUNITY_NAMES = {"디시 실베", "펨코 포텐", "커뮤니티 인기", "더쿠 HOT", "개드립 인기",
                   "루리웹 베스트", "보배드림 베스트", "인스티즈 이슈", "엠팍 BEST", "펨코 간접"}
FMKOREA_HOSTS = {"fmkorea.com", "www.fmkorea.com", "m.fmkorea.com"}
BOARD_URLS = {
    "더쿠 HOT": tuple("https://theqoo.net/hot" + (f"?page={p}" if p > 1 else "") for p in range(1, 4)),
    "개드립 인기": tuple(f"https://www.dogdrip.net/dogdrip?sort_index=popular&page={p}" for p in (1, 2)),
    "루리웹 베스트": tuple(f"https://bbs.ruliweb.com/best/humor_only?orderby=recommend&range=6h&page={p}" for p in (1, 2)),
    "보배드림 베스트": tuple(f"https://www.bobaedream.co.kr/list?code=best&page={p}" for p in (1, 2, 3)),
    "인스티즈 이슈": tuple(f"https://www.instiz.net/pt?page={p}" for p in (1, 2, 3)),
    "엠팍 BEST": tuple(f"https://mlbpark.donga.com/mp/best.php?b={b}&m=like" for b in ("bullpen", "kbotown", "mlbtown")),
}
COMMUNITY_HOSTS = {"theqoo.net", "www.dogdrip.net", "dogdrip.net", "bbs.ruliweb.com", "m.ruliweb.com",
                   "www.bobaedream.co.kr", "m.bobaedream.co.kr", "www.instiz.net", "instiz.net",
                   "mlbpark.donga.com", "gall.dcinside.com", "m.dcinside.com"} | FMKOREA_HOSTS


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def count(text):
    text = clean(text).replace(",", "")
    return int(text) if text.isdigit() else None


def post_url(url):
    """Only normalize identities explicitly present in an observed post link."""
    p = urlsplit(url)
    host, q = p.hostname, parse_qs(p.query)
    if p.scheme not in {"https", "http"} or p.username or p.password or p.port not in {None, 80, 443}:
        return None
    if host in FMKOREA_HOSTS:
        m = re.fullmatch(r"/(?:best2?/)?(\d{6,})/?", p.path)
        post = m[1] if m else q.get("document_srl", [""])[0] if p.path in {"/", "/index.php"} else ""
        if re.fullmatch(r"\d{6,}", post):
            return f"https://www.fmkorea.com/{post}"
    elif host == "theqoo.net":
        m = re.fullmatch(r"/(?:[a-z_]+/)?(\d{6,})/?", p.path)
        if m:
            return f"https://theqoo.net/hot/{m[1]}"
    elif host in {"www.dogdrip.net", "dogdrip.net"}:
        m = re.fullmatch(r"/(?:dogdrip/)?(\d{6,})/?", p.path)
        if m:
            return f"https://www.dogdrip.net/{m[1]}"
    elif host in {"bbs.ruliweb.com", "m.ruliweb.com"}:
        m = re.fullmatch(r"/(?:best|community)/board/(\d+)/read/(\d+)/?", p.path)
        if m:
            return f"https://bbs.ruliweb.com/community/board/{m[1]}/read/{m[2]}"
    elif host in {"www.bobaedream.co.kr", "m.bobaedream.co.kr"}:
        m = re.match(r"/board/bbs_view/(best|humor|accident|freeb)/(\d+)(?:/|$)", p.path)
        code, post = (m[1], m[2]) if m else (q.get("code", [""])[0], q.get("No", [""])[0])
        if (m or p.path in {"/view", "/view.php"}) and code in {"best", "humor", "accident", "freeb"} and post.isdigit():
            return "https://www.bobaedream.co.kr/view?" + urlencode({"code": code, "No": post})
    elif host in {"www.instiz.net", "instiz.net"}:
        m = re.fullmatch(r"/pt/(\d{5,})/?", p.path)
        if m:
            return f"https://www.instiz.net/pt/{m[1]}"
    elif host == "mlbpark.donga.com" and p.path == "/mp/b.php":
        post, board = q.get("id", [""])[0], q.get("b", [""])[0]
        if re.fullmatch(r"\d{15,}", post) and board in {"bullpen", "kbotown", "mlbtown"}:
            return "https://mlbpark.donga.com/mp/b.php?" + urlencode({"b": board, "id": post, "m": "view"})
    return None


def is_community(story):
    return any(x.get("content_kind") == "community" or x.get("source") in COMMUNITY_NAMES
               or urlsplit(x.get("link", "")).hostname in COMMUNITY_HOSTS for x in story.get("members", []))


def material_urls(detail):
    """Shared media/source identities; exclude a lone generic preview image."""
    media = detail.get("media", [])
    eligible = [x for x in media if x.get("kind") in {"video", "gif"}
                or (x.get("kind") == "image" and sum(y.get("kind") == "image" for y in media) >= 2)]
    return {x["url"].split("#", 1)[0] for x in eligible + detail.get("source_links", []) + detail.get("fmkorea_links", []) if x.get("url")}


def fmkorea_url(url):
    try:
        return post_url(url) if urlsplit(url).hostname in FMKOREA_HOSTS else None
    except ValueError:
        return None


def list_time(text, now):
    """A list's post timestamp, never the date the depicted event happened."""
    text = clean(text)
    current = datetime.fromtimestamp(now, KST)
    try:
        if re.fullmatch(r"\d{14}", text):
            dt = datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=KST)
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text):
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
        elif re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", text):
            parts = [int(v) for v in text.split(":")]
            dt = current.replace(hour=parts[0], minute=parts[1], second=parts[2] if len(parts) > 2 else 0, microsecond=0)
            if dt.timestamp() > now + 300:
                dt -= timedelta(days=1)
        elif re.fullmatch(r"\d{1,2}[.-]\d{1,2}", text):
            month, day = map(int, re.split(r"[.-]", text))
            dt = current.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
            if dt.timestamp() > now + 300:
                dt = dt.replace(year=dt.year - 1)
        else:
            m = re.search(r"(\d+)\s*(분|시간|일)\s*전", text)
            if not m:
                return None
            dt = current - timedelta(seconds=int(m[1]) * {"분": 60, "시간": 3600, "일": 86400}[m[2]])
        stamp = int(dt.timestamp())
        return stamp if now - 36 * 3600 <= stamp <= now + 300 else None
    except (ValueError, OverflowError):
        return None


def _text(parent, selector):
    node = parent.select_one(selector) if parent else None
    return clean(node.get_text(" ", strip=True)) if node else ""


def parse_board(soup, base, source, now=None, limit=COMMUNITY_LIMIT):
    now = int(now or time.time())
    selectors = {"더쿠 HOT": "tr:not(.notice) td.title a:not(.replyNum)",
                 "개드립 인기": "a.title-link[data-document-srl]", "루리웹 베스트": "a.subject_link",
                 "보배드림 베스트": "a.bsubject", "인스티즈 이슈": ".listsubject a[href]",
                 "엠팍 BEST": ".lists_today .title a[href]"}
    hosts = {"더쿠 HOT": "theqoo.net", "개드립 인기": "www.dogdrip.net", "루리웹 베스트": "bbs.ruliweb.com",
             "보배드림 베스트": "www.bobaedream.co.kr", "인스티즈 이슈": "www.instiz.net", "엠팍 BEST": "mlbpark.donga.com"}
    rows, seen = [], set()
    for a in soup.select(selectors[source]):
        url = post_url(urljoin(base, a.get("href", "")))
        if not url or url in seen or urlsplit(url).hostname != hosts[source]:
            continue
        container = a.find_parent("li") if source in {"개드립 인기", "엠팍 BEST"} else a.find_parent("tr")
        if not container:
            continue
        headline = a.select_one("strong.text_over, .sbj")
        title_node = BeautifulSoup(str(headline or a), "html.parser")
        for extra in title_node.select(".cmt, .cmt2, .cmt3, .num_reply, .list_subtitle, script, style"):
            extra.decompose()
        title = clean(a.get("title") or a.get("alt") or title_node.get_text(" ", strip=True))
        if len(title) < 4 or re.match(r"\[?공지|이용\s*안내", title):
            continue
        views = reactions = comments = None
        listed = category = ""
        if source == "더쿠 HOT":
            listed = container.get("data-regdate") or _text(container, "td.time")
            views, comments = count(_text(container, "td.m_no")), count(_text(container, ".replyNum"))
            category = _text(container, "td.cate")
        elif source == "개드립 인기":
            clock = container.select_one(".fa-clock")
            listed = clock.parent.get_text(" ", strip=True) if clock else ""
            thumb = container.select_one(".fa-thumbs-up")
            reactions = count(thumb.parent.parent.get_text(" ", strip=True)) if thumb else None
            comments = count(_text(container, "h5 > span"))
        elif source == "루리웹 베스트":
            listed = _text(container, "td.time")
            views, reactions = count(_text(container, "td.hit")), count(_text(container, "td.recomd"))
            comments = count(re.sub(r"[^0-9]", "", _text(container, ".num_reply")))
        elif source == "보배드림 베스트":
            listed = _text(container, "td.date")
            views, reactions = count(_text(container, "td.count")), count(_text(container, "td.recomm"))
            comments = count(_text(container, ".totreply"))
            category = _text(container, ".category")
        elif source == "인스티즈 이슈":
            cells = container.select("td.listno")
            if cells:
                listed = cells[0].get_text(strip=True)
                views = count(cells[1].get_text()) if len(cells) > 1 else None
                reactions = count(cells[2].get_text()) if len(cells) > 2 else None
            else:
                info = _text(container, ".list_subtitle")
                m = re.search(r"\d{1,2}:\d{2}", info)
                listed = m[0] if m else ""
                m = re.search(r"조회\s*([\d,]+)", info)
                views = count(m[1]) if m else None
            comments = count(_text(a, ".cmt3, .cmt2, .cmt"))
            category = _text(container, ".list_category")
        elif source == "엠팍 BEST":
            listed = _text(container, ".date")
            views = count(_text(container, ".viewV"))
            comments = count(re.sub(r"[^0-9]", "", _text(container, ".replycnt")))
            category = "야구" if parse_qs(urlsplit(url).query).get("b", [""])[0] in {"kbotown", "mlbtown"} else ""
            day = parse_qs(urlsplit(url).query)["id"][0][:8]
            try:
                if not 0 <= (datetime.fromtimestamp(now, KST).date() - datetime.strptime(day, "%Y%m%d").date()).days <= 1:
                    continue
            except ValueError:
                continue
        stamp = list_time(listed, now)
        # Undated markup is not treated as today's post just because we fetched it today.
        if stamp is None:
            continue
        seen.add(url)
        rows.append({"source": source, "parser_revision": 5, "title": title[:220], "link": url,
                     "rank": len(rows) + 1, "views": views, "reactions": reactions, "comments": comments,
                     "content_kind": "community", "list_category": category, "listed_at": stamp})
        if len(rows) >= limit:
            break
    return rows


def fetch_board(get_html, source, now=None):
    rows, seen, errors = [], set(), []
    for url in BOARD_URLS[source]:
        try:
            found = parse_board(get_html(url), url, source, now=now)
            for row in found:
                if row["link"] not in seen:
                    seen.add(row["link"])
                    row["rank"] = len(rows) + 1
                    rows.append(row)
            if not found:
                errors.append("게시물 0개")
        except Exception as error:
            errors.append(str(error))
    if not rows:
        raise RuntimeError(" / ".join(errors) or "커뮤니티 게시물 0개")
    if errors:
        print("COMMUNITY PARTIAL", source, " / ".join(errors))
    return rows[:COMMUNITY_LIMIT]


