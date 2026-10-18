"""Deliver an agent-reviewed BTP edition; collection scores never choose its contents."""
import argparse
import hashlib
import html
import ipaddress
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from editorial import (HISTORY_FILE, atomic_json, canonical_url,
                       link, load_history, message_units, observe, render_info, stamp)
from report_timing import hourly_key, prepared_target, recovery_target, require_report_slot, wait_for_target
from telegram_editor import (DeliveryUncertain, PrivateState, TelegramClient, TelegramError,
                             deliver_report, story_content_keys, unreported_stories)

PICKS_FILE = Path("data/editorial-picks.json")
STATE_FILE = Path("data/state.json")
DECISIONS_FILE = Path("data/editorial-history.json")
ATTEMPT_FILE = Path("data/editorial-status.json")
CATEGORIES = ("시사", "축구", "메이저 스포츠", "아이돌")
MAX_PICKS = 20  # Ten recommendations plus reviewed reserves for content deduplication.
REPORT_PICKS = 10
MAX_BYTES = 100_000


def text(value, maximum, name, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > maximum:
        raise ValueError(f"Invalid editorial field: {name}")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError(f"Invalid editorial control character: {name}")
    return " ".join(value.split())


def public_url(value):
    value = text(value, 2000, "url")
    try:
        p = urlsplit(value)
        host = (p.hostname or "").lower()
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            raise ValueError("Expected a public HTTPS source")
        if not host or "." not in host or host.endswith((".local", ".internal", ".localhost")):
            raise ValueError("Expected a public source hostname")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("IP source URLs are not accepted")
    except (ValueError, TypeError):
        raise ValueError("Invalid public source URL") from None
    return canonical_url(value)


def timestamp(value, now, name, max_age=None):
    if type(value) is not int or value <= 0 or value > now + 300:
        raise ValueError(f"Invalid editorial timestamp: {name}")
    if max_age is not None and now - value > max_age:
        raise ValueError(f"Expired editorial timestamp: {name}")
    return value


def load_edition(path, target, now=None, expected_sha256=None):
    now = int(time.time() if now is None else now)
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("Editorial file is too large")
    if expected_sha256 and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Editorial file does not match the pinned request")
    edition = json.loads(raw)
    required = {"version", "hour_utc", "reviewer", "generated_at", "coverage", "picks", "empty_reason"}
    if (not isinstance(edition, dict) or set(edition) != required or type(edition["version"]) is not int
            or edition["version"] not in (1, 2) or edition["reviewer"] != "ChatGPT"
            or edition["hour_utc"] != hourly_key(target).removeprefix("hourly-")):
        raise ValueError("Invalid or wrong-hour editorial edition")
    generated = timestamp(edition["generated_at"], now, "generated_at", 75 * 60)
    if generated < target - 20 * 60:
        raise ValueError("Editorial edition was prepared too early")
    coverage = edition["coverage"]
    if not isinstance(coverage, dict) or set(coverage) != {"queries", "opened_urls", "unavailable"}:
        raise ValueError("Editorial research coverage is required")
    if not isinstance(coverage["queries"], list) or not 4 <= len(coverage["queries"]) <= 40:
        raise ValueError("Research must cover the four requested fields")
    coverage["queries"] = [text(q, 250, "query") for q in coverage["queries"]]
    if not isinstance(coverage["opened_urls"], list) or len(coverage["opened_urls"]) > 80:
        raise ValueError("Invalid opened source list")
    coverage["opened_urls"] = [public_url(u) for u in coverage["opened_urls"]]
    opened = set(coverage["opened_urls"])
    if not isinstance(coverage["unavailable"], list) or len(coverage["unavailable"]) > 30:
        raise ValueError("Invalid unavailable source list")
    coverage["unavailable"] = [text(x, 180, "unavailable source") for x in coverage["unavailable"]]
    picks = edition["picks"]
    if not isinstance(picks, list) or len(picks) > MAX_PICKS:
        raise ValueError("An edition can contain at most twenty reviewed candidates")
    edition["empty_reason"] = text(edition["empty_reason"], 160, "empty_reason", empty=bool(picks))
    normalized, seen_urls, seen_events = [], set(), set()
    for pick in picks:
        fields = {"title", "category", "url", "source", "kind", "event_key", "why", "angle", "why_now",
                  "verified_at", "published_at", "evidence", "materials", "caution"}
        if edition["version"] == 2:
            fields.add("readiness")
        if not isinstance(pick, dict) or set(pick) != fields:
            raise ValueError("Invalid editorial recommendation schema")
        p = dict(pick)
        for name, maximum in (("title", 90), ("source", 40), ("event_key", 160), ("why", 180),
                              ("angle", 150), ("why_now", 180), ("caution", 150)):
            p[name] = text(p[name], maximum, name, empty=name == "caution")
        if p["category"] not in CATEGORIES or p["kind"] not in {"community", "social", "official", "article"}:
            raise ValueError("Invalid editorial category or source kind")
        p["url"] = public_url(p["url"])
        p["event_key"] = p["event_key"].lower()
        timestamp(p["verified_at"], now, "verified_at", 75 * 60)
        if p["published_at"] is not None:
            timestamp(p["published_at"], now, "published_at")
        if p["url"] not in opened:
            raise ValueError("The recommendation source was not recorded as opened")
        if p["url"] in seen_urls or p["event_key"] in seen_events:
            raise ValueError("Duplicate recommendation in the same edition")
        seen_urls.add(p["url"])
        seen_events.add(p["event_key"])
        if not isinstance(p["evidence"], list) or not 1 <= len(p["evidence"]) <= 3:
            raise ValueError("Each recommendation needs checked evidence")
        evidence = []
        for e in p["evidence"]:
            if not isinstance(e, dict) or set(e) != {"url", "note"}:
                raise ValueError("Invalid editorial evidence")
            u = public_url(e["url"])
            if u not in opened:
                raise ValueError("Evidence was not recorded as opened")
            evidence.append({"url": u, "note": text(e["note"], 220, "evidence note")})
        p["evidence"] = evidence
        if not isinstance(p["materials"], list) or len(p["materials"]) > 3:
            raise ValueError("Invalid editorial material list")
        materials = []
        for m in p["materials"]:
            if not isinstance(m, dict) or set(m) != {"url", "label", "kind"}:
                raise ValueError("Invalid editorial material")
            if m["kind"] not in {"image", "video", "source"}:
                raise ValueError("Invalid editorial material kind")
            u = public_url(m["url"])
            if u not in opened:
                raise ValueError("Material was not recorded as opened")
            materials.append({"url": u, "label": text(m["label"], 25, "material label"), "kind": m["kind"]})
        p["materials"] = materials
        if edition["version"] == 2:
            r = p["readiness"]
            if (not isinstance(r, dict) or set(r) != {"mode", "event_date", "observation", "checked_materials", "outline"}
                    or r["mode"] not in ("scene", "major_news")):
                raise ValueError("A production-ready recommendation needs a scene or major-news review")
            event_date = text(r["event_date"], 10, "event_date")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date):
                raise ValueError("An exact source-checked event date is required")
            if date.fromisoformat(event_date) > datetime.fromtimestamp(now, timezone(timedelta(hours=9))).date():
                raise ValueError("The reviewed event cannot be in the future")
            checked = r["checked_materials"]
            if not isinstance(checked, list) or len(checked) > 3:
                raise ValueError("Invalid inspected material list")
            checked = [public_url(u) for u in checked]
            visual = {m["url"] for m in materials if m["kind"] in ("image", "video")}
            if len(set(checked)) != len(checked) or not set(checked).issubset(visual):
                raise ValueError("Inspected material must be an opened image or video in this recommendation")
            if r["mode"] == "scene" and not checked:
                raise ValueError("A scene needs inspected defining media; a source link alone is insufficient")
            if not isinstance(r["outline"], list) or not 2 <= len(r["outline"]) <= 4:
                raise ValueError("A production outline needs two to four concrete cards or cuts")
            p["readiness"] = {"mode": r["mode"], "event_date": event_date,
                              "observation": text(r["observation"], 240, "observation"),
                              "checked_materials": checked,
                              "outline": [text(x, 120, "production step") for x in r["outline"]]}
            if message_units(render_info({"title": p["title"], "link": p["url"], "editorial": p}, "reviewed-edition")) > 3900:
                raise ValueError("Production details exceed the single-message limit; shorten the review")
        normalized.append(p)
    edition["picks"] = normalized
    return edition


