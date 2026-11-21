"""Small discovery queue for football fan stories and major public-interest news.

This ranks leads, never verifies a scene or chooses delivery recommendations.
"""
import re
from edition_preflight import REPORT_PICKS
from urllib.parse import urlsplit

FOOTBALL = re.compile(r"축구|손흥민|김민재|이강인|황희찬|황인범|오현규|이재성|이승우|"
                      r"호날두|메시(?!지)|음바페|홀란|흐비차|크바라츠헬리아|호나우지뉴|수아레[즈스]|"
                      r"모리야스|안첼로티|모레노|박항서|피케|돈나룸마|"
                      r"맨유|맨시티|리버풀|첼시|아스[널날]|토트넘|레알|바르셀로나|뮌헨|PSG|LAFC|K리그|"
                      r"football|soccer", re.I)
FAN_STORY = re.compile(r"트위치|스트리밍|스트리머|게임.?방송|어머니|엄마|"
                      r"직접.?발언|직접.?영상|인터뷰|고백|반박|해명|불만|폭로|징계|"
                      r"유니폼|세리머니|팬.?서비스|팬.?반응|관중|오심|VAR|"
                      r"헤더|감차|반대.?전환|원더골|극장골|선방|드리블|볼.?터치|"
                      r"livestream|celebration|interview", re.I)
IDOL = re.compile(r"여돌|걸그룹|여자.?아이돌|레드벨벳|블랙핑크|트와이스|아이브|에스파|르세라핌|뉴진스|엔믹스|아일릿|베이비몬스터|키스오브라이프|스테이씨|하츠투하츠|장원영|안유진|카리나|윈터", re.I)
PROMO = re.compile(r"teaser|concept photo|mood film|track list|highlight medley|예약.?판매|공항패션|화보|그라비아|운세|실거래가|종목.?추천", re.I)


SPORTS = re.compile(r"야구|농구|배구|테니스|배드민턴|KBO|MLB|NBA|오타니|이정후|김하성|안세영|baseball|basketball", re.I)
SPORT_MAJOR = re.compile(r"우승|준우승|결승|탈락|강등|승격|해트트릭|신기록|역대|최초|발롱도르|월드컵|올림픽|이적.*확정|영입.*확정|계약.*(?:체결|해지)|공식.*(?:영입|경질)|경질|사임|승부조작|영구.?제명|출전.?정지|부상.*(?:시즌|수술)|champion|world cup|record|signs|sacked", re.I)
PUBLIC_MAJOR = re.compile(r"대통령|탄핵|국회|선거|전쟁|침공|휴전|대규모|전국|전면|대형|참사|비상계엄|기준금리|금융위기|국민연금|개인정보.*유출|상장폐지|정부.*(?:조사|발표)|국정감사|성착취|집단.*피해|국민적|산업.*(?:중단|위기)", re.I)
ENTERTAINMENT = re.compile(r"아이돌|여돌|걸그룹|연예|예능|자컨|자체.?콘텐츠|팬미팅|팬서비스|공항패션|열애|결혼|컴백|티저|직캠|챌린지|자막|티키타카", re.I)


def entertainment(row):
    return bool(row.get("topic_hint") in {"idol", "entertainment"} or IDOL.search(row.get("title", ""))
                or ENTERTAINMENT.search(row.get("title", "")) or "연예" in row.get("source", ""))


def priority(row):
    """Order unverified leads; awards/records and hype words do not prove reader fit."""
    text = row.get("title", "") + " " + row.get("context", "")[:220]
    category = lane(row)
    hook = bool(FAN_STORY.search(text))
    tier = (0 if category == "football" and hook else
            1 if category == "football" else
            2 if category == "sports" and hook else
            3 if PUBLIC_MAJOR.search(text) else
            4 if category == "sports" else 5)
    return (tier, not original(row), -(publication(row) or row["observed_at"]))


def lane(row):
    title = row.get("title", "")
    if row.get("topic_hint") == "football" or row.get("video_section") in {"kfootball", "wfootball"} or "축구" in row.get("list_category", "") or FOOTBALL.search(title):
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


def _ranked_inbox(pool, now, max_age=24 * 3600):
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
                "hook_signal": bool(FAN_STORY.search(row["title"] + " " + row.get("context", "")[:220])),
                "discovery_observed_at": row.get("discovery_observed_at", row["observed_at"]),
                "discovery_timestamp_kind": row.get("discovery_timestamp_kind", "collector_observed"),
                "discovery_url": row.get("discovery_url"),
                "already_in_fmkorea_index": bool(row.get("origin") == "펨코" or row.get("source") == "펨코 간접"),
                "next_check": "독자가 멈출 구체적 새 행동·발언·장면을 원본에서 확인. 포텐 선행 여부·조회수는 미확인; 기사 수상/기록 단어만으로 추천하지 않음"}
        (candidates if len(candidates) < 20 else reserves).append(item)
        if len(reserves) >= 10:
            break
    return {"version": 2, "generated_at": now, "mode": "reader_hook_discovery",
            "reference": "docs/btp-news-policy-20261104.md",
            "budget": {"initial_searches": 6, "initial_opens": 18,
                       "extension_searches": 2, "extension_opens": 7, "max_extensions": 2,
                       "extend_until_target": False, "recommendations_target": REPORT_PICKS,
                       "reuse_discovery": True, "stop_when_target_ready": True,
                       "shortfall_recovery_searches": 4, "shortfall_recovery_opens": 12,
                       "max_shortfall_recoveries": 1, "max_total_searches": 14, "max_total_opens": 44},
            "source_errors": list(pool.get("errors", {})), "candidates": candidates, "reserves": reserves,
            "caution": "발견용이며 선정·사실·장면 검증 전. 축구팬의 구체적 새 행동/발언/장면부터 검토. 일반 연예 제외. 중계목록 등장은 포텐 인증·원본 확인·선발굴 실적이 아니며, 훅 단어는 흥행 예측이 아니다."}


def inbox(pool, now):
    result = _ranked_inbox(pool, now)
    result["extended_candidates"] = []
    result["budget"]["initial_freshness_hours"] = 24
    result["budget"]["extended_freshness_hours"] = []
    result["budget"]["selection_basis"] = "verified_reader_hook_not_trophy_or_record_keywords"
    return result
