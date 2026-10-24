"""Accumulate public discovery inputs between editions; never use Telegram."""
import argparse
import json
import time
from pathlib import Path

from editorial import atomic_json, canonical_url, enrich, load_history, observe
from monitor import collect
from selection import context_candidates
from sports_video import SOURCE as VIDEO_SOURCE, fetch_public_videos
from quick_scan import inbox

SNAPSHOT_FILE = Path("data/candidates.json")
DISCOVERY_HISTORY_FILE = Path("data/discovery-history.json")
POOL_RETENTION = 48 * 3600
POOL_LIMIT = 3000


def merge_pool(previous, current, now):
    """Retain missed list entries without changing when they were last seen.

    Discovery timestamps are neither publication dates nor editorial approval.
    """
    rows = {}
    for item in previous.get("items", []):
        observed = item.get("observed_at")
        if type(observed) is int and now - POOL_RETENTION <= observed <= now:
            key = canonical_url(item["link"])
            rows[key] = dict(item)
            rows[key].setdefault("first_seen_at", observed)
    for item in current:
        key = canonical_url(item["link"])
        old = rows.get(key, {})
        rows[key] = dict(item, first_seen_at=old.get("first_seen_at", item.get("first_seen_at", now)))
    return sorted(rows.values(), key=lambda row: (-row["observed_at"], row.get("rank", 999)))[:POOL_LIMIT]


def run(min_refresh_seconds=0):
    # Separate history keeps collection independent of delivery's production lock.
    previous = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8")) if SNAPSHOT_FILE.exists() else {}
    now = int(time.time())
    generated = previous.get("generated_at")
    if (min_refresh_seconds > 0 and type(generated) is int
            and 0 <= now - generated < min_refresh_seconds
            and previous.get("fresh_count", 0) > 0
            and previous.get("status") in {"ok", "degraded"}):
        print("BTP DISCOVERY RECENT", json.dumps({"generated_at": generated,
              "age_seconds": now - generated}, ensure_ascii=False))
        return 0
    history = load_history(DISCOVERY_HISTORY_FILE)
    data, errors = collect(history, include_fmkorea_direct=False)
    now = int(time.time())
    try:
        data[VIDEO_SOURCE] = fetch_public_videos(now=now)
    except (ValueError, OSError) as error:
        data[VIDEO_SOURCE] = []
        errors[VIDEO_SOURCE] = str(error)[:180]
    stories, history = observe(data, history, now)
    # Body/media inspection is reserved for the bounded editorial shortlist.
    items = []
    for story in stories:
        for row in story["members"]:
            item = {k: row[k] for k in ("source", "title", "link", "views", "reactions", "change", "rank")}
            item.update(observed_at=now, first_seen_at=row.get("first_seen_at", now), story_id=story["id"])
            for k in ("topic_hint", "content_kind", "listed_at", "discovery", "discovery_url", "discovery_observed_at", "discovery_timestamp_kind",
                      "video_id", "video_section", "video_provider", "video_published_at", "video_viewed"):
                if k in row:
                    item[k] = row[k]
            detail = story.get("detail", {})
            if detail:
                item["context"] = detail.get("context", "")[:700]
                item["materials"] = detail.get("media", [])[:3] + detail.get("source_links", [])[:3]
            items.append(item)
    atomic_json(DISCOVERY_HISTORY_FILE, history)
    status = "unavailable" if not items else "degraded" if errors else "ok"
    fresh_count = len(items)
    pool = merge_pool(previous, items, now)
    atomic_json(SNAPSHOT_FILE, {"version": 1, "generated_at": now, "status": status,
                               "errors": errors, "counts": {k: len(v) for k, v in data.items()},
                               "fresh_count": fresh_count, "pool_count": len(pool),
                               "retained_count": sum(row["observed_at"] != now for row in pool), "items": pool})
    atomic_json(Path("data/review-inbox.json"), inbox({"items": pool, "errors": errors}, now))
    print("BTP DISCOVERY ONLY", json.dumps({"candidates": fresh_count, "pool": len(pool), "counts": {k: len(v) for k, v in data.items()},
                                           "source_errors": list(errors), "status": status}, ensure_ascii=False))
    return 0 if items else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-refresh-seconds", type=int, default=0)
    args = parser.parse_args()
    if args.min_refresh_seconds < 0:
        parser.error("Refresh interval cannot be negative")
    raise SystemExit(run(args.min_refresh_seconds))


