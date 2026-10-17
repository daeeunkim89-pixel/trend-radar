"""Telegram transport, delayed group commands and encrypted editorial state."""
import base64
import copy
import hashlib
import html
import json
import os
import re
import time
from pathlib import Path

import requests
from cryptography.fernet import Fernet, InvalidToken

from editorial import STATUS_NAMES, item_id, link, message_units, pack_cards, render_info, title_key
from communities import material_urls

PRIVATE_FILE = Path("data/editor.enc")
CONTENT_RETENTION = 7 * 86400


class TelegramError(RuntimeError):
    pass


class DeliveryUncertain(TelegramError):
    pass


class PrivateState:
    def __init__(self, token, chat_id, path=None):
        self.path = Path(path or PRIVATE_FILE)
        material = b"trend-radar/editor/v1\0" + token.encode() + b"\0" + str(chat_id).encode()
        self.cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256(material).digest()))
        self.data = {"version": 1, "offset": None, "statuses": {}, "reports": {}}
        if self.path.exists():
            try:
                self.data = json.loads(self.cipher.decrypt(self.path.read_bytes()))
                if self.data.get("version") != 1 or not isinstance(self.data.get("statuses"), dict):
                    raise ValueError("schema")
            except (InvalidToken, ValueError, TypeError) as exc:
                raise TelegramError("선정 기록 복호화 실패: 봇 토큰·대상 변경 또는 파일 손상 확인 필요") from None
        self.original = copy.deepcopy(self.data)

    def save(self):
        if self.path.exists() and self.data == self.original:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(self.cipher.encrypt(json.dumps(self.data, ensure_ascii=False).encode()))
        temporary.replace(self.path)
        self.original = copy.deepcopy(self.data)


