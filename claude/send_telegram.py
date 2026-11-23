"""Send new BTP editions from claude/outbox to Telegram.

Editions are written by the scheduled Claude task as
claude/outbox/<YYYYMMDD-HH>.json (preferred) or .md (plain text, legacy).
JSON editions are rendered in the compact card style the earlier btp
reports used (HTML, one message). A file is sent once: a marker
claude/sent/<name> is written before sending and committed by the workflow,
so re-runs never resend. Only the Python standard library is used.

JSON shape:
{
  "slot": "11/23 17:00",
  "items": [
    {"category": "해외축구", "title": "...", "url": "https://...",
     "why": "한 줄 포인트", "check": "본문 확인" | "제목만 확인 ..."}
  ],
  "note": "못 본 곳 등 한 줄 (선택)"
}
"""
import html
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
CONFIRMED = {"", "본문 확인", "기사 본문 확인", "확인"}


def short(value: str, maximum: int) -> str:
    value = " ".join(str(value or "").split())
    return value if len(value) <= maximum else value[: maximum - 1].rstrip() + "…"


def render(edition: dict) -> str:
    items = edition["items"]
    esc = html.escape
    # Shrink text until the whole edition fits one message.
    for title_n, why_n, check_n in ((70, 70, 40), (58, 52, 30), (46, 38, 22)):
        lines = [f"<b>⚡ btp · 추천 {len(items)}/10 · {esc(edition['slot'])}</b>"]
        for i, it in enumerate(items, 1):
            label = "🔥 01" if i == 1 else f"{i:02d}"
            title = esc(short(it["title"], title_n))
            if it.get("url"):
                title = f'<a href="{esc(it["url"], quote=True)}">{title}</a>'
            lines += ["", f"<b>{label} · {esc(it.get('category', ''))}</b>", title]
            if it.get("why"):
                lines.append(esc(short(it["why"], why_n)))
            check = str(it.get("check", "")).strip()
            if check not in CONFIRMED:
                lines.append("확인: " + esc(short(check, check_n)))
        if edition.get("note"):
            lines += ["", "<i>" + esc(short(edition["note"], 120)) + "</i>"]
        text = "\n".join(lines)
        if len(text) <= LIMIT:
            return text
    return text  # still too long: sent in parts by chunks()


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


def send(token: str, chat_id: str, text: str, as_html: bool) -> None:
    fields = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    if as_html:
        fields["parse_mode"] = "HTML"
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urllib.parse.urlencode(fields).encode(),
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
        p for p in list(OUTBOX.glob("*.json")) + list(OUTBOX.glob("*.md"))
        if not (SENT / p.name).exists()
    )
    if not pending:
        print("Nothing new to send.")
        return 0
    for path in pending:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            print(f"Skip empty {path.name}")
            continue
        as_html = path.suffix == ".json"
        text = render(json.loads(raw)) if as_html else raw
        # Marker first: a half-failed send is better than a duplicate.
        (SENT / path.name).write_text("sent\n", encoding="utf-8")
        for part in chunks(text):
            send(token, chat_id, part, as_html)
        print(f"Sent {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
