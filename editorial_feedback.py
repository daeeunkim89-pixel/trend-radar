"""Evidence-based BTP publication feedback. Standard library; no network or tokens."""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

LEARNING_FILE = Path("data/editorial-learning.json")
DAY = 86400
WINDOW = 7 * DAY
PROFILE = "https://www.instagram.com/bythepulse/"
SCOPES = {"caption", "caption_and_media", "connected_media"}


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def verified_posts(learning, now):
    """Only actual same-fact reviews of this account, never name/title similarity."""
    result = []
    for post in (learning.get("observations", []) if isinstance(learning, dict) else []):
        if not isinstance(post, dict) or post.get("account") != "bythepulse" or post.get("scope") not in SCOPES:
            continue
        observed = post.get("observed_at")
        if type(observed) is not int or not now-WINDOW-DAY <= observed <= now+300:
            continue
        parsed = urlsplit(post.get("post_url", ""))
        if (parsed.scheme != "https" or parsed.hostname not in {"instagram.com", "www.instagram.com"}
                or not re.fullmatch(r"/(?:bythepulse/)?(?:p|reel)/[A-Za-z0-9_-]+/?", parsed.path)):
            continue
        published = post.get("published_at")
        if published is not None and (type(published) is not int or not 0 < published <= observed+300):
            continue
        keys = []
        for match in post.get("recommendation_matches", []) + post.get("fact_identities", []):
            if (isinstance(match, dict) and match.get("same_fact_verified") is True
                    and isinstance(match.get("event_key"), str) and match["event_key"].strip()
                    and isinstance(match.get("evidence"), str) and match["evidence"].strip()):
                keys.append(match["event_key"].lower())
        if keys:
            result.append({**post, "matched_keys": keys})
    return result


def filter_already_published(stories, now, path=LEARNING_FILE):
    learning = read_json(path, {"observations": []})
    known = set()
    for post in verified_posts(learning, now):
        if post["observed_at"] <= now:
            known.update(post["matched_keys"])
    kept = [s for s in stories if s.get("editorial", {}).get("event_key", "").lower() not in known]
    return kept, len(stories)-len(kept)


def complete_coverage(learning, start, end, now):
    for check in learning.get("profile_checks", []):
        if not isinstance(check, dict) or check.get("complete_feed_window") is not True:
            continue
        at, first, last = check.get("at"), check.get("coverage_start_at"), check.get("coverage_end_at")
        if (check.get("profile_url") == PROFILE and check.get("status") == "feed_observed"
                and all(type(v) is int for v in (at, first, last))
                and end <= at <= now+300 and first <= start and end <= last <= at):
            return True
    return False


def analyze(history, learning, now):
    posts = verified_posts(learning, now)
    cohort = {}
    delivery_rows = 0
    for edition in history.get("editions", []):
        sent = edition.get("at")
        if edition.get("delivery") != "sent" or type(sent) is not int or not now-WINDOW <= sent <= now:
            continue
        for rank, pick in enumerate(edition.get("picks", []), 1):
            key = pick.get("event_key", "").lower()
            if not key:
                continue
            delivery_rows += 1
            if key not in cohort or sent < cohort[key]["sent_at"]:
                cohort[key] = {"event_key": key, "title": pick.get("title", ""), "source_url": pick.get("url"),
                               "sent_at": sent, "rank": rank, "category": pick.get("category")}
    counts = {k: 0 for k in ("posted_after", "already_posted_before_send", "observed_timing_unknown",
                              "not_observed_in_complete_window", "pending", "unassessed")}
    records = []
    for key, item in cohort.items():
        matches = [p for p in posts if key in p["matched_keys"]]
        before = [p for p in matches if type(p.get("published_at")) is int and p["published_at"] < item["sent_at"]]
        after = [p for p in matches if type(p.get("published_at")) is int and p["published_at"] > item["sent_at"]]
        mature = now-item["sent_at"] >= DAY
        if before:
            status, matched = "already_posted_before_send", min(before, key=lambda p:p["published_at"])
        elif after:
            status, matched = "posted_after", min(after, key=lambda p:p["published_at"])
        elif matches:
            status, matched = "observed_timing_unknown", matches[0]
        elif not mature:
            status, matched = "pending", None
        elif complete_coverage(learning, item["sent_at"], item["sent_at"]+DAY, now):
            status, matched = "not_observed_in_complete_window", None
        else:
            status, matched = "unassessed", None
        counts[status] += 1
        records.append({**item, "matured_24h": mature, "status": status,
                        "post_url": matched["post_url"] if matched else None,
                        "post_published_at": matched.get("published_at") if matched else None,
                        "reason": ("BTP was already published; this recommendation arrived late" if before else
                                   "Same fact observed publicly; use of our recommendation is not established" if after else
                                   "Absence is not proof of editorial rejection")})
    mature = [r for r in records if r["matured_24h"]]
    unassessed = sum(r["status"] in {"unassessed", "observed_timing_unknown"} for r in mature)
    matches = sum(r["status"] == "posted_after" for r in mature)
    rate = matches/len(mature) if mature and not unassessed else None
    checks = [c for c in learning.get("profile_checks", []) if isinstance(c, dict) and type(c.get("at")) is int and c["at"] <= now+300]
    latest = max(checks, key=lambda c:c["at"], default={})
    return {"version": 1, "updated_at": now, "account": "bythepulse", "window_days": 7,
            "observation_period_hours": 24,
            "access": {"last_check_at": latest.get("at"), "status": latest.get("status", "not_checked"),
                       "limits": latest.get("limits", [])},
            "summary": {"sent_rows": delivery_rows, "unique_recommendations": len(records),
                        "matured_recommendations": len(mature), "unassessed_matured": unassessed,
                        **counts, "publication_match_rate": rate, "rate_denominator": len(mature) if rate is not None else 0,
                        "direct_adoption_rate": None,
                        "top3_posted_after": sum(r["rank"] <= 3 and r["status"] == "posted_after" for r in records),
                        "confirmed_observed_posts": len(posts)},
            "limits": ["Public same-fact overlap is not proof the recommendation was used.",
                       "Incomplete/blocked access is unknown, never a zero adoption rate.",
                       "A 24h non-match is an observation, not a confirmed rejection reason.",
                       "Post captions/times need actual observation; title/person overlap is insufficient."],
            "records": records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=Path, default=Path("data/editorial-history.json"))
    parser.add_argument("--learning", type=Path, default=LEARNING_FILE)
    parser.add_argument("--output", type=Path, default=Path("data/editorial-feedback.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    result = analyze(read_json(args.history, {}), read_json(args.learning, {}), int(time.time()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"access": result["access"], "summary": result["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
