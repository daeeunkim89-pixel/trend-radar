# BTP 검토본·승인 발송 절차 — 2026-11-04
[매시간10개 운영 지침](btp-quick-check.md)과 [스포츠 중심·시사 대형 뉴스 기준](btp-news-policy-20261104.md)을 먼저 적용한다. 과거 3시간마다10개·여돌필수·미달 현황 송신 지시는 폐기한다.

## 정확한 검토본 schema — edition version 2

아래와 **같은 키**를 사용한다. URL·날짜·내용·시각은 실제 검토 결과로 바꾼다.

```json
{
  "version": 2,
  "hour_utc": "YYYYMMDDHH",
  "reviewer": "ChatGPT",
  "generated_at": 1792235100,
  "coverage": {
    "queries": ["actual football search", "actual major-news search", "actual current-affairs search", "actual major-sports search"],
    "opened_urls": ["https://example.org/actually-opened-source", "https://example.org/actually-inspected-frame.jpg"],
    "unavailable": []
  },
  "picks": [
    {
      "title": "Accurate proposed BTP headline, at most 90 characters",
      "category": "축구",
      "url": "https://example.org/actually-opened-source",
      "source": "Source name, at most 40 characters",
      "kind": "community",
      "event_key": "stable-person-event-original-date",
      "why": "Specific reason this fits BTP and is worth sharing; at most 180 characters",
      "angle": "Concrete frame and order for the editor to build; at most 150 characters",
      "why_now": "Source date, recent development or observed current spread; at most 180 characters",
      "verified_at": 1792235100,
      "published_at": null,
      "evidence": [{"url": "https://example.org/actually-opened-source", "note": "What was actually confirmed, at most 220 characters"}],
      "materials": [{"url": "https://example.org/actually-inspected-frame.jpg", "label": "확인한 장면", "kind": "image"}, {"url": "https://example.org/actually-opened-source", "label": "원문 자료", "kind": "source"}],
      "caution": "Any material unverified detail, at most 150 characters; empty when none",
      "readiness": {
        "mode": "scene",
        "event_date": "2026-10-17",
        "observation": "The specific defining action and consequence actually inspected; at most 240 characters",
        "checked_materials": ["https://example.org/actually-inspected-frame.jpg"],
        "outline": ["First card/cut using the checked material", "Next card/cut explaining the verified consequence"]
      }
    }
  ],
  "empty_reason": ""
}
```

- Root: version=2, reviewer=ChatGPT, 실제 generated_at(epoch 정수), hour_utc, coverage, picks, empty_reason. UTF-8 JSON+마지막 줄바꿈이며 최대 100,000바이트. 새 검토본은 v2만 사용한다. legacy v1은 과거 고정 요청을 위한 호환이다.
- Category: `시사` / `축구` / `메이저 스포츠` (과거 아이돌 category는 새 v2 검토본에서 금지). kind: `community` / `social` / `official` / `article`.
- coverage.queries: 실제 검색 4~120개, 각 250자 이하. opened_urls: 실제 본문/자료를 연 공개 HTTPS URL 최대 240개. unavailable: 실패 설명 최대 60개, 각 180자 이하. 실패 URL은 opened에 넣지 않는다.
- picks는 순위별 0~20개를 사용한다. 실제 메시지는 7일 sent/uncertain 중복 제외 후 상위 최대 10개다. 10개 미달이면 발송 완료로 삼지 않고 추가 조사한다. empty_reason은 160자 이하이며, 부족한 검토본에는 구체적인 부족 이유를 쓴다.
- 각 pick: title≤90, source≤40, event_key≤160, why≤180, angle≤150, why_now≤180, caution≤150자. caution만 빈 문자열을 허용한다. 왜·첫 장은 간결한 한 문장씩 쓴다. Markdown/Telegram HTML을 JSON 본문에 넣지 않는다.
- event_key는 소문자 안정적인 사건 식별자다. 같은 사건은 기존 키를 재사용한다. 다른 제목·매체·새 수집 시각은 새 사건이 아니다. 진짜 새 후속은 why_now에 새 사실을 명시한다.
- verified_at은 실제 원문/자료를 확인한 epoch 정수다. generated_at과 verified_at은 발송 때까지 **75분** 이내여야 한다. 값을 갱신해 검토한 척하지 않는다. published_at은 검증된 원문 게시 epoch 또는 null이며 사건일 추정값이 아니다.
- evidence: 1~3개, 정확히 url/note 키, note≤220자. materials: 0~3개, 정확히 url/label/kind, label≤25자. material kind는 image/video/source이며 **실제로 본 영상만 video**다. 모든 선택·근거·자료 URL은 coverage.opened_urls에도 있어야 한다.
- readiness: 정확히 mode/event_date/observation/checked_materials/outline. mode=scene|major_news, event_date는 출처로 확인한 실제 사건·새 발표의 YYYY-MM-DD이며 미래 날짜 금지. observation≤240자. checked_materials는 실제 본 image/video URL 최대 3개이며 그 pick의 materials와 opened에도 있어야 한다. scene은 1개 이상 필수다. outline은 확인된 사실과 장면만으로 구체적인 카드/컷 2~4개, 각 120자 이하다.
- `/info` 상세 하나도 Telegram 1메시지(3,900 UTF-16 단위) 안에 들어가야 한다. 본문을 무작정 길게 쓰지 않는다. 제목·선정 이유·첫 장은 메인 메시지에, 검증 근거·주의·제작 순서는 /info에 둔다.


