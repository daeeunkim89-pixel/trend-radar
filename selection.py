"""Conservative BTP editorial gate. A topic/name match alone is not eligibility."""
import re
import math
from collections import Counter
from communities import COMMUNITY_HOSTS, is_community, material_urls
from urllib.parse import urlsplit

CATEGORIES = ("시사", "축구", "메이저 스포츠", "아이돌")
REPORT_LIMIT = 10
CATEGORY_LIMIT = 4
ARTICLE_LIMIT = 2
CONTEXT_LIMIT = 36

FOOTBALL = re.compile(
    r"축구|K리그|EPL|프리미어리그|챔피언스리그|라리가|세리에|분데스리가|MLS|"
    r"손흥민|김민재|이강인|황희찬|황인범|양민혁|오현규|이재성|이승우|조규성|"
    r"호날두|메시(?!지)|음바페|홀란|살라|제이미\s*바디|토트넘|맨유|맨시티|리버풀|"
    r"아스널|아스날|첼시|레알\s*(?:마드리드|소시에다드)|바르셀로나|뮌헨|PSG|울버햄튼|번리|LAFC|"
    r"전북현대|전북 현대|울산현대|울산 현대|울산HD|울산 HD|FC서울|수원삼성|포항스틸러스|"
    r"부천FC|부천 FC|기성용|조현우|주민규|일류첸코|프리킥|페널티킥|골키퍼", re.I)
SPORTS = re.compile(
    r"야구|농구|배구|배드민턴|테니스|골프|격투기|복싱|수영|육상|스피드스케이팅|"
    r"올림픽|세계선수권|패럴림픽|월드베이스볼|WBC|NBA|MLB|KBO|UFC|F1|"
    r"오타니|이정후|김하성|류현진|김도영|김연경|안세영|알카라스|조코비치|페르스타펜", re.I)
MALE_IDOL = re.compile(
    r"남자\s*아이돌|남돌|보이그룹|방탄소년단|엑소|세븐틴|스트레이키즈|엔시티|"
    r"투모로우바이투게더|투바투|엔하이픈|보이넥스트도어|제로베이스원|"
    r"투어스|에이티즈|더보이즈|샤이니|정국|지드래곤|차은우|백현|태민|"
    r"(?<![a-z])(?:BTS|EXO|NCT|ENHYPEN|RIIZE|ATEEZ)(?![a-z])", re.I)
IDOL_WORD = re.compile(r"아이돌|걸그룹|걸 그룹|보이그룹|남돌|여돌")
CONTEXTUAL_GROUP = re.compile(r"빅뱅|라이즈|(?<![a-z])(?:TXT|TWS)(?![a-z])", re.I)
MUSIC_CONTEXT = re.compile(r"팬|무대|컴백|신곡|직캠|챌린지|자막|콘서트|빌보드|안무")
IDOL_GROUP = re.compile(r"레드벨벳|블랙핑크|뉴진스|에스파|르세라핌|아이브|트와이스|엔믹스|아일릿|"
                        r"키스오브라이프|베이비몬스터|소녀시대|스테이씨|하츠투하츠|아이린|슬기|웬디|예리|"
                        r"장원영|안유진|카리나|닝닝|홍은채|허윤진|설윤|(?<![가-힣])조이(?![가-힣])")

LOW_VALUE = re.compile(r"모닝셀카|셀카 공개|출근길|퇴근길|포토타임|공항패션|화보 공개|화보 촬영|"
                       r"모델 발탁|앰버서더 발탁|제작발표회|시사회 참석|인터뷰 공개|근황 공개|역대급 미모|동안 미모")
