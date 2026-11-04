"""Small editorial discovery queue for sports-led major news (4 November 2026).

This ranks leads, never verifies a scene or chooses delivery recommendations.
"""
import re
from urllib.parse import urlsplit

FOOTBALL = re.compile(r"축구|손흥민|김민재|이강인|맨유|맨시티|아스[널날]|토트넘|레알|바르셀로나|K리그|football|soccer", re.I)
IDOL = re.compile(r"여돌|걸그룹|여자.?아이돌|레드벨벳|블랙핑크|트와이스|아이브|에스파|르세라핌|뉴진스|엔믹스|아일릿|베이비몬스터|키스오브라이프|스테이씨|하츠투하츠|장원영|안유진|카리나|윈터", re.I)
HOOK = re.compile(r"실수|돌발|대처|반전|자막|농담|웃|ㅋㅋ|논란|퇴장|충돌|황당|번복|항의|말실수|사과|반박|거부|banter|joke|bizarre|mistake", re.I)
CONCRETE = re.compile(r"실종|사라진|기름띠|방화|빵.?봉지|소화기|진화|제압|임금|월급|체불|명의신탁|세금|배상|징역|구형|선고|구조|재입사|적발|자막|대처|농담|말실수|뒤집|cancel|rescue|walkout", re.I)
PROMO = re.compile(r"teaser|concept photo|mood film|track list|highlight medley|예약.?판매|공항패션|화보|그라비아|운세|실거래가|종목.?추천", re.I)


SPORTS = re.compile(r"야구|농구|배구|테니스|배드민턴|KBO|MLB|NBA|오타니|이정후|김하성|안세영|baseball|basketball", re.I)
SPORT_MAJOR = re.compile(r"우승|준우승|결승|탈락|강등|승격|해트트릭|신기록|역대|최초|발롱도르|월드컵|올림픽|이적.*확정|영입.*확정|계약.*(?:체결|해지)|공식.*(?:영입|경질)|경질|사임|승부조작|영구.?제명|출전.?정지|부상.*(?:시즌|수술)|champion|world cup|record|signs|sacked", re.I)
PUBLIC_MAJOR = re.compile(r"대통령|탄핵|국회|선거|전쟁|침공|휴전|대규모|전국|전면|대형|참사|비상계엄|기준금리|금융위기|국민연금|개인정보.*유출|상장폐지|정부.*(?:조사|발표)|국정감사|성착취|집단.*피해|국민적|산업.*(?:중단|위기)", re.I)
ENTERTAINMENT = re.compile(r"아이돌|여돌|걸그룹|연예|예능|자컨|자체.?콘텐츠|팬미팅|팬서비스|공항패션|열애|결혼|컴백|티저|직캠|챌린지|자막|티키타카", re.I)


def entertainment(row):
    return bool(row.get("topic_hint") in {"idol", "entertainment"} or IDOL.search(row.get("title", ""))
                or ENTERTAINMENT.search(row.get("title", "")) or "연예" in row.get("source", ""))


def priority(row):
    """Discovery order only; title signals cannot verify headline importance."""
    title = row.get("title", "")
    sport = lane(row) in {"football", "sports"}
    major = bool(SPORT_MAJOR.search(title)) if sport else bool(PUBLIC_MAJOR.search(title))
    return (0 if sport and major else 1 if major else 2 if sport else 3,
            not original(row), -(publication(row) or row["observed_at"]))


def lane(row):
    title = row.get("title", "")
    if row.get("topic_hint") == "football" or row.get("video_section") in {"kfootball", "wfootball"} or FOOTBALL.search(title):
        return "football"
    if SPORTS.search(title) or row.get("source") == "네이트 스포츠":
        return "sports"
    return "current_affairs"


def original(row):
    host = (urlsplit(row.get("link", "")).hostname or "").lower()
    # Only registry feeds assert ownership. A YouTube reupload is just a lead.
    return row.get("source_role") == "original" or row.get("content_kind") == "video_source" or host == "fcbayern.com"


def publication(row):
    return next((row[key] for key in ("source_published_at", "video_published_at", "listed_at")
                 if type(row.get(key)) is int), None)


def _ranked_inbox(pool, now, max_age=12 * 3600):
    ranked, seen = [], set()
    for row in pool.get("items", []):
        url, title = row.get("link", ""), row.get("title", "")
        observed = row.get("observed_at")
        published = publication(row)
        identity = re.sub(r"[^가-힣a-z0-9]", "", title.lower())
        if (not url or not identity or url in seen or identity in seen
                or type(observed) is not int or not 0 <= now - observed <= max_age
                or (type(published) is int and not 0 <= now - published <= max_age)):
            continue
        if entertainment(row) and not PUBLIC_MAJOR.search(title):
            continue
        if PROMO.search(title):
            continue
        seen.update((url, identity))
        ranked.append((priority(row), row))
    ranked.sort(key=lambda pair: pair[0])
    candidates, reserves, providers = [], [], {}
    for _, row in ranked:
        provider = row.get("source_channel_id")
        if provider and providers.get(provider, 0) >= 2:
            continue
        if provider:
            providers[provider] = providers.get(provider, 0) + 1
        published = publication(row)
        item = {"lane": lane(row), "title": row["title"][:150], "url": row["link"],
                "source": row.get("source", ""), "source_role": "original" if original(row) else "lead",
                "context": row.get("context", "")[:220], "materials": row.get("materials", [])[:2],
                "published_metadata": published, "video_viewed": False,
                "next_check": "주요 뉴스 가치·확정 여부·파급력과 실제 새 사실 확인; 영상 핵심인 경우만 장면 확인"}
        (candidates if len(candidates) < 20 else reserves).append(item)
        if len(reserves) >= 10:
            break
    return {"version": 2, "generated_at": now, "mode": "major_news_ranked",
            "reference": "docs/btp-news-policy-20261104.md",
            "budget": {"initial_minutes": 10, "initial_searches": 6, "initial_opens": 24,
                       "extension_searches": 4, "extension_opens": 12,
                       "extend_until_target": True, "recommendations_target": 5},
            "source_errors": list(pool.get("errors", {})), "candidates": candidates, "reserves": reserves,
            "caution": "발견용. 스포츠 중심·시사 대형 뉴스 우선. 연예 세부 소식 제외. 본문에서 1면 가치·새 사실·날짜·중복 확인 전이며 조회수 예측이 아니다."}


def inbox(pool, now):
    result = _ranked_inbox(pool, now)
    older = [row for row in pool.get("items", [])
             if type(publication(row)) is int and 12 * 3600 < now - publication(row) <= 48 * 3600]
    extended = _ranked_inbox({"items": older}, now, 48 * 3600)["candidates"]
    for item in extended:
        item["freshness_policy"] = "미발송 원본 확인 후 24시간, 필요시 48시간 확대; 실제 공개시각 표시"
    result["extended_candidates"] = extended
    result["budget"]["initial_freshness_hours"] = 12
    result["budget"]["extended_freshness_hours"] = [24, 48]
    return result
