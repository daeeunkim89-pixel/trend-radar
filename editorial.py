"""Public source history and evidence-based editorial cards; no model calls."""
import copy
import hashlib
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from communities import COMMUNITY_HOSTS, FMKOREA_HOSTS, fmkorea_url, is_community, post_url

KST = ZoneInfo("Asia/Seoul")
HISTORY_FILE = Path("data/history.json")
MAX_ITEMS = 5000
RETENTION = 7 * 86400
DETAIL_HOSTS = {
    "news.naver.com", "n.news.naver.com", "m.news.naver.com",
    "sports.news.nate.com", "news.nate.com",
    "gall.dcinside.com", "m.dcinside.com",
}
DETAIL_HOSTS |= COMMUNITY_HOSTS - FMKOREA_HOSTS
STATUS_NAMES = {"pick": "선정", "hold": "보류", "doing": "제작 중", "done": "업로드 완료", "clear": "미선정"}

# Editorial preferences, not a prediction of Instagram reach. Keep ambiguous
# member names contextual, and avoid matching English IVE inside live.
FEMALE_IDOL = re.compile(
    r"여자\s*아이돌|여성\s*아이돌|걸\s*그룹|여돌|블랙핑크|뉴진스|에스파|르세라핌|"
    r"(?<![가-힣])아이브|트와이스|엔믹스|아일릿|키스\s*오브\s*라이프|베이비몬스터|"
    r"레드벨벳|소녀시대|스테이씨|오마이걸|(?:\(여자\)|여자)\s*아이들|하츠투하츠|"
    r"장원영|안유진|카리나|홍은채|허윤진|닝닝|쯔위|설윤|"
    r"(?<![a-z])(?:blackpink|newjeans|aespa|ive|le\s*sserafim|twice|nmixx|illit|"
    r"kiss\s*of\s*life|babymonster|red\s*velvet|itzy|i-dle)(?![a-z])", re.I)
CONTEXTUAL_IDOL_MEMBER = re.compile(
    r"(?<![가-힣a-z])(?:윈터|제니|로제|리사|지수|김채원|사쿠라|민지|하니|해린|혜인|"
    r"나연|사나|다현|미연|우기|민니|슈화|유나|예지|리아|있지|여자친구|키키)(?![a-z])", re.I)
