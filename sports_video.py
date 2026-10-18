"""Public Naver Sports video discovery; metadata is not evidence of viewing."""
import time
from datetime import datetime, timedelta, timezone

import requests

LIST_URL = ("https://api-gw.sports.naver.com/video/lists/total"
            "?sort=date&pageSize=60&page=1&fields=basic,naverTvChannel,upperSectionId")
SOURCE = "네이버 스포츠 영상"
SECTIONS = {"kfootball", "wfootball", "kbaseball", "wbaseball", "basketball", "volleyball", "golf", "general"}
KST = timezone(timedelta(hours=9))


def parse_videos(payload, now=None):
    now = int(time.time() if now is None else now)
    if not isinstance(payload, dict) or payload.get("code") != 200:
        raise ValueError("Invalid public sports video response")
    result = payload.get("result")
    videos = result.get("videos") if isinstance(result, dict) else None
    if not isinstance(videos, list):
        raise ValueError("Missing public sports video list")
    result, seen = [], set()
    for video in videos:
        if not isinstance(video, dict):
            continue
        identity, section = video.get("sportsVideoId"), video.get("upperSectionId")
        title = video.get("title")
        if (type(identity) is not int or identity <= 0 or identity in seen or section not in SECTIONS
                or not isinstance(title, str) or len(title.strip()) < 4):
            continue
        try:
            published = datetime.fromisoformat(video["produceDateTime"])
            published = published if published.tzinfo else published.replace(tzinfo=KST)
            published = int(published.timestamp())
        except (KeyError, TypeError, ValueError):
            continue
        if not now - 86400 <= published <= now + 300:
            continue
        provider = video.get("naverTvChannel")
        provider = provider if isinstance(provider, dict) else {}
        seen.add(identity)
        result.append({"source": SOURCE, "title": " ".join(title.split())[:220],
                       "link": f"https://m.sports.naver.com/{section}/video/{identity}",
                       "rank": len(result) + 1, "views": None, "reactions": None,
                       "parser_revision": 1, "content_kind": "video_source",
                       "discovery": "네이버 스포츠 공개 영상 목록", "discovery_url": LIST_URL,
                       "discovery_observed_at": now, "discovery_timestamp_kind": "index_observed",
                       "video_id": identity, "video_section": section,
                       "video_provider": str(provider.get("channelName", ""))[:80],
                       "video_published_at": published, "video_viewed": False})
    return result


def fetch_public_videos(now=None):
    response = requests.get(LIST_URL, timeout=(5, 12))
    response.raise_for_status()
    rows = parse_videos(response.json(), now)
    if not rows:
        raise ValueError("공개 스포츠 영상 목록에 24시간 안의 후보가 없습니다")
    return rows