def build_stories(edition, history, now):
    rows = [{"source": p["source"], "title": p["title"], "link": p["url"], "rank": i,
             "views": None, "reactions": None, "parser_revision": 7,
             "content_kind": p["kind"], "curation_event_key": p["event_key"]}
            for i, p in enumerate(edition["picks"], 1)]
    stories, history = observe({"편집장 선정": rows}, history, now)
    by_url = {p["url"]: (i, p) for i, p in enumerate(edition["picks"])}
    for story in stories:
        index, pick = min((by_url[m["link"]] for m in story["members"]), key=lambda x: x[0])
        detail = {"format": "원본 영상" if any(m["kind"] == "video" for m in pick["materials"]) else "카드뉴스",
                  "media": [m for m in pick["materials"] if m["kind"] in {"image", "video"}],
                  "source_links": [{"label": m["label"], "url": m["url"]} for m in pick["materials"]],
                  "excerpt": "", "context": pick["why_now"], "fetched_at": now, "parser_revision": 7}
        story.update(category=pick["category"], review_reason=pick["why"], editorial=pick, detail=detail,
                     editorial_order=index, score=100 - index)
        for member in story["members"]:
            member["curation_event_key"] = pick["event_key"]
            record = history["items"][member["item_id"]]
            record.update(editorial=pick, detail=detail, curation_event_key=pick["event_key"])
    return sorted(stories, key=lambda s: s["editorial_order"]), history