IDOL_CONTEXT = re.compile(r"아이돌|걸\s*그룹|걸갤|무대|직캠|컴백|신곡|뮤직비디오|뮤비|안무|음악방송|음방|팬|콘서트|자막|라이브|시구")


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
    community_url = post_url(url)
    if community_url:
        return community_url
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
            parser_changed = bool(previous and previous.get("parser_revision") != row.get("parser_revision"))
            row.update(item_id=key, first_seen_at=previous.get("first_seen_at", now), parser_changed=parser_changed,
                       new=not bool(previous), title_changed=bool(previous and not parser_changed and previous["title"] != row["title"]))
            row["views"], row["reactions"] = metric(row.get("views")), metric(row.get("reactions"))
            samples = previous.get("samples", [])
            last = samples[-1] if samples else {}
            elapsed = now - last.get("at", now)
            change = {"seconds": elapsed}
            if 300 <= elapsed <= 6 * 3600:
                if row.get("rank_kind") and row.get("rank_kind") == last.get("rank_kind") and isinstance(last.get("rank"), int):
                    change["rank"] = last["rank"] - row["rank"]
                    change["previous_rank"] = last["rank"]
                for name in ("views", "reactions"):
                    before, after = metric(last.get(name)), row[name]
                    if before is not None and after is not None:
                        if after >= before:
                            change[name] = after - before
                            change[name + "_hourly"] = (after - before) * 3600 / elapsed
                        else:
                            change[name + "_reset"] = True
            row["change"] = change
            sample = {"at": now, "views": row["views"], "reactions": row["reactions"],
                      "rank": row["rank"], "rank_kind": row.get("rank_kind")}
            if not samples or samples[-1]["at"] < now:
                samples = (samples + [sample])[-24:]
            record = {**previous, "source": row["source"], "title": row["title"], "link": row["link"],
                      "first_seen_at": row["first_seen_at"], "last_seen_at": now, "samples": samples,
                      "parser_revision": row.get("parser_revision")}
            for name in ("origin", "discovery", "discovery_url", "discovery_observed_at", "discovery_timestamp_kind",
                         "discovery_label", "listed_at", "content_kind", "list_category"):
                if name in row:
                    record[name] = row[name]
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
        story["members"].sort(key=lambda x: (not is_community({"members": [x]}), bool(x.get("discovery")),
                                           x["first_seen_at"], x["rank"]))
        story["lead"] = story["members"][0]
        story.update(assess(story))
    # Compare actual growth only within one source/metric. Each signal can boost
    # a story once, even when the same headline appears on several sources.
    for name, label, points in (("views", "조회", 15), ("reactions", "추천", 10)):
        boosted = set()
        for source in data:
            comparable = [x for x in current if x["source"] == source and x["change"].get(name + "_hourly", 0) > 0]
            comparable.sort(key=lambda x: x["change"][name + "_hourly"], reverse=True)
            for row in comparable[:max(1, len(comparable) // 3)]:
                story = groups[row["story_id"]]
                if story["id"] in boosted:
                    continue
                boosted.add(story["id"])
                story["score"] += points
                reason = (f"같은 소스의 비교 가능한 수집 글 중 {label} 증가 속도가 상위권" if len(comparable) > 1
                          else f"직전 관측 대비 {label} 증가 확인")
                story["reasons"].append(reason)
    stories.sort(key=lambda s: (-s["score"], not s["lead"]["new"], s["id"]))
    return stories, history


def assess(story):
    title = story["lead"]["title"]
    female_idol = bool(FEMALE_IDOL.search(title) or
                       (CONTEXTUAL_IDOL_MEMBER.search(title) and IDOL_CONTEXT.search(title)))
    rules = [
        ("축구", r"손흥민|김민재|이강인|황희찬|오현규|호날두|메시|안토니|축구|토트넘|맨유|맨시티|아스널|아스날|레알|바르셀로나|챔피언스리그|프리미어리그|국가대표", 30, "btp에서 자주 다루는 축구·선수 소재"),
        ("스포츠", r"야구|농구|배구|올림픽|월드컵|오타니|류현진|김하성|이정후|NBA|MLB|KBO|UFC|격투기", 23, "스포츠 팬이 알아볼 인물·대회 소재"),
        ("밈·문화", r"밈|챌린지|화제|난리|웃음|예능|아이돌|배우|가수|블랙핑크|BTS|뉴진스|공중제비", 18, "문화·밈 분야 검토 후보"),
        ("기술·생활", r"테슬라|머스크|아이폰|갤럭시|인공지능|로봇|우주|신기술", 12, "변화나 장면을 쉽게 보여줄 수 있는 기술·생활 소재"),
    ]
    tags, reasons, score = [], [], 0
    if female_idol:
        tags.append("여자 아이돌")
        reasons.append("btp에서 우선 검토할 여자 아이돌 소재")
        score += 30
    for tag, pattern, points, reason in rules:
        if female_idol and tag == "밈·문화":
            continue
        if re.search(pattern, title, re.I):
            tags.append(tag)
            reasons.append(reason)
            score += points
    if female_idol and re.search(r"무대|직캠|컴백|신곡|안무|챌린지|예능", title):
        score += 8
        reasons.append("제목에 무대·활동 소재가 있어 영상 구성을 검토할 만함")
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
    if is_community(story):
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
    for node in soup.select("script, style, .ad, .advertisement, .reporter_area, .copyright, .tool_cont, .fan-option-button-group"):
        node.decompose()
    community = urlsplit(url).hostname in COMMUNITY_HOSTS
    body = soup.select_one("#dic_area, #articleBodyContents, #realArtcContents, #articleCont, .write_div, "
                           ".view_content, .bodyCont, #memo_content_1, #contentDetail, .xe_content")
    description = soup.select_one('meta[property="og:description"], meta[name="description"]')
    text = clean(body.get_text(" ", strip=True)) if body else clean(description.get("content", "") if description else "")
    result = {"excerpt": short_excerpt(text, title), "media": [], "source_links": [], "fmkorea_links": [], "revision": 6}
    if community:
        result["context"] = text[:1200] if body else ""
    image = soup.select_one('meta[property="og:image"]') if not community else None
    if image:
        link = urljoin(url, image.get("content", ""))
        if public_link(link) and len(link) < 600:
            result["media"].append({"label": "기사 미리보기 이미지", "url": link})
    scope = body if body else (soup if not community else BeautifulSoup("", "html.parser"))
    for node in scope.select("video[src], video source[src], iframe[src], iframe[data-src]"):
        link = urljoin(url, node.get("src") or node.get("data-src", ""))
        host = urlsplit(link).hostname or ""
        if public_link(link) and len(link) < 600 and (node.name != "iframe" or host in {"www.youtube.com", "www.youtube-nocookie.com", "player.vimeo.com"}):
            result["media"].append({"label": "원문 영상", "url": link, "kind": "video"})
            if len(result["media"]) >= 3:
                break
    if community:
        for node in scope.select("img[src], img[data-src], img[data-original]"):
            value = node.get("data-original") or node.get("data-src") or node.get("src", "")
            image_url = urljoin(url, value)
            if not public_link(image_url) or len(image_url) >= 600 or re.search(r"(?:logo|icon|avatar|emoticon|profile|/ads?/)", image_url, re.I):
                continue
            if image_url not in {x["url"] for x in result["media"]}:
                kind = "gif" if urlsplit(image_url).path.lower().endswith(".gif") else "image"
                result["media"].append({"label": "원문 움짤" if kind == "gif" else "원문 이미지", "url": image_url, "kind": kind})
            if len(result["media"]) >= 5:
                break
        # X embeds are often plain text, not iframe elements. Preserve the actual
        # source post without pretending we have verified what its video depicts.
        candidates = [a["href"] for a in scope.select("a[href]")]
        candidates += re.findall(r"https://[^\s<>\"']+", text)
        # Explicit citation blocks are separate from the article body on Ruliweb.
        # Do not inspect recommended posts, comments, ads or arbitrary page links.
        for citation in soup.select(".source_url, [itemprop='citation']"):
            candidates += [a["href"] for a in citation.select("a[href]")]
            candidates += re.findall(r"https?://[^\s<>\"']+", citation.get_text(" ", strip=True))
        for value in candidates:
            original = fmkorea_url(value.rstrip(".,);"))
            if original and original not in {x["url"] for x in result["fmkorea_links"]}:
                result["fmkorea_links"].append({"label": "펨코 출처", "url": original})
            if len(result["fmkorea_links"]) >= 3:
                break
        for value in candidates:
            p = urlsplit(value)
            if p.hostname in {"x.com", "twitter.com", "www.twitter.com"} and re.fullmatch(r"/[^/]+/status/\d+/?", p.path):
                source = "https://x.com" + p.path.rstrip("/")
            elif p.hostname in {"youtu.be", "www.youtube.com", "youtube.com"} and (p.path.startswith(("/watch", "/shorts/", "/embed/")) or p.hostname == "youtu.be"):
                source = value
            elif p.hostname in {"www.instagram.com", "instagram.com"} and re.match(r"/(?:p|reel)/[A-Za-z0-9_-]+", p.path):
                source = "https://www.instagram.com" + p.path
            else:
                continue
            if public_link(source) and len(source) < 600 and source not in {x["url"] for x in result["source_links"]}:
                result["source_links"].append({"label": "원본 SNS", "url": source})
            if len(result["source_links"]) >= 3:
                break
        kinds = {x.get("kind") for x in result["media"]}
        result["format"] = "영상" if "video" in kinds else "움짤" if "gif" in kinds else "이미지" if "image" in kinds else "원본 SNS" if result["source_links"] else "원문"
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
                if not result["excerpt"] and not result["media"] and not result.get("source_links"):
                    result["unavailable"] = "원문 텍스트 자동 추출 불가"
                return result
    except (requests.RequestException, ValueError, LookupError):
        return {"unavailable": "원문 미리보기 연결 실패", "media": []}
    return {"unavailable": "원문 리다이렉트 확인 불가", "media": []}


def enrich(stories, history, now=None, fetcher=None):
    now = int(now or time.time())
    fetcher = fetcher or fetch_detail
    pending = []
    for story in stories:
        row = story["lead"]
        record = history["items"][row["item_id"]]
        cache = record.get("detail", {})
        if not cache or row["title_changed"] or row.get("parser_changed") or now - cache.get("checked_at", 0) > 6 * 3600 or (is_community(story) and cache.get("revision") != 6):
            pending.append((story, record))
        else:
            story["detail"] = cache
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [(story, record, pool.submit(fetcher, story["lead"])) for story, record in pending]
        for story, record, future in futures:
            cache = {**future.result(), "checked_at": now, "revision": 6}
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
    if delta.get("rank"):
        direction = "상승" if delta["rank"] > 0 else "하락"
        values.append(f"직전 관측 {delta['previous_rank']}→{row['rank']}위 ({abs(delta['rank'])}계단 {direction})")
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
        position = " 급상승 " + str(row["rank"]) + "위" if row.get("rank_kind") == "nate_sports_interest" else " 목록 " + str(row["rank"])
        lines.append(link(row["source"] + position, row["link"]) + " | " + html.escape(reaction_text(row)))
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


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []

    def handle_data(self, data):
        self.text.append(data)


def message_units(markup):
    """Telegram's limit applies after HTML parsing; count UTF-16 conservatively."""
    parser = _VisibleText()
    parser.feed(markup)
    return len("".join(parser.text).encode("utf-16-le")) // 2


def digest_stories(stories, state):
    statuses = state.get("statuses", {})
    return sorted(stories, key=lambda s: statuses.get(s["id"], {}).get("status") == "done")


def digest_numbers(stories, state):
    return {str(i): story["id"] for i, story in enumerate(digest_stories(stories, state), 1)}


def short_title(title, width):
    return title if len(title) <= width else title[:width - 1].rstrip() + "…"


def compact_number(value):
    if value >= 10000:
        return f"{value / 10000:.1f}만"
    if value >= 1000:
        return f"{value / 1000:.1f}천"
    return str(value)


def compact_signal(story):
    for row in story["members"]:
        change = row["change"]
        if change.get("views", 0) > 0:
            minutes = round(change["seconds"] / 60)
            return f"조회 +{compact_number(change['views'])} / {minutes}분"
        if change.get("rank", 0) > 0:
            return f"급상승 {row['rank']}위 · ↑{change['rank']}계단"
        if change.get("reactions", 0) > 0:
            return f"추천 +{compact_number(change['reactions'])}"
    for row in story["members"]:
        if row.get("rank_kind") in {"nate_ent_interest_100", "nate_spo_interest_100"}:
            return f"관심 {row['rank']}위"
        if row.get("rank_kind") == "nate_sports_interest":
            return f"급상승 {row['rank']}위"
        if row.get("views") is not None:
            return "조회 " + compact_number(row["views"])
    return ""


SOURCE_LABELS = {"네이버 뉴스": "뉴스", "네이트 스포츠": "스포츠", "디시 실베": "실베", "펨코 포텐": "펨코",
                 "국내·해외축구": "축구", "네이트 연예": "연예", "커뮤니티 인기": "커뮤니티",
                 "더쿠 HOT": "더쿠", "개드립 인기": "개드립", "루리웹 베스트": "루리웹",
                 "보배드림 베스트": "보배", "인스티즈 이슈": "인스티즈", "엠팍 BEST": "엠팍", "펨코 간접": "펨코 간접"}


def _compact_row(story, index, state, width, featured=False):
    lead = story["lead"]
    title = short_title(lead["title"], width)
    source = SOURCE_LABELS.get(lead["source"], lead["source"])
    if lead.get("discovery"):
        source = lead.get("discovery_label") or lead.get("origin", source) + "·목록"
    row = f"{index:02d} {link(title, lead['link'])}"
    detail = story.get("detail", {})
    video = next((x for x in detail.get("media", []) if x.get("kind") == "video"), None)
    original = video or next(iter(detail.get("source_links", [])), None)
    if featured and original:
        row += " · " + link("영상" if video else "원본", original["url"])
    if detail.get("fmkorea_links") and not fmkorea_url(lead["link"]):
        row += " · " + link("펨코", detail["fmkorea_links"][0]["url"])
    other_links, seen = [], {lead["link"]}
    for member in story["members"]:
        if member["link"] not in seen:
            seen.add(member["link"])
            other_links.append(link(SOURCE_LABELS.get(member["source"], member["source"]), member["link"]))
    if other_links:
        row += " · " + "/".join(other_links)
    signal = compact_signal(story)
    status = state.get("statuses", {}).get(story["id"], {}).get("status")
    meta = [source]
    if story.get("category"):
        meta.insert(0, story["category"])
    meta.append(detail.get("format", "커뮤니티") if is_community(story) else "기사")
    if featured and story.get("review_reason"):
        meta.append(story["review_reason"])
    if signal:
        meta.append(signal)
    if status and status != "clear":
        meta.append(STATUS_NAMES[status])
    if featured:
        row += "\n     " + html.escape(" · ".join(meta))
    else:
        row += " — " + html.escape(" · ".join(meta))
    return row


def render_digest(stories, counts, errors, state, now=None, excluded=0):
    now = int(now or time.time())
    ordered = digest_stories(stories, state)
    for width in (40, 32, 24, 16):
        header = [f"<b>⚡ btp 소재함 · {stamp(now)}</b>",
                  " · ".join(f"{html.escape(SOURCE_LABELS.get(name, name))} {count}" for name, count in counts.items())]
        if excluded:
            header.append(f"새 소재 {len(ordered)}개 · 중복 {excluded}개 제외")
        if ordered and any(s.get("category") for s in ordered):
            communities = sum(is_community(s) for s in ordered)
            header.append(f"커뮤니티 {communities}개 · 기사 {len(ordered) - communities}개")
        if errors:
            failed = ["펨코 직접" if name == "펨코 포텐" else SOURCE_LABELS.get(name, name) for name in errors if not name.startswith("텔레그램")]
            if failed:
                header.append("⚠ " + html.escape("·".join(failed)) + " 수집 불가")
        if not ordered:
            header.append("이번 회차에 새로 보낼 소재가 없습니다.")
        else:
            header += ["", "<b>🔥 먼저 볼 5개</b>" if len(ordered) >= 5 else "<b>🔥 먼저 볼 소재</b>"]
            header.extend(_compact_row(s, i, state, width, True) for i, s in enumerate(ordered[:5], 1))
            if len(ordered) > 5:
                tail = [f"<b>나머지 {len(ordered) - 5}개 · 펼쳐보기</b>"]
                tail.extend(_compact_row(s, i, state, max(16, width - 8)) for i, s in enumerate(ordered[5:], 6))
                header += ["", "<blockquote expandable>" + "\n".join(tail) + "</blockquote>"]
            header += ["", "상세 <code>/info 03</code> · 선정 <code>/pick 03</code>",
                       "번호는 최신 소재함 기준 · 명령은 약 10분 간격 반영"]
        text = "\n".join(header)
        if message_units(text) <= 3900:
            return [text]
    raise ValueError("전체 후보를 단일 텔레그램 메시지에 담지 못했습니다")


def render_info(record, key, status=None):
    samples = record.get("samples", [])
    last = samples[-1] if samples else {}
    row = {**record, "source": record.get("source", "선정 소재"), "rank": last.get("rank", 0), "views": last.get("views"),
           "reactions": last.get("reactions"), "new": False, "change": {}}
    assessment = assess({"lead": row, "members": [row]})
    detail = record.get("detail", {})
    lines = [link(record["title"], record["link"]),
             html.escape(row["source"]) + " · " + STATUS_NAMES.get(status, "미선정"),
             "", "원문 미리보기: " + html.escape(detail.get("excerpt") or detail.get("unavailable", "자동 미리보기 없음")),
             "btp 포인트: " + html.escape(" · ".join(assessment["reasons"][:2])),
             html.escape(reaction_text(row))]
    for media in detail.get("media", [])[:2]:
        lines.append(link(media["label"], media["url"]))
    for original in detail.get("source_links", [])[:2]:
        lines.append(link(original["label"], original["url"]))
    for original in detail.get("fmkorea_links", [])[:2]:
        lines.append(link(original["label"], original["url"]))
    if record.get("discovery"):
        lines.append("발견 경로: " + link(record["discovery"], record["discovery_url"]))
        if record.get("discovery_observed_at"):
            label = "외부 목록 관측" if record.get("discovery_timestamp_kind") == "index_observed" else "외부 목록에 표시된 게시 시각"
            lines.append(label + ": " + stamp(record["discovery_observed_at"]) + " · 사건 발생일 아님")
    lines.extend("확인: " + html.escape(caution) for caution in assessment["cautions"])
    lines.append(f"소재 ID <code>{key}</code>")
    return "\n".join(lines)