OBJECTIFYING = re.compile(r"ㅇㅎ|약후|후방주의|검스|가슴|엉덩|골반|몸매|노출 의상|가랑이")
ROUTINE_NEWS = re.compile(r"빈소|조문|영결식|장례|애도|논평|설전|공방|저격|정치권 반응|압수수색|송치|구속영장")
SPECULATION = re.compile(r"가능성|이적설|영입설|갈등설|불화설|은퇴하면|은퇴할까|수도 있다|영입하나|러브콜|관심|필요해|정조준|우승.*도전|결승.*(?:노린|도전)")
CONFIRMED = re.compile(r"공식|확정|완료|체결|우승했다|우승 달성|금메달 획득|결승골|데뷔골|신기록|역대\s*(?:최다|최초)|기록\s*달성")
FOOTBALL_HOOK = re.compile(
    r"데뷔골|결승골|극장골|원더골|멀티골|해트트릭|선제골|동점골|골장면|골 장면|"
    r"프리킥|바이시클|오버헤드킥|자책골|추가골|쐐기골|슈퍼세이브|선방|드리블|팬.*반응|VAR|오심|골 취소|퇴장|폭행|승부조작|"
    r"역전승|우승|강등|승격|기록|최초|최다|최연소|최고령|공식|확정|전격 경질|"
    r"은퇴 선언|은퇴 발표|팬 서비스|팬서비스|웃음|반전|발롱도르|단독 선두|단독선두|\d+골\s*\d+도움", re.I)
MAJOR_SPORT_HOOK = re.compile(
    r"우승|신기록|최초|최다|최연소|최고령|금메달|세계\s*1위|MVP|명예의\s*전당|"
    r"영구결번|은퇴 선언|은퇴 발표|시즌\s*아웃|월드시리즈|한국시리즈|그랜드슬램|"
    r"공식.*(?:계약|입단)|(?:계약|입단).*확정|\d+억.*계약|\d+연승|\d+승\s*\d+패", re.I)
IDOL_HOOKS = (
    (r"반영\s*빠르|팬.*(?:요청|댓글|부탁)|자막.*(?:크|커|변경)|전후\s*비교|비포\s*애프터", "팬 반응·전후 변화"),
    (r"반전|뜻밖|깜짝|대처|돌발|실수|사고.*(?:무대|공연)|앵콜|라이브 실력|표정.*반응|웃음|빵\s*터|공중제비", "장면·반응 포인트"),
    (r"챌린지.*(?:당황|실수|반전|웃|화제|반응|ㅋㅋ|역대)|(?:당황|실수|반전|웃|화제|반응|ㅋㅋ|역대).*챌린지|커버.*(?:화제|반응)|직캠.*(?:조회|만|억|화제)|떼창|팬서비스|팬 서비스|역주행|밈", "무대·참여 확산 소재"),
    (r"빌보드|그래미|기네스|최초|최다|신기록|역대|\d+억\s*(?:뷰|회)|\d+만\s*(?:뷰|명)|재결합.*확정", "주요 성과·기록"),
    (r"공식.*(?:열애|결혼|해체|복귀)|(?:열애|결혼|해체|재결합).*확정|입대 발표", "확인된 주요 활동 소식"),
)
LIVING = re.compile(r"전기요금|가스요금|교통비|대중교통|지하철|버스요금|통신비|보험료|건강보험|"
                    r"국민연금|최저임금|주4일|대출금리|주담대|기준금리|월급|물가|가격|세금|전세|청약")
LIVING_CHANGE = re.compile(r"인상|인하|도입|시행|확정|폐지|중단|금지|무료|의무|돌파|폭등|폭락|변경|멋대로|유출")
PUBLIC_SCALE = re.compile(r"전국|전국민|대규모|수천\s*명|수만\s*명|100만|억\s*명|전세계|먹통|대란|대형|전면|일제히")
PUBLIC_EVENT = re.compile(r"유출|해킹|리콜|파업|폭발|지진|산불|폭우|참사|침수|결항|정전|통신|은행|카드|교통|공항|사기|폐쇄|마비")
PUBLIC_FIGURE = re.compile(r"백악관|대통령|총리|장관|국왕|교황|국회의원|CEO|머스크|저커버그", re.I)
UNEXPECTED_EVENT = re.compile(r"허위경력|허위 경력|가짜 변호사|최단명|전격.*(?:해임|경질)|체포|구속|사퇴|파면|탄핵.*가결")
SUBJECT = re.compile(r"손흥민|김민재|이강인|황희찬|황인범|양민혁|오현규|이재성|이승우|조규성|"
                     r"호날두|메시(?!지)|음바페|홀란|제이미\s*바디|오타니|이정후|김하성|류현진|김도영|김연경|안세영|"
                     r"레드벨벳|블랙핑크|뉴진스|에스파|르세라핌|아이브|트와이스|엔믹스|아일릿|"
                     r"장원영|안유진|카리나|윈터|제니|방탄소년단|BTS|엑소|세븐틴|샤이니|정국|백악관\s*대변인", re.I)