def render_edition(stories, target, empty_reason, excluded=0):
    if len(stories) > REPORT_PICKS:
        raise ValueError("Select ten recommendations before rendering")

    def short(value, maximum):
        return value if len(value) <= maximum else value[:maximum - 1].rstrip() + "…"

    # Keep ten usable summaries in one message; full text and evidence remain in /info.
    for title_size, why_size, angle_size, caution_size in ((72, 70, 64, 55), (60, 55, 50, 40), (48, 42, 38, 28)):
        lines = [f"<b>⚡ btp · 추천 {len(stories)}/{REPORT_PICKS} · {stamp(target)}</b>"]
        if not stories:
            lines += ["이번 시간 강하게 추천할 새 소재는 없습니다.", html.escape(empty_reason or "기존 발송 소재를 제외한 결과입니다.")]
        else:
            for i, story in enumerate(stories, 1):
                p = story["editorial"]
                lines += ["", "<b>" + ("🔥 지금 1순위" if i == 1 else f"{i:02d}") + " · " + html.escape(p["category"]) + "</b>",
                          link(short(p["title"], title_size), p["url"]),
                          "왜: " + html.escape(short(p["why"], why_size)),
                          "첫 장: " + html.escape(short(p["angle"], angle_size))]
                if p["materials"]:
                    m = p["materials"][0]
                    lines.append("자료: " + link(m["label"], m["url"]))
                if p["caution"]:
                    lines.append("확인: " + html.escape(short(p["caution"], caution_size)))
            if len(stories) < REPORT_PICKS:
                lines += ["", f"10개 중 {len(stories)}개 확보: " + html.escape(short(empty_reason or "검증·중복 제외 후 새 소재가 부족했습니다.", 100))]
            lines += ["", "전체 제목·검증·제작 <code>/info 1</code> · 선정 <code>/pick 1</code>"]
        if excluded:
            lines.append(f"기존 발송·같은 사건 {excluded}개 제외")
        result = "\n".join(lines)
        if message_units(result) <= 3900:
            return [result]
    raise ValueError("Editorial recommendations exceed the single-message limit")


def same_event_filter(stories):
    chosen, identities = [], set()
    for story in stories:
        keys = story_content_keys(story)
        if not identities.intersection(keys):
            chosen.append(story)
            identities.update(keys)
    return chosen


def record_decision(stories, target, now, delivery, delivery_key=None):
    """Public editorial decisions let the next researcher reuse event identities."""
    try:
        previous = json.loads(DECISIONS_FILE.read_text(encoding="utf-8")) if DECISIONS_FILE.exists() else {"version": 1, "editions": []}
        if previous.get("version") != 1 or not isinstance(previous.get("editions"), list):
            raise ValueError("Invalid public editorial history")
        delivery_key = delivery_key or hourly_key(target)
        rows = [r for r in previous["editions"] if r.get("at", 0) >= now - 7 * 86400
                and r.get("delivery_key", "hourly-" + r.get("hour_utc", "")) != delivery_key]
        rows.append({"hour_utc": hourly_key(target)[7:], "at": now, "delivery": delivery,
                     "delivery_key": delivery_key,
                     "picks": [{"title": s["lead"]["title"], "url": s["lead"]["link"],
                                "event_key": s["editorial"]["event_key"]} for s in stories]})
        atomic_json(DECISIONS_FILE, {"version": 1, "editions": rows[-168:]})
    except (ValueError, OSError, TypeError):
        print("BTP EDITORIAL HISTORY WARNING: public decision archive could not be updated")


def record_attempt(target, status, ready=0, excluded=0, user_requested=False):
    """Public, credential-free outcome; never overwrite the last confirmed send."""
    atomic_json(ATTEMPT_FILE, {"version": 1, "updated_at": int(time.time()),
                             "hour_utc": hourly_key(target)[7:], "status": status,
                             "ready": ready, "required": REPORT_PICKS,
                             "missing": max(0, REPORT_PICKS - ready),
                             "duplicates_excluded": excluded,
                             "trigger": "user_requested" if user_requested else "scheduled"})


