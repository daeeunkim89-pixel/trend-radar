"""Refresh public discovery inputs for the hourly editor; never use Telegram."""
import json
import time
from pathlib import Path

from editorial import HISTORY_FILE, atomic_json, enrich, load_history, observe
from monitor import collect
from selection import context_candidates
from sports_video import SOURCE as VIDEO_SOURCE, fetch_public_videos

SNAPSHOT_FILE = Path("data/candidates.json")


def run():
    history = load_history()
    data, errors = collect(history, include_fmkorea_direct=False)
    now = int(time.time())
    try:
        data[VIDEO_SOURCE] = fetch_public_videos(now=now)
    except (ValueError, OSError) as error:
        data[VIDEO_SOURCE] = []
        errors[VIDEO_SOURCE] = str(error)[:180]
    stories, history = observe(data, history, now)
    enrich(context_candidates(stories), history, now)
    items = []
    for story in stories:
        for row in story["members"]:
            item = {k: row[k] for k in ("source", "title", "link", "views", "reactions", "change", "rank")}
            item.update(observed_at=now, story_id=story["id"])
            for k in ("content_kind", "listed_at", "discovery", "discovery_url", "discovery_observed_at", "discovery_timestamp_kind",
                      "video_id", "video_section", "video_provider", "video_published_at", "video_viewed"):
                if k in row:
                    item[k] = row[k]
            detail = story.get("detail", {})
            if detail:
                item["context"] = detail.get("context", "")[:700]
                item["materials"] = detail.get("media", [])[:3] + detail.get("source_links", [])[:3]
            items.append(item)
    atomic_json(HISTORY_FILE, history)
    status = "unavailable" if not items else "degraded" if errors else "ok"
    atomic_json(SNAPSHOT_FILE, {"version": 1, "generated_at": now, "status": status,
                               "errors": errors, "counts": {k: len(v) for k, v in data.items()}, "items": items})
    print("BTP DISCOVERY ONLY", json.dumps({"candidates": len(items), "counts": {k: len(v) for k, v in data.items()},
                                           "source_errors": list(errors), "status": status}, ensure_ascii=False))
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(run())