PUBLIC_LIFE = re.compile(r"소아과|응급실|병원|의료|노로바이러스|식중독|해산물|시내버스|택시|대중교통|"
                         r"소방관|통학|어린이집|학교급식|보행자|전기차|유튜브|인스타그램|개인정보|배달|소비자|관광객")
SOCIAL_HOOK = re.compile(r"강제\s*하차|승차\s*거부|사태|비상|중단|거절|강요|피해|먹으면|경고|유출|철회|"
                         r"환불|차별|구조|구출|전면|안전|바뀐|바꾸|판정|법안|단속")
COMMUNITY_SCENE = re.compile(r"반응|댓글|대처|표정|실수|깜짝|웃|팬서비스|팬 서비스|레전드|ㅋㅋ|ㄷㄷ|반영|변화|장면|플타")
PLAYOFF = re.compile(r"준PO|플레이오프|한국시리즈|월드시리즈|가을야구|포스트시즌|KBO\s*PS", re.I)
DECISIVE_SPORT = re.compile(r"멀티\s*홈런|역전.*홈런|끝내기|결승|승리.*확정|우승|역전승")
INSTITUTION = re.compile(r"(?<![가-힣])([가-힣]{2,6}(?:대학교|대학병원|병원|초등학교|고등학교|어린이집)|[가-힣]{2,4}대)(?:\s|[,.])")
FAN_ALLEGATION = re.compile(r"난투극|폭행|왕따|따돌림|사생활|열애설|불화설")
SPORT_OPINION = re.compile(r"TOP\s*\d+|Top\s*\d+|반박할|논리가|거임|어떻게\s*생각|누가\s*더|입단\s*순위")
CLICKBAIT = re.compile(r"얼마나\s*더|더\s*잘해야|폭탄\s*발언|대반전|러브콜")


def visual(story):
    detail = story.get("detail", {})
    return bool(detail.get("media") or detail.get("source_links"))


def public_interest(story):
    """Observed counters only provide ordering, never proof of a claim or virality."""
    return max((min(12, math.log1p(x.get("views") or 0))
                + min(8, math.log1p(x.get("reactions") or 0))
                + min(6, math.log1p(x.get("comments") or 0)) for x in story["members"]), default=0)


def material_keys(story):
    return material_urls(story.get("detail", {}))


def subject_key(story):
    match = SUBJECT.search(story["lead"]["title"])
    if match:
        return story["category"], re.sub(r"\s+", "", match[0]).lower()
    institution = INSTITUTION.search(story["lead"]["title"]) if story["category"] == "시사" else None
    return ("시사", institution[1]) if institution else None


def qualify(story):
    title = story["lead"]["title"]
    members = story["members"]
    community = is_community(story)
    text = title + (" " + story.get("detail", {}).get("context", "")[:1200] if community else "")
    listed_category = " ".join(x.get("list_category", "") for x in members)
    if OBJECTIFYING.search(title):
        return None
    idol = ("여자 아이돌" in story.get("tags", []) or IDOL_WORD.search(title) or IDOL_GROUP.search(title) or MALE_IDOL.search(title)
            or (CONTEXTUAL_GROUP.search(title) and MUSIC_CONTEXT.search(title))
            or (community and IDOL_GROUP.search(text) and MUSIC_CONTEXT.search(text)))
    if idol:
        if LOW_VALUE.search(title) or (community and FAN_ALLEGATION.search(title)):
            return None
        for pattern, reason in IDOL_HOOKS:
            if re.search(pattern, text, re.I):
                return "아이돌", reason
        if community and visual(story) and COMMUNITY_SCENE.search(text) and public_interest(story) >= 10:
            return "아이돌", "장면·팬 반응이 있는 커뮤니티 글"
        return None
    football = FOOTBALL.search(text) or "축구" in listed_category or any(x.get("topic_hint") == "football" for x in members)
    if football:
        if not community and CLICKBAIT.search(title) and not re.search(r"결승골|데뷔골|해트트릭|신기록|이적\s*확정|입단\s*확정", title):
            return None
        if SPECULATION.search(title) and not CONFIRMED.search(title):
            return None
        if FOOTBALL_HOOK.search(text):
            return "축구", "경기 장면·결정적 변화"
        if community and visual(story) and COMMUNITY_SCENE.search(text) and public_interest(story) >= 10:
            return "축구", "선수·팬 반응이 담긴 장면"
        return None
    sport = SPORTS.search(text + " " + listed_category) or any(x["source"] == "네이트 스포츠" for x in members)
    if sport:
        if community and (SPORT_OPINION.search(title) or (not visual(story) and not CONFIRMED.search(title))):
            return None
        if SPECULATION.search(title) and not CONFIRMED.search(title):
            return None
        if MAJOR_SPORT_HOOK.search(title):
            return "메이저 스포츠", "주요 성과·기록·확정 소식"
        if community and visual(story) and PLAYOFF.search(text) and DECISIVE_SPORT.search(text):
            return "메이저 스포츠", "주요 경기의 결정적 장면"
        return None
    if community and PUBLIC_LIFE.search(text) and SOCIAL_HOOK.search(text) and (visual(story) or public_interest(story) >= 10):
        return "시사", "생활에 닿는 사건·현장 반응"
    if ROUTINE_NEWS.search(title):
        return None
    if LIVING.search(title) and LIVING_CHANGE.search(title):
        return "시사", "생활에 직접 닿는 변화"
    if PUBLIC_SCALE.search(title) and PUBLIC_EVENT.search(title):
        return "시사", "영향 범위가 큰 사건"
    if PUBLIC_FIGURE.search(title) and UNEXPECTED_EVENT.search(title):
        return "시사", "주요 인물의 이례적 사건"
    return None


