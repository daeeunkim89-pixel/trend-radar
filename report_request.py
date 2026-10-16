"""Deliver a single explicitly requested current-hour report."""
import argparse
import json
import time
from pathlib import Path

from report_timing import recovery_target

REQUEST_FILE = Path("data/report-request.json")


def run(path=REQUEST_FILE, now=None, sender=None):
    try:
        request = json.loads(Path(path).read_text(encoding="utf-8"))
        if (not isinstance(request, dict) or set(request) != {"version", "hour_utc"}
                or type(request["version"]) is not int or request["version"] != 1
                or not isinstance(request["hour_utc"], str)):
            raise ValueError("Invalid report request schema")
        recovery_target(request["hour_utc"], time.time() if now is None else now)
    except (ValueError, OSError, TypeError):
        print("BTP REQUEST REJECTED: malformed request or target is outside the current hour")
        return 2
    if sender is None:
        from monitor import main
        sender = main
    print("BTP REQUEST ACCEPTED:", request["hour_utc"])
    return sender(recover_hour=request["hour_utc"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="검증된 현재 시간대 발송 요청만 처리")
    parser.add_argument("--request-file", type=Path, default=REQUEST_FILE)
    raise SystemExit(run(parser.parse_args().request_file))
