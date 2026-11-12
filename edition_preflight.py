"""Read-only, standard-library checks before submitting an approved edition.

This deliberately does not approve stories or replace the sender's full schema,
freshness, message-size and private deduplication checks. No network or tokens.
"""
import argparse
import json
import re
from pathlib import Path

REPORT_PICKS = 10
REPORT_HOURS_KST = (8, 11, 14, 17, 20)

CATEGORIES = ("시사", "축구", "메이저 스포츠", "아이돌")
SOURCE_KINDS = ("community", "social", "official", "article")


def validate_source_fields(pick, version, position=None):
    prefix = f"picks[{position}]" if position is not None else "pick"
    if not isinstance(pick, dict):
        raise ValueError(f"{prefix}: expected an object")
    if pick.get("category") not in CATEGORIES:
        raise ValueError(f"{prefix}.category: expected 시사, 축구 or 메이저 스포츠")
    if version == 2 and pick["category"] == "아이돌":
        raise ValueError("Entertainment is only eligible as major public-interest news, category 시사")
    if pick.get("kind") not in SOURCE_KINDS:
        raise ValueError(f"{prefix}.kind: expected article/official/community/social; major_news belongs in readiness.mode")


def preflight(edition):
    if (not isinstance(edition, dict) or type(edition.get("version")) is not int
            or edition["version"] != 2 or edition.get("reviewer") != "ChatGPT"):
        raise ValueError("Expected a version2 ChatGPT edition")
    if not isinstance(edition.get("hour_utc"), str) or not re.fullmatch(r"[0-9]{10}",edition["hour_utc"]):
        raise ValueError("hour_utc: expected UTC YYYYMMDDHH")
    picks=edition.get("picks")
    if not isinstance(picks,list) or len(picks) != REPORT_PICKS:
        raise ValueError(f"Expected exactly {REPORT_PICKS} reviewed picks")
    for i,pick in enumerate(picks):
        validate_source_fields(pick,2,i)
        for name,limit in (("title",90),("source",40),("event_key",160),("why",180),
                           ("angle",150),("why_now",180),("caution",150)):
            value=pick.get(name)
            if not isinstance(value,str) or len(value)>limit or (name!="caution" and not value.strip()):
                raise ValueError(f"picks[{i}].{name}: expected text within {limit} characters")
        if not isinstance(pick.get("readiness"),dict) or pick["readiness"].get("mode") not in ("scene","major_news"):
            raise ValueError(f"picks[{i}].readiness.mode: expected scene or major_news")
    return len(picks)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description="Non-sending editorial field preflight; no dependencies or Telegram access")
    parser.add_argument("picks_file",type=Path)
    args=parser.parse_args()
    try:
        count=preflight(json.loads(args.picks_file.read_text(encoding="utf-8")))
    except (ValueError,OSError) as error:
        parser.exit(2,f"BTP PREFLIGHT REJECTED: {error}\n")
    print(f"BTP PREFLIGHT OK: {count} picks; full sender validation still required")
