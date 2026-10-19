"""Deliver a single explicitly requested current-hour report."""
import argparse
import hashlib
import json
import time
from pathlib import Path

from report_timing import prepared_target, recovery_target, require_report_slot

REQUEST_FILE = Path("data/report-request.json")


def run(path=REQUEST_FILE, now=None, sender=None, picks_file=Path("data/editorial-picks.json"), scheduled_check=False):
    try:
        request = json.loads(Path(path).read_text(encoding="utf-8"))
        clock = time.time() if now is None else now
        if scheduled_check:
            # Recovery may consume an existing regular request only, never create one
            # or replay manual/old editions when no new reviewed material was submitted.
            try:
                if not isinstance(request, dict) or request.get("version") != 2:
                    raise ValueError("No regular request")
                require_report_slot(recovery_target(request["hour_utc"], clock))
            except (ValueError, KeyError, TypeError):
                print("BTP REQUEST CHECK: no current regular request")
                return 0
        if (not isinstance(request, dict) or type(request.get("version")) is not int or request["version"] not in (1, 2, 3)
                or not isinstance(request["hour_utc"], str)):
            raise ValueError("Invalid report request schema")
        expected = {"version", "hour_utc"} | ({"editorial_sha256"} if request["version"] in (2, 3) else set())
        if request["version"] == 3:
            expected.add("mode")
            if request.get("mode") != "user_requested":
                raise ValueError("An on-demand edition requires an explicit user request")
        if set(request) != expected:
            raise ValueError("Invalid report request fields")
        if request["version"] in (2, 3):
            target = (prepared_target if request["version"] == 2 else recovery_target)(request["hour_utc"], clock)
            require_report_slot(target, user_requested=request["version"] == 3)
            digest = request["editorial_sha256"]
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Invalid editorial content digest")
            if hashlib.sha256(Path(picks_file).read_bytes()).hexdigest() != digest:
                raise ValueError("The requested editorial file has changed")
        else:
            require_report_slot(recovery_target(request["hour_utc"], clock))
    except (ValueError, OSError, TypeError, KeyError):
        print("BTP REQUEST REJECTED: malformed request or target is outside the current hour")
        return 2
    if sender is None:
        from curated_report import main
        def sender(**kwargs):
            return main(picks_file=picks_file, **kwargs)
    print("BTP REQUEST ACCEPTED:", request["hour_utc"])
    if request["version"] == 2:
        return sender(prepared_hour=request["hour_utc"], expected_sha256=request["editorial_sha256"])
    if request["version"] == 3:
        return sender(recover_hour=request["hour_utc"], expected_sha256=request["editorial_sha256"], user_requested=True)
    return sender(recover_hour=request["hour_utc"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="검증된 현재 시간대 발송 요청만 처리")
    parser.add_argument("--request-file", type=Path, default=REQUEST_FILE)
    parser.add_argument("--picks-file", type=Path, default=Path("data/editorial-picks.json"))
    parser.add_argument("--scheduled-check", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(args.request_file, picks_file=args.picks_file, scheduled_check=args.scheduled_check))