## 제출·발송
1. 현재 실제 한국시각과 UTC hour를 확인한다. 정기는08·11·14·17·20시 매시간이다. 정기 실행은 현재 회차를 조사·제출하며 미래 정각까지 기다리지 않는다.
2. 최신 main의 공개 state/request/status/editorial-history에서 대상 회차와7일 sent/uncertain 식별자를 도구 안에서 간추린다. 비밀값·암호화 state는 읽지 않는다. 같은 회차 요청·sent/uncertain·부분 전송이면 새 해시로 재요청하지 않는다.
3. 실제 원문을 확인한 version2 picks를 표준 라이브러리 전용 `python edition_preflight.py <picks파일>`로 검사한다. 이 파일은 토큰·네트워크·production 모듈 import 없이 kind/category/길이 등 작성 오류를 잡는다. major_news는 readiness.mode에만 쓰고 pick.kind는 실제 출처대로 article/official/community/social을 쓴다. 사전 검사 오류는 제출 전에 고친다. 이는 실제 원문 검증이나 서버의 전체 스키마·신선도·비공개 중복 검사를 대신하지 않는다. 이어서 최종 중복 제거 후10개를 확보할 검증 예비를 준비한다. 검토 시간을 새 검증 없이 갱신하지 않는다.
4. 정기 요청은 {"version":4,"hour_utc":"YYYYMMDDHH","binding":"trigger_commit"} 한 줄과 마지막 줄바꿈이다. picks 스키마는 version2를 유지한다. GitHub pin_report_request.py가 두 파일이 함께 변경된 불변 승인 커밋의 picks 바이트에서 SHA256을 계산해 기존 version2 요청으로 변환한다. 에이전트는 해시를 추정하거나 수기로 작성하지 않는다. 회차 일치·ChatGPT 검토·10개를 먼저 확인하며, 기존 발송기의 시간·신선도·검토 스키마·비공개 중복·10개 강제 검사는 유지한다. 기존 version2/3 요청의 틀린 해시는 자동 보정하지 않는다.
5. 두 파일 data/editorial-picks.json과 data/report-request.json만 최신 main tree 기반 한 커밋으로 원자 반영한다. create_tree→단일 parent create_commit→expected_sha와 force=false update_ref를 쓴다. 충돌이면 최신 공개 잠금·요청·ref를 다시 읽는다.
6. 기존 승인 delivery-request workflow의 실제 결과를 짧게 확인한다. BTP_REQUIRE_COMPLETE=1이며 최소10개가 아니면 추가 조사로 돌아간다. 실제 stories=5/messages=1/target_met=true를 완료로 본다. 모의 테스트/형식 검사/수집 성공은 발송 성공이 아니다.
7. 재시도 가능한 실패와 불확실 전송을 구분한다. sent/uncertain 잠금과 이력을 지우지 않는다. 연결 테스트·Telegram 직접 호출·자동 Instagram 게재·과거 몰아 보내기는 금지한다. 추가 운영 보고를 Telegram에 보내지 않는다.
8. 사용자가 별도 즉시 보충을 명시한 경우만 기존 version3 mode=user_requested, 현재 UTC hour, 동일 해시를 사용한다. 기존 정기 잠금·7일 중복 보호는 유지한다.

## 2026-11-12 우선 규칙
정규 발송은 KST08/11/14/17/20시,10개·한메시지다. [최신 정책](btp-news-policy-20261104.md)의 국내 독자 기준·출처 다양성·주간6시간/08시12시간 신선도·조사10/32최대를 적용한다. v2 published_at은 실제 최초 공개시각이 필수다. 24/48시간 확장은 폐기한다. 예약이 정시5분 전 시작되면 scheduled_for 회차를 원자 제출하고 GitHub만 최대5분 기다린다. AI는 정시 대기하지 않는다.
