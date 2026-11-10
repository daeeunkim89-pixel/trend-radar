"""Bind an explicitly approved edition to immutable Git commit bytes.

Only the push workflow may use version 4. Both approval and edition must be
changed together; the existing sender still verifies digest, hour, freshness,
editorial schema, full count and the shared deduplication ledger.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

REQUEST = "data/report-request.json"
PICKS = "data/editorial-picks.json"


def bind(request, picks_bytes, changed_paths):
    if not isinstance(request, dict) or type(request.get("version")) is not int:
        raise ValueError("Invalid request object")
    if request["version"] != 4:
        return request
    if set(request) != {"version", "hour_utc", "binding"} or request["binding"] != "trigger_commit":
        raise ValueError("Invalid commit-bound approval")
    if not {REQUEST, PICKS}.issubset(set(changed_paths)):
        raise ValueError("Commit-bound approval requires both files in the same commit")
    hour = request["hour_utc"]
    if not isinstance(hour, str) or not re.fullmatch(r"[0-9]{10}", hour):
        raise ValueError("Invalid approval hour")
    edition = json.loads(picks_bytes)
    if (not isinstance(edition, dict) or type(edition.get("version")) is not int
            or edition["version"] != 2 or edition.get("hour_utc") != hour
            or edition.get("reviewer") != "ChatGPT"
            or not isinstance(edition.get("picks"), list) or len(edition["picks"]) != 5):
        raise ValueError("Approval must bind a matching five-story ChatGPT edition")
    return {"version": 2, "hour_utc": hour,
            "editorial_sha256": hashlib.sha256(picks_bytes).hexdigest()}


def pin(commit, request_out, picks_out):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected an immutable Git commit SHA")
    def git(*args):
        return subprocess.check_output(["git", *args])
    request = json.loads(git("show", f"{commit}:{REQUEST}"))
    picks_bytes = git("show", f"{commit}:{PICKS}")
    changed = git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).decode().splitlines()
    result = bind(request, picks_bytes, changed)
    Path(picks_out).write_bytes(picks_bytes)
    Path(request_out).write_bytes((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
    print("BTP REQUEST PINNED: immutable commit", commit, "input_version", request["version"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--request-out", required=True)
    parser.add_argument("--picks-out", required=True)
    args = parser.parse_args()
    pin(args.commit, args.request_out, args.picks_out)