class TelegramClient:
    def __init__(self, token, chat_id, expected_hash=None, session=None):
        if not token or not chat_id:
            raise TelegramError("텔레그램 연결 설정이 없습니다")
        self.token, self.chat_id = token, str(chat_id)
        expected_hash = expected_hash or os.environ.get("EXPECTED_TELEGRAM_CHAT_SHA256")
        if expected_hash and hashlib.sha256(self.chat_id.encode()).hexdigest() != expected_hash:
            raise TelegramError("설정된 전송 대상이 승인된 Btp 방과 다릅니다")
        self.session = session or requests.Session()
        self.username = ""
        self.last_sent = None

    def call(self, method, payload=None):
        for attempt in range(3):
            try:
                response = self.session.post(f"https://api.telegram.org/bot{self.token}/{method}",
                                             json=payload or {}, timeout=(5, 20))
                body = response.json()
            except requests.RequestException:
                # requests exceptions include URLs containing the bot token; do not log them.
                if method == "sendMessage":
                    raise DeliveryUncertain("텔레그램 전송 결과 확인 불가: 자동 재전송 중지") from None
                raise TelegramError(f"텔레그램 {method} 연결 실패") from None
            except (ValueError, TypeError):
                if method == "sendMessage":
                    raise DeliveryUncertain("텔레그램 전송 결과 응답 확인 불가: 자동 재전송 중지") from None
                raise TelegramError(f"텔레그램 {method} 응답 형식 오류") from None
            if isinstance(body, dict) and response.status_code == 200 and body.get("ok") is True:
                return body.get("result")
            code = body.get("error_code", response.status_code) if isinstance(body, dict) else response.status_code
            retry = body.get("parameters", {}).get("retry_after", 0) if isinstance(body, dict) else 0
            if code == 429 and isinstance(retry, (int, float)) and 0 < retry <= 30 and attempt < 2:
                time.sleep(retry + 0.2)
                continue
            raise TelegramError(f"텔레그램 {method} 실패 (코드 {code})")
        raise TelegramError("텔레그램 재시도 제한")

    def verify(self):
        me = self.call("getMe")
        chat = self.call("getChat", {"chat_id": self.chat_id})
        if not me.get("is_bot") or str(chat.get("id")) != self.chat_id or chat.get("type") not in {"group", "supergroup"}:
            raise TelegramError("텔레그램 봇·그룹 확인 실패")
        self.username = me.get("username", "")
        print("TELEGRAM_GROUP_VERIFIED=OK")

    def send(self, text):
        if message_units(text) > 4096:
            raise TelegramError("텔레그램 메시지 길이 제한 초과")
        if self.last_sent is not None:
            wait = 3.1 - (time.monotonic() - self.last_sent)
            if wait > 0:
                time.sleep(wait)
        result = self.call("sendMessage", {"chat_id": self.chat_id, "text": text,
                                          "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}})
        if str(result.get("chat", {}).get("id")) != self.chat_id or not result.get("message_id"):
            raise DeliveryUncertain("텔레그램 반환 전송 대상·메시지 확인 실패")
        self.last_sent = time.monotonic()
        print("TELEGRAM_SEND=OK")
        return result["message_id"]


def catalog(history):
    stories = {}
    for key, row in history["items"].items():
        story_id = row.get("story_id", key)
        previous = stories.get(story_id)
        if not previous or row["last_seen_at"] > previous["last_seen_at"]:
            stories[story_id] = row
    return stories


def story_content_keys(story):
    keys = {"item:" + story["id"]}
    for row in story["members"]:
        keys.add("item:" + item_id(row["link"]))
        headline = title_key(row["title"])
        if len(headline) >= 10:
            keys.add("title:" + hashlib.sha256(headline.encode()).hexdigest())
    for detail in [story.get("detail", {})] + [row.get("detail", {}) for row in story["members"]]:
        for url in material_urls(detail):
            keys.add("asset:" + hashlib.sha256(url.encode()).hexdigest())
        for original in detail.get("fmkorea_links", []):
            keys.add("item:" + item_id(original["url"]))
    return keys


def unreported_stories(stories, history, private, now=None):
    """Migrate prior delivery ledgers, then exclude content already sent/uncertain."""
    now = int(now or time.time())
    cutoff = now - CONTENT_RETENTION
    seen = {key: at for key, at in private.data.get("content_history", {}).items() if at >= cutoff}
    by_story = {}
    for key, row in history["items"].items():
        story_id = row.get("story_id", key)
        by_story.setdefault(story_id, set()).update(story_content_keys({"id": story_id, "members": [row]}))
    for report in private.data["reports"].values():
        at = report["started_at"]
        if at < cutoff or not (report.get("done") or report.get("message_ids") or report.get("uncertain")):
            continue
        keys = set(report.get("content_keys", []))
        for story_id in report.get("numbers", {}).values():
            keys.add("item:" + story_id)
            keys.update(by_story.get(story_id, set()))
        for key in keys:
            seen[key] = max(seen.get(key, 0), at)
    private.data["content_history"] = seen
    private.save()
    return [story for story in stories if not story_content_keys(story).intersection(seen)]


def remember_report_content(private, report, now):
    seen = private.data.setdefault("content_history", {})
    for key in report.get("content_keys", []):
        seen[key] = max(seen.get(key, 0), now)


def help_text(username):
    suffix = "@" + username if username else ""
    return ("<b>btp 소재 선정</b>\n"
            f"<code>/info{suffix} 번호</code> 상세·자료 링크\n"
            f"<code>/pick{suffix} 번호</code> 선정\n"
            f"<code>/hold{suffix} 소재ID</code> 보류\n"
            f"<code>/doing{suffix} 소재ID</code> 제작 중\n"
            f"<code>/done{suffix} 소재ID</code> 업로드 완료\n"
            f"<code>/clear{suffix} 소재ID</code> 상태 초기화\n"
            f"<code>/queue{suffix}</code> 선정·보류·제작 목록\n"
            "최신 소재함 번호 또는 12자리 ID를 사용하세요. 이전 소재함은 해당 메시지에 답장해 번호를 입력하세요. 명령은 약 10분 간격 점검 때 반영됩니다(지연 가능).")


def process_commands(client, private, history, now=None):
    now = int(now or time.time())
    state = private.data
    payload = {"timeout": 0, "limit": 10, "allowed_updates": ["message"]}
    if state["offset"] is None:
        updates = client.call("getUpdates", {**payload, "offset": -1, "limit": 1})
        # First deployment starts after the existing backlog; no earlier conversation is acted on.
        state["offset"] = max((x["update_id"] + 1 for x in updates), default=0)
        private.save()
        print("TELEGRAM_COMMANDS_INITIALIZED=OK")
        return 0
    updates = client.call("getUpdates", {**payload, "offset": state["offset"]})
    stories = catalog(history)
    for key, value in state["statuses"].items():
        if value.get("item"):
            stories.setdefault(key, value["item"])
    handled = 0
    for update in updates:
        update_id = update["update_id"]
        if update_id < state["offset"]:
            continue
        message = update.get("message", {})
        match = re.fullmatch(r"/(info|pick|hold|doing|done|clear|queue|help)(?:@([A-Za-z0-9_]+))?(?:\s+(\S+))?\s*", message.get("text", ""))
        accepted = (str(message.get("chat", {}).get("id")) == client.chat_id
                    and not message.get("from", {}).get("is_bot")
                    and now - 86400 <= message.get("date", 0) <= now + 300
                    and match and (not match[2] or match[2].lower() == client.username.lower()))
        if accepted:
            command, key = match[1], (match[3] or "").lower()
            if key.isdecimal() and len(key) <= 2:
                reply_id = message.get("reply_to_message", {}).get("message_id")
                reports = [r for r in state["reports"].values() if r.get("done") and r.get("numbers")]
                if reply_id:
                    reports = [r for r in reports if reply_id in r.get("message_ids", [])]
                reports.sort(key=lambda r: r["started_at"], reverse=True)
                key = reports[0]["numbers"].get(str(int(key)), "") if reports else ""
            if command == "help":
                replies = [help_text(client.username)]
            elif command == "queue":
                active = [(k, v) for k, v in state["statuses"].items() if v["status"] in {"pick", "hold", "doing"} and k in stories]
                active.sort(key=lambda kv: kv[1]["updated_at"], reverse=True)
                entries = [f"{STATUS_NAMES[value['status']]} · {link(stories[k]['title'], stories[k]['link'])}\n<code>{k}</code>" for k, value in active[:30]]
                replies = ["<b>btp 선정 목록</b>\n" + f"진행·보류 {len(active)}개 (최근 30개 표시)"] + pack_cards(entries) if entries else ["현재 선정·보류·제작 중인 소재가 없습니다."]
            elif key not in stories:
                replies = ["최신 소재함 번호 또는 12자리 ID를 확인해 주세요. 사용법은 /help로 볼 수 있습니다."]
            elif command == "info":
                replies = [render_info(stories[key], key, state["statuses"].get(key, {}).get("status"))]
            else:
                item = {k: stories[key][k] for k in ("title", "link", "last_seen_at")}
                state["statuses"][key] = {"status": command, "updated_at": now, "item": item}
                replies = [f"<b>{STATUS_NAMES[command]}</b> · {link(stories[key]['title'], stories[key]['link'])}\n<code>{key}</code>"]
            # Persist state and cursor before acknowledgements; retries cannot apply commands twice.
            state["offset"] = update_id + 1
            private.save()
            for reply in replies:
                client.send(reply)
            handled += 1
        else:
            state["offset"] = update_id + 1
    # No raw messages, actor names, Telegram ids or tokens are persisted.
    private.save()
    print("TELEGRAM_COMMANDS_HANDLED", handled)
    return handled


def deliver_report(client, parts, private, report_key, now=None, numbers=None, content_keys=None):
    now = int(now or time.time())
    if len(parts) != 1:
        raise TelegramError("자동 소재함은 시간당 메시지 1개만 보낼 수 있습니다")
    reports = private.data["reports"]
    report = reports.get(report_key)
    if report and report.get("done"):
        print("TELEGRAM_REPORT_ALREADY_SENT=SKIP")
        return 0
    if report and report.get("message_ids"):
        report["done"] = True
        report["suppressed_remainder"] = True
        report.pop("parts", None)
        private.save()
        print("TELEGRAM_LEGACY_REPORT_REMAINDER=SKIP")
        return 0
    if report and report.get("uncertain"):
        raise DeliveryUncertain("이 보고서의 이전 전송 결과 확인이 필요합니다")
    if not report:
        report = {"parts": parts, "next": 0, "started_at": now, "message_ids": [],
                  "done": False, "numbers": numbers or {}, "content_keys": sorted(set(content_keys or []))}
        reports[report_key] = report
        private.save()
    sent = 0
    for index in range(report["next"], len(report["parts"])):
        try:
            message_id = client.send(report["parts"][index])
        except DeliveryUncertain:
            report["uncertain"] = True
            remember_report_content(private, report, now)
            private.save()
            raise
        report["message_ids"].append(message_id)
        report["next"] = index + 1
        remember_report_content(private, report, now)
        private.save()
        sent += 1
    report["done"] = True
    del report["parts"]
    # Completed report bodies are removed; only a small encrypted delivery ledger remains.
    private.data["reports"] = dict(sorted(reports.items(), key=lambda kv: kv[1]["started_at"], reverse=True)[:72])
    private.save()
    print("TELEGRAM_REPORT_COMPLETE", sent)
    return sent

