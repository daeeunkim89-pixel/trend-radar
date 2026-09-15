import os
import re
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# =========================================================
# TREND RADAR V2
# - 5분마다 실행
# - 매시간 사이트별 TOP 30 텔레그램 전송
# - 신규/급상승 감시
# - 수집 실패도 텔레그램 보고
# =========================================================

STATE_FILE = Path("data/state.json")
STATE_FILE.parent.mkdir(exist_ok=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-S948N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


# =========================================================
# 공통
# =========================================================

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def number(text):
    if not text:
        return None

    text = clean(text).replace(",", "")

    m = re.search(r"([\d.]+)\s*(만|천)?", text)

    if not m:
        return None

    try:
        value = float(m.group(1))
    except ValueError:
        return None

    if m.group(2) == "만":
        value *= 10000

    if m.group(2) == "천":
        value *= 1000

    return int(value)


def get(url):
    r = session.get(url, timeout=20)
    print("GET", r.status_code, url)

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")

    return BeautifulSoup(r.text, "lxml")


def send(text):
    if not TOKEN or not CHAT_ID:
        print("텔레그램 설정 없음")
        return

    # 텔레그램 메시지 길이 안전하게 분할
    chunks = []

    while len(text) > 3800:
        cut = text.rfind("\n", 0, 3800)

        if cut < 1000:
            cut = 3800

        chunks.append(text[:cut])
        text = text[cut:].lstrip()

    if text:
        chunks.append(text)

    for chunk in chunks:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": chunk,
                "disable_web_page_preview":
