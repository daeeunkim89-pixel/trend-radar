"""Small editorial discovery queue calibrated to the user-approved 23 October 20:00 batch.

This ranks leads, never verifies a scene or chooses delivery recommendations.
"""
import re
from urllib.parse import urlsplit

FOOTBALL = re.compile(r"축구|손흥민|김민재|이강인|맨유|맨시티|아스[널날]|토트넘|레알|바르셀로나|K리그|football|soccer", re.I)
IDOL = re.compile(r"여돌|걸그룹|여자.?아이돌|레드벨벳|블랙핑크|트와이스|아이브|에스파|르세라핌|뉴진스|엔믹스|아일릿|베이비몬스터|키스오브라이프|스테이씨|하츠투하츠|장원영|안유진|카리나|윈터", re.I)
HOOK = re.compile(r"실수|돌발|대처|반전|자막|농담|웃|ㅋㅋ|논란|퇴장|충돌|황당|번복|항의|말실수|사과|반박|거부|banter|joke|bizarre|mistake", re.I)
CONCRETE = re.compile(r"실종|사라진|기름띠|방화|빵.?봉지|소화기|진화|제압|임금|월급|체불|명의신탁|세금|배상|징역|구형|선고|구조|재입사|적발|자막|대처|농담|말실수|뒤집|cancel|rescue|walkout", re.I)
PROMO = re.compile(r"teaser|concept photo|mood film|track list|highlight medley|예약.?판매|공항패션|화보|그라비아|운세|실거래가|종목.?추천", re.I)


def lane(row):
    title = row.get("title", "")
    if row.get("topic_hint") == "football" or row.get("video_section") in {"kfootball", "wfootball"} or FOOTBALL.search(title):
        return "football"
    if row.get("topic_hint") == "idol" or IDOL.search(title):
        return "idol"
    return "community"


def original(row):
    host = (urlsplit(row.get("link", "")).hostname or "").lower()
    # Only registry feeds assert ownership. A YouTube reupload is just a lead.
    return row.get("source_role") == "original" or row.get("content_kind") == "video_source" or host == "fcbayern.com"


def publication(row):
    return next((row[key] for key in ("source_published_at", "video_published_at", "listed_at")
                 if type(row.get(key)) is int), None)


def inbox(pool, now):
    ranked, seen = [], set()
    for row in pool.get("items", []):
        url, title = row.get("link", ""), row.get("title", "")
        observed = row.get("observed_at")
        published = publication(row)
        identity = re.sub(r"[^가-힣a-z0-9]", "", title.lower())
        if (not url or not identity or url in seen or identity in seen
                or type(observed) is not int or not 0 <= now - observed <= 12 * 3600
                or (type(published) is int and not 0 <= now - published <= 12 * 3600)):
            continue
        has_hook = bool(HOOK.search(title) or CONCRETE.search(title))
        if PROMO.search(title) and not has_hook:
            continue
        seen.update((url, identity))
        direct = original(row)
        # Specific action/consequence beats a famous name or direct URL alone.
        priority = (not has_hook, not direct, -(published or observed))
        ranked.append((priority, row))
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
                "next_check": "원본의 실제 대사·행동·반전과 시각 확인" if original(row) else "당사자·제작사 원본 추적; 재기사 시각 사용 금지"}
        (candidates if len(candidates) < 20 else reserves).append(item)
        if len(reserves) >= 10:
            break
    return {"version": 2, "generated_at": now, "mode": "reference_ranked",
            "reference": "docs/btp-reference-20261023-20.md",
            "budget": {"minutes": 10, "searches": 6, "opens": 24, "recommendations_target": 10},
            "source_errors": list(pool.get("errors", {})), "candidates": candidates, "reserves": reserves,
            "caution": "발견용. 실제 장면·원본·날짜·중복 검증 전. 상위10개를 상대선정하며 모두 최상급이라는 문턱을 만들지 않는다."}
