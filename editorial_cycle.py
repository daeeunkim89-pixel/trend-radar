"""Read-only guide for hourly research and the six approved BTP reports."""
import json
import time
from datetime import datetime
from pathlib import Path

from report_timing import KST, REPORT_HOURS_KST, hourly_key

DISCOVERY_STALE_SECONDS = 20 * 60


def plan_cycle(now, state=None, request=None, status=None, history=None, candidates=None):
    """Keep researching after a completed report without unlocking its delivery."""
    state, request, status = state or {}, request or {}, status or {}
    history, candidates = history or {}, candidates or {}
    local = datetime.fromtimestamp(now, KST)
    generated = candidates.get("generated_at")
    age = now - generated if type(generated) is int and generated <= now else None
    result = {"at": now, "local_at": local.isoformat(), "phase": "off_hours",
              "target_hour_utc": None, "target_epoch": None, "may_submit": False,
              "locked_reports": [], "discovery_generated_at": generated,
              "discovery_age_seconds": age,
              "discovery_refresh_needed": age is None or age > DISCOVERY_STALE_SECONDS
                  or candidates.get("status") == "unavailable"}
    if not 7 <= local.hour <= 23:
        return result
    locks = {}
    for edition in history.get("editions", []):
        if edition.get("delivery") in {"sent", "already_sent", "uncertain"}:
            locks[edition.get("hour_utc")] = edition["delivery"]
    report = state.get("report", {})
    updated = state.get("updated_at", 0)
    for report_hour in REPORT_HOURS_KST:
        target = int(local.replace(hour=report_hour, minute=0, second=0, microsecond=0).timestamp())
        hour = hourly_key(target)[7:]
        if report.get("hour_utc") == hour and target <= updated < target + 3600:
            if report.get("delivery") in {"sent", "already_sent", "uncertain"}:
                locks[hour] = (report["delivery"] if report.get("messages") == 1 else "partial_or_uncertain")
    if status.get("status") == "delivery_uncertain":
        locks[status.get("hour_utc")] = "uncertain"
    if request.get("hour_utc") not in locks:
        locks[request.get("hour_utc")] = "request_exists_do_not_reissue"
    current_hour = int(now) // 3600 * 3600
    available = []
    for report_hour in REPORT_HOURS_KST:
        target = int(local.replace(hour=report_hour, minute=0, second=0, microsecond=0).timestamp())
        if target < current_hour:
            continue
        hour = hourly_key(target)[7:]
        if hour in locks:
            result["locked_reports"].append({"hour_utc": hour, "reason": locks[hour]})
        else:
            available.append(target)
    if not available:
        result["phase"] = "await_delivery" if any(
            x["reason"] == "request_exists_do_not_reissue" for x in result["locked_reports"]
        ) else "day_complete"
        return result
    target = available[0]
    phase = "report" if target == current_hour else "prepare" if target - now <= 3600 else "research"
    result.update(phase=phase, target_hour_utc=hourly_key(target)[7:], target_epoch=target,
                  may_submit=phase in {"prepare", "report"})
    return result


def read_public(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main():
    result = plan_cycle(int(time.time()),
        state=read_public("data/state.json"), request=read_public("data/report-request.json"),
        status=read_public("data/editorial-status.json"),
        history=read_public("data/editorial-history.json"), candidates=read_public("data/candidates.json"))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