def context_candidates(stories, limit=CONTEXT_LIMIT):
    """Bounded, diverse body inspection before final selection, without news filling it."""
    candidates = []
    for story in stories:
        title = story["lead"]["title"]
        if not is_community(story) or OBJECTIFYING.search(title):
            continue
        if urlsplit(story["lead"]["link"]).hostname not in COMMUNITY_HOSTS - {"www.fmkorea.com", "m.fmkorea.com"}:
            continue
        topic = bool(FOOTBALL.search(title) or SPORTS.search(title) or IDOL_WORD.search(title)
                     or IDOL_GROUP.search(title) or MALE_IDOL.search(title) or PUBLIC_LIFE.search(title)
                     or "여자 아이돌" in story.get("tags", []) or qualify(story))
        # A few high-interest ambiguous captions are inspected too; generic games
        # and personal diary posts cannot outrank clearly relevant community posts.
        concrete = bool(qualify(story) or (PLAYOFF.search(title) and DECISIVE_SPORT.search(title))
                        or (FOOTBALL.search(title) and FOOTBALL_HOOK.search(title)))
        candidates.append((concrete, topic, public_interest(story), story))
    candidates.sort(key=lambda x: (not x[0], not x[1], -x[2], -x[3]["score"]))
    picked, per_source = [], Counter()
    for concrete, topic, interest, story in candidates:
        if len(picked) >= limit:
            break
        source = story["lead"]["source"]
        if per_source[source] >= 8 or (not topic and (interest < 14 or per_source[source] >= 2)):
            continue
        picked.append(story)
        per_source[source] += 1
    return picked


def select_stories(stories):
    eligible = []
    subjects = set()
    for story in sorted(stories, key=lambda s: (not is_community(s), -(s["score"] + public_interest(s) + 12 * visual(s)),
                                               -int(s["lead"].get("article_date", "0")))):
        review = qualify(story)
        if review:
            story = dict(story, category=review[0], review_reason=review[1])
            subject = subject_key(story)
            if subject and subject in subjects:
                continue
            if subject:
                subjects.add(subject)
            eligible.append(story)
    # Community originals lead. News can supplement, but can never fill an empty
    # community report: at most two article links in the whole ten-item digest.
    picked, ids, counts, articles, assets = [], set(), Counter(), 0, set()
    def add(story):
        nonlocal articles
        community = is_community(story)
        keys = material_keys(story)
        if (len(picked) >= REPORT_LIMIT or story["id"] in ids or counts[story["category"]] >= CATEGORY_LIMIT
                or (not community and articles >= ARTICLE_LIMIT) or keys.intersection(assets)):
            return False
        picked.append(story)
        ids.add(story["id"])
        counts[story["category"]] += 1
        articles += not community
        assets.update(keys)
        return True
    for category in CATEGORIES:
        first = next((s for s in eligible if s["category"] == category and is_community(s)), None)
        if first:
            add(first)
    for story in eligible:
        add(story)
    return picked
