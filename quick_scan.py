"""Bounded research inbox. No network, model calls, approval, or delivery."""
import re
from urllib.parse import urlsplit

FOOTBALL = re.compile(r"축구|손흥민|김민재|이강인|안토니|맨유|맨시티|아스[널날]|토트넘|레알|바르셀로나|K리그|football|soccer", re.I)
IDOL = re.compile(r"여돌|걸그룹|여자.?아이돌|레드벨벳|블랙핑크|트와이스|아이브|에스파|르세라핌|뉴진스|엔믹스|아일릿|베이비몬스터|키스오브라이프|스테이씨|하츠투하츠|장원영|안유진|카리나|윈터", re.I)
HOOK = re.compile(r"실수|돌발|대처|반전|자막|농담|웃|ㅋㅋ|논란|퇴장|충돌|황당|번복|항의|말실수|사과|banter|joke|bizarre|mistake", re.I)


def inbox(pool, now):
    queues = {name: [] for name in ("football", "idol", "community")}
    seen = set()
    for row in pool.get("items", []):
        url = row.get("link", "")
        observed, published = row.get("observed_at"), row.get("video_published_at")
        if (not url or url in seen or type(observed) is not int or not 0 <= now - observed <= 12 * 3600
                or (type(published) is int and not 0 <= now - published <= 12 * 3600)):
            continue
        seen.add(url)
        title = row.get("title", "")
        name = ("football" if row.get("topic_hint") == "football"
                or row.get("video_section") in {"kfootball", "wfootball"} or FOOTBALL.search(title)
                else "idol" if row.get("topic_hint") == "idol" or IDOL.search(title) else "community")
        direct = row.get("content_kind") == "video_source" or (urlsplit(url).hostname or "") in {
            "youtube.com", "www.youtube.com", "youtu.be", "x.com", "instagram.com", "www.instagram.com"}
        queues[name].append((not direct, not bool(HOOK.search(title)), -observed, row))
    for queue in queues.values():
        queue.sort(key=lambda value: value[:3])
    picks = []
    # Sampling lanes are a research budget, not publication quotas.
    for i in range(7):
        for name, queue in queues.items():
            if i < len(queue):
                row = queue[i][3]
                picks.append({"lane": name, "title": row["title"][:150], "url": row["link"],
                              "context": row.get("context", "")[:220], "materials": row.get("materials", [])[:2],
                              "published_metadata": row.get("video_published_at"), "video_viewed": False})
    return {"version": 1, "generated_at": now, "mode": "hits_only",
            "budget": {"minutes": 10, "searches": 6, "opens": 24, "recommendations_target": 10},
            "source_errors": list(pool.get("errors", {})), "candidates": picks[:20],
            "caution": "발견용. 원본·최초 공개 시각·사실·중복·공유 포인트 검증 전이며 영상 시청 기록이 아니다."}