def main(recover_hour=None, prepared_hour=None, picks_file=PICKS_FILE, expected_sha256=None, preview=False,
         user_requested=False):
    now = int(time.time())
    try:
        target = prepared_target(prepared_hour, now) if prepared_hour else recovery_target(recover_hour, now)
        if not preview:
            require_report_slot(target, user_requested=user_requested)
        edition = load_edition(picks_file, target, now, expected_sha256)
        if user_requested and (prepared_hour or not isinstance(expected_sha256, str)
                               or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
            raise ValueError("An on-demand edition requires a pinned current-hour request")
        delivery_key = "user-curated-" + expected_sha256 if user_requested else hourly_key(target)
        # Parse and bound everything before touching Telegram credentials.
        history = load_history()
        stories, history = build_stories(edition, history, now)
        stories = same_event_filter(stories)
        if preview:
            parts = render_edition(stories[:REPORT_PICKS], target, edition["empty_reason"])
            print("BTP EDITORIAL PREVIEW ONLY: no Telegram calls or state writes")
            print(parts[0])
            return 0
        if len(stories) < REPORT_PICKS:
            record_attempt(target, "insufficient_new_material", len(stories), user_requested=user_requested)
            print(f"BTP EDITORIAL SHORTFALL: {len(stories)}/{REPORT_PICKS}; no message sent")
            return 2
        token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
        client = TelegramClient(token, chat)
        client.verify()
        private = PrivateState(token, chat)
        previous = private.data.get("reports", {}).get(delivery_key, {})
        if previous.get("done") or previous.get("message_ids"):
            print("BTP EDITORIAL ALREADY_SENT: requested delivery ledger is complete")
            return 0
        if previous.get("uncertain"):
            raise DeliveryUncertain("이 시간대의 이전 전송 결과 확인이 필요합니다")
        before = len(stories)
        stories = unreported_stories(stories, history, private, now)
        excluded = before - len(stories)
        stories = stories[:REPORT_PICKS]
        if user_requested and not stories:
            record_attempt(target, "duplicate_edition", 0, excluded, user_requested)
            print("BTP EDITORIAL ON_DEMAND_SKIPPED: no new reviewed material after content deduplication")
            return 0
        if len(stories) != REPORT_PICKS:
            record_attempt(target, "insufficient_new_material", len(stories), excluded, user_requested)
            print(f"BTP EDITORIAL SHORTFALL: {len(stories)}/{REPORT_PICKS} after duplicate filter; no message sent")
            return 2
        parts = render_edition(stories, target, edition["empty_reason"], excluded)
        atomic_json(HISTORY_FILE, history)
        if not wait_for_target(target):
            print("BTP EDITORIAL EXPIRED: no past-hour report sent")
            return 2
        # The wait must not turn a 75-minute review into an expired delivery.
        load_edition(picks_file, target, int(time.time()), expected_sha256)
        # A pre-hour edition uses the same hourly key and content ledger as recovery.
        sent = deliver_report(client, parts, private, delivery_key, int(time.time()),
                              numbers={str(i): s["id"] for i, s in enumerate(stories, 1)},
                              content_keys={k for s in stories for k in story_content_keys(s)})
        if sent:
            record_decision(stories, target, int(time.time()), "sent", delivery_key)
        report = {"version": "btp-editorial-v9", "delivery": "sent" if sent else "already_sent", "messages": sent,
                  "stories": len(stories), "duplicates_excluded": excluded, "ai": "chatgpt_web_research",
                  "requested_stories": REPORT_PICKS,
                  "reviewed_edition_version": edition["version"],
                  "trigger": "user_requested" if user_requested else "hourly", "hour_utc": hourly_key(target)[7:],
                  "category_counts": {c: sum(s["category"] == c for s in stories) for c in CATEGORIES},
                  "research_queries": len(edition["coverage"]["queries"]),
                  "opened_sources": len(edition["coverage"]["opened_urls"]),
                  "picks": [{"title": s["lead"]["title"], "url": s["lead"]["link"],
                             "event_key": s["editorial"]["event_key"]} for s in stories]}
        atomic_json(STATE_FILE, {"updated_at": int(time.time()), "status": "ok", "errors": {}, "report": report})
        record_attempt(target, report["delivery"], len(stories), excluded, user_requested)
        print("BTP EDITORIAL REPORT", json.dumps({k: v for k, v in report.items() if k != "picks"}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, TelegramError) as error:
        # Do not erase a previously confirmed sent state on parse/transport failure.
        if isinstance(error, DeliveryUncertain) and "stories" in locals():
            record_decision(stories, target, int(time.time()), "uncertain", locals().get("delivery_key"))
        print("BTP EDITORIAL DELIVERY_UNCERTAIN:" if isinstance(error, DeliveryUncertain) else "BTP EDITORIAL FAILED:", str(error))
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="검토된 편집장 추천 1회 미리보기")
    parser.add_argument("--picks-file", type=Path, default=PICKS_FILE)
    parser.add_argument("--hour", required=True)
    parser.add_argument("--preview", action="store_true", required=True)
    args = parser.parse_args()
    raise SystemExit(main(prepared_hour=args.hour, picks_file=args.picks_file, preview=True))


