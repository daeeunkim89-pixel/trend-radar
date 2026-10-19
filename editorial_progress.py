"""Resume human/agent research without approving or sending any Telegram report."""
import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from curated_report import CATEGORIES, load_edition, public_url, text
from editorial import atomic_json, canonical_url
from report_timing import KST, require_report_slot

PROGRESS_FILE = Path("data/editorial-progress.json")
RETENTION = 48 * 3600
REVIEW_TTL = 75 * 60
NOTE_STATES = {"needs_facts", "needs_date", "needs_visual", "rejected"}


def read_json(path, default):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else default


def load_research_review(path, target, now):
    """Validate working picks now, even when the eventual report is hours away.

    The working edition must use the actual current UTC hour. This does not
    make a future delivery request valid or refresh any verification timestamp.
    """
    current = int(now) // 3600 * 3600
    require_report_slot(target)
    if not 7 <= datetime.fromtimestamp(now, KST).hour <= 23 or not 0 <= target - current <= 4 * 3600:
        raise ValueError("Research checkpoint is outside the current daytime cycle")
    edition = load_edition(path, current, now)
    if edition["version"] != 2:
        raise ValueError("New reviews require edition version 2")
    return edition


def delivery_identities(history, now):
    """Collection or review history alone must never count as a sent event."""
    keys, urls = set(), set()
    for edition in history.get("editions", []):
        if edition.get("delivery") not in {"sent", "already_sent", "uncertain"} or edition.get("at", 0) < now - 7 * 86400:
            continue
        for pick in edition.get("picks", []):
            keys.add(pick["event_key"])
            urls.add(canonical_url(pick["url"]))
    return keys, urls


def summarize(pool, progress, history, now, limit=24):
    sent_keys, sent_urls = delivery_identities(history, now)
    ready, unfinished, rejected, seen = [], [], [], set()
    for row in progress.get("items", []):
        if not 0 <= now - row.get("recorded_at", now) <= RETENTION:
            continue
        url = canonical_url(row["url"])
        if row["event_key"] in sent_keys or url in sent_urls:
            continue
        seen.add(url)
        if row["status"] == "rejected":
            rejected.append(row)
        elif row["status"] == "reviewed" and 0 <= now - row["pick"]["verified_at"] <= REVIEW_TTL:
            ready.append(row)
        else:
            unfinished.append(dict(row, status="needs_recheck") if row["status"] == "reviewed" else row)
    pending = [r for r in pool.get("items", []) if canonical_url(r["link"]) not in seen | sent_urls
               and 0 <= now - r["observed_at"] <= RETENTION]
    # Present different sources, not twenty-four similar rows from one list.
    source_counts, preview = Counter(), []
    for row in sorted(pending, key=lambda r: (-r["observed_at"], r.get("rank", 999))):
        if source_counts[row["source"]] < 3 and len(preview) < limit:
            preview.append({k: row[k] for k in ("source", "title", "link", "observed_at")})
            source_counts[row["source"]] += 1
    return {"reviewed_available": len(ready), "missing": max(0, 10 - len(ready)),
            "resume": ready + unfinished, "rejected": rejected,
            "unreviewed_count": len(pending), "unreviewed_sample": preview,
            "latest_attempt": progress.get("attempts", [])[-1:]}


def save_progress(path, hour, now, history, notes=(), edition=None, stage=None):
    """Persist work even when fewer than ten picks are ready; never request delivery."""
    datetime.strptime(hour, "%Y%m%d%H")
    if len(hour) != 10:
        raise ValueError("Invalid research hour")
    progress = read_json(path, {"version": 1, "items": [], "attempts": []})
    if progress.get("version") != 1:
        raise ValueError("Invalid research progress version")
    rows = {row["event_key"]: row for row in progress["items"] if row["recorded_at"] >= now - RETENTION}
    for note in notes:
        if set(note) != {"event_key", "url", "title", "category", "status", "note", "next_action"}:
            raise ValueError("Invalid research note")
        if note["status"] not in NOTE_STATES or note["category"] not in CATEGORIES:
            raise ValueError("A note cannot claim a completed review")
        row = dict(note, event_key=text(note["event_key"], 160, "event_key").lower(),
                   url=public_url(note["url"]), title=text(note["title"], 90, "title"),
                   note=text(note["note"], 300, "note"),
                   next_action=text(note["next_action"], 200, "next_action"), recorded_at=now)
        rows[row["event_key"]] = row
    if edition:
        if edition.get("version") != 2:
            raise ValueError("New reviews require edition version 2")
        for pick in edition["picks"]:
            rows[pick["event_key"]] = {"event_key": pick["event_key"], "url": pick["url"],
                "title": pick["title"], "category": pick["category"], "status": "reviewed",
                "recorded_at": now, "pick": pick, "coverage": edition["coverage"]}
    progress["items"] = sorted(rows.values(), key=lambda r: r["recorded_at"], reverse=True)[:300]
    summary = summarize({"items": []}, progress, history, now)
    status = stage or ("review_complete" if summary["reviewed_available"] >= 10 else "research_incomplete")
    if status not in {"researching", "research_incomplete", "review_complete", "submitted"}:
        raise ValueError("Research progress cannot claim Telegram delivery")
    if status in {"review_complete", "submitted"} and summary["missing"]:
        raise ValueError("Fewer than ten fresh, not-publicly-sent reviews")
    attempt = {"hour_utc": hour, "at": now, "status": status, "required": 10,
               "ready": summary["reviewed_available"], "missing": summary["missing"],
               "unfinished": len(summary["resume"]) - summary["reviewed_available"]}
    progress["attempts"] = [a for a in progress.get("attempts", [])
                            if a["at"] >= now - 7 * 86400 and a["hour_utc"] != hour][-41:] + [attempt]
    progress["updated_at"] = now
    atomic_json(path, progress)
    return attempt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hour")
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--research-only", action="store_true",
                        help="Store current-hour working reviews for a later report without requesting delivery")
    parser.add_argument("--stage", choices=("researching", "research_incomplete", "review_complete", "submitted"))
    args = parser.parse_args()
    now = int(time.time())
    history = read_json("data/editorial-history.json", {"editions": []})
    if args.hour:
        target = int(datetime.strptime(args.hour + "+0000", "%Y%m%d%H%z").timestamp())
        edition = (load_research_review(args.review, target, now) if args.research_only
                   else load_edition(args.review, target, now)) if args.review else None
        if edition and edition["version"] != 2:
            raise ValueError("New reviews require edition version 2")
        result = save_progress(PROGRESS_FILE, args.hour, now, history,
                               read_json(args.notes, []) if args.notes else [], edition, args.stage)
    else:
        result = summarize(read_json("data/candidates.json", {"items": []}),
                           read_json(PROGRESS_FILE, {"items": []}), history, now)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
