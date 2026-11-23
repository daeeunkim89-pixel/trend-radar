"""Send new BTP editions from claude/outbox to Telegram.

Each edition is a plain-text file claude/outbox/<YYYYMMDD-HH>.md written by the
scheduled Claude task. A file is sent once: after a successful send, a marker
claude/sent/<name> is written and committed by the workflow. Files that already
have a marker are skipped, so re-runs and repeated pushes never resend.
Only the Python standard library is used.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTBOX = ROOT / "outbox"
SENT = ROOT / "sent"
LIMIT = 3900  # Telegram hard limit is 4096 characters per message.


def chunks(text: str):
    """Split on blank lines so items are not cut mid-way."""
    parts, current = [], ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= LIMIT:
            current = candidate
            continue
        if current:
            parts.append(current)
        while len(block) > LIMIT:
            parts.append(block[:LIMIT])
            block = block[LIMIT:]
        current = block
    if current:
        parts.append(current)
    return parts


def send(token: str, chat_id: str, text: str) -> None:
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if not body.get("ok"):
        raise RuntimeError(f"Telegram error: {body.get('description')}")


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1
    SENT.mkdir(exist_ok=True)
    pending = sorted(
        p for p in OUTBOX.glob("*.md") if not (SENT / p.name).exists()
    )
    if not pending:
        print("Nothing new to send.")
        return 0
    for path in pending:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            print(f"Skip empty {path.name}")
            continue
        # Write the marker before sending: if a send fails midway we would
        # rather miss one message than risk a duplicate on the next run.
        (SENT / path.name).write_text("sent\n", encoding="utf-8")
        for part in chunks(text):
            send(token, chat_id, part)
        print(f"Sent {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
