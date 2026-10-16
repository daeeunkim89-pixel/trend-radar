"""Public source history and evidence-based editorial cards; no model calls."""
import copy
import hashlib
import html
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

KST = ZoneInfo("Asia/Seoul")
HISTORY_FILE = Path("data/history.json")
MAX_ITEMS = 5000
RETENTION = 7 * 86400
DETAIL_HOSTS = {
    "news.naver.com", "n.news.naver.com", "m.news.naver.com",
    "sports.news.nate.com", "news.nate.com",
    "gall.dcinside.com", "m.dcinside.com",
}
STATUS_NAMES = {"pick": "선정", "hold": "보류", "doing": "제작 중", "done": "업로드 완료", "clear": "미선정"}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_history(path=None):
    path = Path(path or HISTORY_FILE)
    if not path.exists():
        return {"version": 1, "items": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != 1 or not isinstance(value.get("items"), dict):
        raise ValueError("수집 기록 형식을 확인해야 합니다")
    return value


def canonical_url(url):
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    q = parse_qs(p.query)
    article = re.search(r"/article/(\d+)/(\d+)", p.path)
    if host in {"news.naver.com", "n.news.naver.com", "m.news.naver.com"}:
        if article:
            return f"https://n.news.naver.com/article/{article[1]}/{article[2]}"
        if q.get("oid") and q.get("aid"):
            return f"https://n.news.naver.com/article/{q['oid'][0]}/{q['aid'][0]}"
    if host in {"gall.dcinside.com", "m.dcinside.com"}:
        mobile = re.fullmatch(r"/board/([^/]+)/(\d+)/?", p.path)
        board = mobile[1] if mobile else q.get("id", [""])[0]
        post = mobile[2] if mobile else q.get("no", [""])[0]
        if board and post:
            return "https://gall.dcinside.com/board/view/?" + urlencode({"id": board, "no": post})
    if host in {"www.fmkorea.com", "m.fmkorea.com", "fmkorea.com"}:
        match = re.fullmatch(r"/(?:best/)?(\d+)/?", p.path)
        post = match[1] if match else q.get("document_srl", [""])[0]
        if post:
            return f"https://www.fmkorea.com/{post}"
    query = [(k, v) for k, values in q.items() for v in values
             if not k.lower().startswith("utm_") and k.lower() not in {"ref", "from", "fbclid", "gclid"}]
    return urlunsplit(("https", host, p.path, urlencode(sorted(query)), ""))


def item_id(url):
    return hashlib.sha256(canonical_url(url).encode()).hexdigest()[:12]


def title_key(title):
    title = re.sub(r"^\s*\[(?:속보|단독|영상|사진)\]\s*", "", title)
    title = re.sub(r"\s*\[\d+\]\s*$", "", title)
    return "".join(re.findall(r"[가-힣a-z0-9]+", title.lower()))


def same_headline(left, right):
    # Conservative: wording changes and allegations are never inferred to be the same event.
    return len(title_key(left)) >= 10 and title_key(left) == title_key(right)


def metric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None


def observe(data, history, now=None):
    now = int(now or time.time())
    history = copy.deepcopy(history)
    records = history["items"]
    current = []
    for rows in data.values():
        for raw in rows:
            row = dict(raw)
            row["link"] = canonical_url(row["link"])
            key = item_id(row["link"])
            previous = records.get(key, {})
            row.update(item_id=key, first_seen_at=previous.get("first_seen_at", now),
                       new=not bool(previous), title_changed=bool(previous and previous["title"] != row["title"]))
            row["views"], row["reactions"] = metric(row.get("views")), metric(row.get("reactions"))
            samples = previous.get("samples", [])
            last = samples[-1] if samples else {}
            elapsed = now - last.get("at", now)
            change = {"seconds": elapsed}
            if 300 <= elapsed <= 6 * 3600:
                for name in ("views", "reactions"):
                    before, after = metric(last.get(name)), row[name]
                    if before is not None and after is not None:
                        if after >= before:
                            change[name] = after - before
                            change[name + "_hourly"] = (after - before) * 3600 / elapsed
                        else:
                            change[name + "_reset"] = True
            row["change"] = change
            sample = {"at": now, "views": row["views"], "reactions": row["reactions"]}
            if not samples or samples[-1]["at"] < now:
                samples = (samples + [sample])[-24:]
            record = {**previous, "source": row["source"], "title": row["title"], "link": row["link"],
                      "first_seen_at": row["first_seen_at"], "last_seen_at": now, "samples": samples}
            records[key] = record
            current.append(row)
    records = {k: v for k, v in records.items() if v["last_seen_at"] >= now - RETENTION}
    records = dict(sorted(records.items(), key=lambda kv: kv[1]["last_seen_at"], reverse=True)[:MAX_ITEMS])
    history.update(items=records, updated_at=now)
    # A previously seen identical headline can keep its editorial state across sources.
    prior_titles = {}
    for key, record in sorted(records.items(), key=lambda kv: (kv[1]["first_seen_at"], kv[0])):
        if record["last_seen_at"] >= now - 48 * 3600:
            prior_titles.setdefault(title_key(record["title"]), record.get("story_id", key))
    groups = {}
    for row in current:
        record = records[row["item_id"]]
        headline = title_key(row["title"])
        story = record.get("story_id") or (prior_titles.get(headline) if len(headline) >= 10 else None) or row["item_id"]
        record["story_id"] = story
        row["story_id"] = story
        groups.setdefault(story, {"id": story, "members": []})["members"].append(row)
    stories = list(groups.values())
    for story in stories:
        story["members"].sort(key=lambda x: (x["source"] == "디시 실베", x["first_seen_at"], x["rank"]))
        story["lead"] = story["members"][0]
        story.update(assess(story))
    # A growth bonus compares only items from the same source and the same metric.
    for source in data:
        comparable = [x for x in current if x["source"] == source and x["change"].get("views_hourly", 0) > 0]
        comparable.sort(key=lambda x: x["change"]["views_hourly"], reverse=True)
        for index, row in enumerate(comparable):
            if index < max(1, len(comparable) // 3):
                for story in stories:
                    if row in story["members"]:
                        story["score"] += 15
                        story["reasons"].append("같은 소스의 비교 가능한 수집 글 중 조회 증가 속도가 상위권")
    stories.sort(key=lambda s: (-s["score"], not s["lead"]["new"], s["id"]))
    return stories, history


def assess(story):
    title = story["lead"]["title"]
    rules = [
        ("축구", r"손흥민|김민재|이강인|황희찬|오현규|호날두|메시|안토니|축구|토트넘|맨유|맨시티|아스널|아스날|레알|바르셀로나|챔피언스리그|프리미어리그|국가대표", 30, "btp에서 자주 다루는 축구·선수 소재"),
        ("스포츠", r"야구|농구|배구|올림픽|월드컵|오타니|류현진|김하성|이정후|NBA|MLB|KBO|UFC|격투기", 23, "스포츠 팬이 알아볼 인물·대회 소재"),
        ("밈·문화", r"밈|챌린지|화제|난리|웃음|예능|아이돌|배우|가수|블랙핑크|BTS|뉴진스|공중제비", 18, "문화·밈 분야 검토 후보"),
        ("기술·생활", r"테슬라|머스크|아이폰|갤럭시|인공지능|로봇|우주|신기술", 12, "변화나 장면을 쉽게 보여줄 수 있는 기술·생활 소재"),
    ]
    tags, reasons, score = [], [], 0
    for tag, pattern, points, reason in rules:
        if re.search(pattern, title, re.I):
            tags.append(tag)
            reasons.append(reason)
            score += points
    if re.search(r"최초|최다|최연소|최고령|신기록|역대|기록 경신|1위", title):
        score += 12
        reasons.append("제목에 기록·순위 소재가 있어 비교 구성을 검토할 만함")
    if re.search(r"반전|도둑|절도|도난|집에|경기 중|경기중|뜻밖|깜짝|불구|알고 보니|알고보니", title):
        score += 10
        reasons.append("예상 밖 상황이 제목에 있어 첫 장면으로 설명하기 좋음")
    if len({x["source"] for x in story["members"]}) > 1:
        score += 5
        reasons.append("같은 제목이 여러 수집 소스에 등장")
    if not reasons:
        tags, reasons = ["일반 이슈"], ["수집 목록에 포착된 후보 · btp 주제 적합성은 직접 검토"]
    cautions = []
    if any(x["source"] in {"디시 실베", "펨코 포텐"} for x in story["members"]):
        cautions.append("커뮤니티 게시물은 반응 탐지용 · 사실은 기사·공식 발표로 대조")
    if re.search(r"의혹|루머|이적설|혐의|추정|가능성|미확인", title):
        cautions.append("제목의 의혹·가능성을 확정 사실로 쓰지 않기")
    return {"score": score, "tags": tags, "reasons": reasons, "cautions": cautions}


def allowed_detail(url):
    p = urlsplit(url)
    return p.scheme == "https" and p.hostname in DETAIL_HOSTS and not p.username and not p.password and p.port in {None, 443}


def public_link(url):
    try:
        p = urlsplit(url)
        return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password
    except ValueError:
        return False


def short_excerpt(text, title):
    # Limit the combined headline and excerpt to a short quotation from the article.
    budget = max(0, 24 - len(title.split()))
    words = clean(text).split()[:min(18, budget)]
    excerpt = " ".join(words)[:130]
    return excerpt + ("…" if excerpt and len(clean(text)) > len(excerpt) else "")


def parse_detail(markup, url, title):
    soup = BeautifulSoup(markup, "html.parser")
    for node in soup.select("script, style, .ad, .advertisement, .reporter_area, .copyright"):
        node.decompose()
    body = soup.select_one("#dic_area, #articleBodyContents, #realArtcContents, #articleCont, .write_div")
    description = soup.select_one('meta[property="og:description"], meta[name="description"]')
    text = clean(body.get_text(" ", strip=True)) if body else clean(description.get("content", "") if description else "")
    result = {"excerpt": short_excerpt(text, title), "media": []}
    image = soup.select_one('meta[property="og:image"]')
    if image:
        link = urljoin(url, image.get("content", ""))
        if public_link(link) and len(link) < 600:
            result["media"].append({"label": "기사 미리보기 이미지", "url": link})
    for node in soup.select("video[src], video source[src], iframe[src]"):
        link = urljoin(url, node.get("src", ""))
        host = urlsplit(link).hostname or ""
        if public_link(link) and len(link) < 600 and (node.name != "iframe" or host in {"www.youtube.com", "www.youtube-nocookie.com", "player.vimeo.com"}):
            result["media"].append({"label": "원문에 연결된 영상", "url": link})
            break
    published = soup.select_one('meta[property="article:published_time"], meta[name="article:published_time"], time[itemprop="datePublished"][datetime], .media_end_head_info_datestamp_time[data-date-time]')
    if published:
        value = published.get("content") or published.get("datetime") or published.get("data-date-time")
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            # Naver's explicit article timestamp is in Korea time; this is not an event date.
            result["published_at"] = (dt if dt.tzinfo else dt.replace(tzinfo=KST)).isoformat()
        except (ValueError, TypeError, AttributeError):
            pass
    return result


def fetch_detail(item):
    url = item["link"]
    try:
        for _ in range(4):
            if not allowed_detail(url):
                return {"unavailable": "원문 자동 미리보기 미지원", "media": []}
            with requests.get(url, timeout=(5, 8), allow_redirects=False, stream=True,
                              headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR"}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    url = urljoin(url, response.headers.get("Location", ""))
                    continue
                if response.status_code != 200:
                    return {"unavailable": f"원문 미리보기 HTTP {response.status_code}", "media": []}
                if "html" not in response.headers.get("Content-Type", "").lower():
                    return {"unavailable": "원문 HTML 확인 불가", "media": []}
                content = bytearray()
                for block in response.iter_content(16384):
                    content.extend(block)
                    if len(content) > 1_500_000:
                        return {"unavailable": "원문 용량 제한", "media": []}
                result = parse_detail(bytes(content), url, item["title"])
                if not result["excerpt"]:
                    result["unavailable"] = "원문 텍스트 자동 추출 불가"
                return result
    except (requests.RequestException, ValueError, LookupError):
        return {"unavailable": "원문 미리보기 연결 실패", "media": []}
    return {"unavailable": "원문 리다이렉트 확인 불가", "media": []}


def enrich(stories, history, now=None, fetcher=None):
    now = int(now or time.time())
    fetcher = fetcher or fetch_detail
    for story in stories:
        row = story["lead"]
        record = history["items"][row["item_id"]]
        cache = record.get("detail", {})
        if not cache or now - cache.get("checked_at", 0) > 6 * 3600:
            cache = {**fetcher(row), "checked_at": now}
            record["detail"] = cache
        story["detail"] = cache
    return stories


def stamp(timestamp):
    return datetime.fromtimestamp(timestamp, KST).strftime("%m/%d %H:%M")


def link(label, url):
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>' if public_link(url) else html.escape(label)


def reaction_text(row):
    values = []
    delta = row["change"]
    elapsed = delta.get("seconds", 0)
    interval = f"{elapsed // 60}분" if elapsed < 3600 else f"{elapsed / 3600:.1f}시간"
    for name, label in (("views", "조회"), ("reactions", "추천")):
        value = row.get(name)
        if value is None:
            continue
        text = f"{label} {value:,}"
        if name in delta:
            text += f" ({interval} 전 대비 +{delta[name]:,})"
        elif delta.get(name + "_reset"):
            text += " (집계값 감소·증가량 계산 제외)"
        elif row["new"]:
            text += " (첫 관측·비교 대기)"
        values.append(text)
    return " · ".join(values) if values else "조회·추천 수집 불가 · 목록 등장만 확인"


def render_card(story, index, state):
    lead, detail = story["lead"], story.get("detail", {})
    priority = "우선 검토" if story["score"] >= 40 else "검토 후보"
    status = STATUS_NAMES.get(state.get("statuses", {}).get(story["id"], {}).get("status"), "미선정")
    badge = "신규 포착" if all(x["new"] for x in story["members"]) else "재포착"
    if any(x["title_changed"] for x in story["members"]):
        badge = "제목 변경·원문 확인"
    lines = [f"<b>{index:02d} · {priority} · {html.escape(' / '.join(story['tags']))}</b>",
             link(lead["title"], lead["link"]), f"{badge} | 첫 포착 {stamp(lead['first_seen_at'])}"]
    if detail.get("excerpt"):
        lines.append("원문 미리보기: " + html.escape(detail["excerpt"]))
    else:
        lines.append("내용: " + html.escape(detail.get("unavailable", "원문에서 확인 필요")))
    lines.append("btp 포인트: " + html.escape(" · ".join(story["reasons"][:2])))
    for row in story["members"]:
        lines.append(link(row["source"] + " 목록 " + str(row["rank"]), row["link"]) + " | " + html.escape(reaction_text(row)))
        if row["title"] != lead["title"]:
            lines.append("↳ " + html.escape(row["title"]))
    if detail.get("published_at"):
        lines.append("기사 표기 시각: " + html.escape(detail["published_at"]))
    if detail.get("media"):
        lines.append("자료: " + " · ".join(link(x["label"], x["url"]) for x in detail["media"][:2]))
    for caution in story["cautions"]:
        lines.append("확인: " + html.escape(caution))
    lines.append(f"상태 {status} | 선정 <code>/pick {story['id']}</code>")
    return "\n".join(lines)


def pack_cards(cards, limit=3500):
    chunks, current = [], ""
    for card in cards:
        # Bound individual cards upstream; never split HTML tags or URLs.
        if len(card.encode("utf-16-le")) // 2 > limit:
            raise ValueError("텔레그램 소재 카드 길이 제한 초과")
        candidate = current + ("\n\n────────\n\n" if current else "") + card
        if len(candidate.encode("utf-16-le")) // 2 > limit:
            chunks.append(current)
            current = card
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def render_digest(stories, counts, errors, state, now=None):
    now = int(now or time.time())
    statuses = state.get("statuses", {})
    stories = sorted(stories, key=lambda s: statuses.get(s["id"], {}).get("status") == "done")
    header = [f"<b>btp 소재함 · {stamp(now)}</b>",
              " · ".join(f"{html.escape(name)} {count}/10" for name, count in counts.items()),
              f"수집 {sum(counts.values())}개 → 동일 제목 묶음 {len(stories)}개 · 전부 포함",
              "편집 적합도 순서 · 조회수 예측값 아님",
              "선정 /pick ID · 보류 /hold ID · 제작 /doing ID · 완료 /done ID",
              "선정 목록 /queue · 명령은 약 10분 간격 점검 시 반영(지연 가능)"]
    for source in errors:
        if source.startswith("텔레그램"):
            header.append("⚠️ 선정 명령 점검 실패 · 소재 보고는 계속 전송")
        else:
            header.append(f"⚠️ {html.escape(source)}: 수집 실패 · 확인된 다른 소스는 계속 전송")
    cards = []
    for i, story in enumerate(stories, 1):
        for start in range(0, len(story["members"]), 3):
            page = {**story, "members": story["members"][start:start + 3]}
            cards.append(render_card(page, i, state))
    return ["\n".join(header)] + pack_cards(cards)
