# BTP 편집·발송 운영 — 2026-10-19

## 목표와 보고 시간

@bythepulse에서 바로 제작할 새로운 소재 **10개**를 기존 승인된 Btp Telegram 그룹에 **메시지 1개**로 전달한다. 한국시간 **08·11·14·17·20·23시**, 각 회차 20분 전부터 준비한다. 08시부터 00시까지 3시간 간격이면 마지막 회차는 23시다. 00시는 별도 회차가 아니다. 정기 야간 발송, 지난 회차 몰아 보내기, 추가 테스트 메시지, Instagram 자동 게재를 하지 않는다.

이 문서를 먼저 읽고 `docs/btp-profile.md`의 확인된 최근 표지 12개와 사용자 반려 사례를 기준으로 판단한다. 100만 조회수는 대중성과 공유 이유를 엄격히 보는 편집 목표다. 조회수 예측·보장이나 Instagram Insights 분석을 했다는 뜻이 아니다. 수집량·JSON 통과·발송 성공은 실제 제작 채택 성과와 구별한다.

분야: 국내·해외축구, 누구나 관심 가질 큰 시사, **여자아이돌**의 구체적인 바이럴 장면, 메이저 스포츠. 남자아이돌 팬덤 소식은 제외한다. 축구와 여자아이돌부터 찾고 일반 기사로 빈칸을 쉽게 채우지 않는다. Python은 검토본 검증·중복 제거·송신을 맡으며 이름·키워드 점수로 선정하지 않는다.

## BTP에 맞는지 먼저 판단

후보의 제목을 꾸미기 전에 다음을 확인한다.

1. 첫 장에 실제로 보일 증거는 무엇인가: 동작, 전후 화면, 당사자의 실제 대화, 공식 발표의 큰 영향 중 하나를 특정한다.
2. 누가 누구에게 왜 보낼까: 한국 축구 팬의 자부심·라이벌 구도·큰 경기의 긴장, 일상 서비스의 손해, 돈과 공정성, 유명인의 의외의 선택처럼 구체적인 이해관계가 필요하다. '뜻밖이다/공유할 만하다'만 쓰지 않는다.
3. 다음 장에서 무엇이 달라지나: 첫 장의 질문을 확인한 행동·반응·결과로 회수한다. 본 적 없는 반응을 추가하라고 쓰지 않는다.
4. 지금 새로 알릴 사실은 무엇인가: 원래 발생일, 원문 게시일, 새 공개·확정 사실을 구별한다. 재수집·파일명·검색 갱신 시각은 사건 날짜가 아니다.
5. 이미 보냈거나 BTP에 게재된 같은 사건인가: 제목·도메인이 달라도 사건은 같다. 새 후속은 편집 가치가 바뀌는 새 사실이 있을 때만 별도로 다룬다.

사용자가 반려한 커 감독 닮은꼴, 중국 유소년 감독 항의 재연, 야말·베르날 충돌, 프랑스 시위 피해 집계 갱신을 재선정하지 않는다. 유명인·큰 리그만으로 통과시키지 않는다. '감독이 화났다'는 공통점만으로 최근 이정효 표지와 같은 가치라고 판단하지 않는다. 국내 관련성·구체적인 이유·결과·장면을 함께 본다.

단순 외모·티저·평범한 팬서비스·팬 감상·인기 순위·작은 기록·알려지지 않은 해외 대학리그·낯선 지역정치·단순 참사·확인 안 된 소문은 빈칸용으로 쓰지 않는다. 스코어만 있는 경기 결과는 제외한다. 큰 구단·한국 선수의 중요한 경쟁 구도 변화와 확인한 핵심 장면이 있으면 평가할 수 있다. 일상적인 연승 숫자 증가만을 새 사건으로 만들지 않는다.

사용자 긍정 예시인 레드벨벳 자막 피드백(https://m.fmkorea.com/best/10454601662)은 실제로 읽히는 요청과 전후 대비가 핵심이다. 그 사례 자체를 새 추천으로 보내거나 한 글이 후속 수정을 일으켰다고 추정하지 않는다.

## 실제 조사와 작업량

- 실제 현재 한국시각·UTC YYYYMMDDHH·정각 epoch를 도구로 구한다. :40 이후 **다음 정각이 보고 시간일 때만** 다음 시간을 대상으로 한다. 그 외에는 실제 현재 시간이 보고 시간일 때만 처리한다. 예: 07:40→08시, 지연된 08:45→현재 08시, 09시→발송 안 함. 조사 후와 쓰기 직전에 다시 확인한다.
- main의 state/request/picks/editorial-history/candidates를 읽는다. 도구 안에서 파싱하여 필요한 발송 event_key·신선한 유망 후보·실패 출처만 출력한다. 전문을 반복 출력하지 않는다. 최초 새 파일 404는 정상이다.
- `data/editorial-history.json`의 **sent/uncertain** 사건과 event_key를 먼저 제외한다. 수집된 적만 있는 미발송 후보는 제외하지 않는다. BTP 공개 표지의 확인 가능한 기존 게재도 대조하되, 실제 게시와 추천이 게재의 원인이 됐다는 판단을 구별한다.
- 네 분야를 6~12개 집중 검색으로 조사한다. 더쿠·펨코 공개 간접 색인/인용·인스티즈·개드립·루리웹·엠팍과 원본 SNS/영상·구단/대회/아티스트 공식 자료·신뢰할 만한 보도를 함께 사용한다. 해외축구·메이저 스포츠는 영문도 쓴다. 40후보/12도메인 같은 건수 목표는 없다.
- 후보 스냅샷은 발견용이다. 원문 본문·실제 사진·핵심 동작과 결과를 포괄하는 연속 프레임을 열어 확인한다. 검색 요약, 플레이어, 썸네일, 인터뷰의 묘사는 영상 시청이 아니다. Naver 공개 영상 후보의 `video_viewed=false`를 유지한 채 발견 링크로 사용하고 실제 검토 후에만 추천한다. 업로드 날짜를 원래 경기·사건 날짜로 바꾸지 않는다.
- 보호 확인이 끝나지 않는 펨코 직접 경로를 반복하지 않는다. 접근 가능한 인용본·독립 원본으로 확인하고, 읽지 않은 펨코 본문을 봤다고 쓰지 않는다. 실패는 coverage.unavailable에 남긴다. 공개·독립 자료를 사용하며 차단·인증·지역 제한을 우회하지 않는다.
- 프로필 표지는 하루 첫 회차에 접근 가능한 범위를 새로 확인하고 이후 검토 메모를 재사용한다. 로그인 때문에 상세가 안 보이면 그 범위를 명시하고 반복 시도하지 않는다. 도달·저장·공유·유지율을 꾸미지 않는다.
- 최강 1순위부터 새 추천 10개와 **검증된 예비 최대 3개**를 만든다. 검토 완료가 10개 미만이면 초반 검색이나 6~12개 검색을 마쳤다는 이유로 종료하지 않는다. 남은 약 20분 조사 창에서 아직 읽지 않은 유망 후보와 부족한 분야의 다른 공개 경로를 우선 검토한다. 검토한 3개와 전체에서 가능한 소재가 3개라는 주장은 다르다. 실제로 10개를 확보하면 시간을 채우려고 기다리지 않는다. 기한까지 열 개를 확보하지 못하면 작업 기록을 저장하고 확보 수·부족 수·구체적 검증 장애를 짧게 알린다. 부분 송신·미완료 성공 처리는 하지 않는다.

## 회차 사이의 수집과 검토 이어가기

수집기는 한국시간 07~23시에 30분 간격으로 공개 목록을 갱신한다. GitHub 예약 실행은 지연될 수 있으므로 `generated_at`으로 마지막 실제 갱신을 확인한다. 최근 48시간 후보를 최대 3,000개 누적하며 목록에서 사라진 미검토 후보를 바로 지우지 않는다. `first_seen_at`/`observed_at`은 발견 시각이며 사건일·게시일·검토일이 아니다. `fresh_count`/`retained_count`를 구별하고 이번 수집이 모두 실패했다면 이전 후보를 남겨도 status=unavailable로 기록한다. 수집은 모델을 호출하거나 소재를 승인하지 않는다.

`data/discovery-history.json`은 수집 전용 공개 기록이다. 수집기는 `data/history.json`이나 암호화 송신 이력을 쓰지 않으며 송신의 production 잠금도 점유하지 않는다. 본문 확인을 위한 자료 링크를 모았다는 이유로 `video_viewed`를 true로 바꾸지 않는다.

편집자는 매 회차 `data/editorial-progress.json`을 먼저 읽어 이전의 미발송 검토·보류 이유를 이어받는다. 없으면 아래 형식으로 시작한다. 이 파일은 **진행 메모**이며 게재·발송 이력이 아니다.

```json
{"version":1,"updated_at":1792375200,"items":[],"attempts":[]}
```

- 메모 항목은 `event_key,url,title,category,status,note,next_action,recorded_at`이다. status는 `needs_facts`/`needs_date`/`needs_visual`/`rejected`. 확인하지 못한 조건과 다음 확인 경로를 구체적으로 적는다. 메모 작성 시각을 원문·영상 검증 시각으로 쓰지 않는다.
- 실제 완성한 항목은 status=`reviewed`, 같은 식별자·url·title·category·recorded_at과 전체 v2 `pick`, 그때 실제 수행한 `coverage`를 보관한다. 완성한 3개도 저장하되 발송 파일이나 요청은 만들지 않는다. 확인한 시각은 유지하고 75분을 넘으면 `needs_recheck`로 취급해 원문·현재 사실을 다시 확인한다. 메모 저장만으로 verified_at을 갱신하지 않는다.
- `attempts`에는 회차별 `hour_utc,at,status,required,ready,missing,unfinished`를 기록한다. status는 `researching`/`research_incomplete`/`review_complete`/`submitted`이며 실제 송신 성공을 뜻하지 않는다. 10개 미만이면 research_incomplete로 끝내고 어디서 중단됐는지 메모를 남긴다. 현재 송신 상태는 기존 state/status/history와 실제 전달 로그로 별도 확인한다.
- 작업 메모는 48시간·300개, 회차 기록은 7일·42개를 보관한다. sent/uncertain 공개 이력만 실제 중복 제외에 사용한다. 같은 사건의 다른 URL은 event_key를 맞춰 사람이 확인한다. 미검토 목록이나 이전 반려 메모를 발송 증거로 쓰지 않는다.
- `python editorial_progress.py`는 발송 이력을 먼저 뺀 완성/보류/미검토 수와 서로 다른 출처의 후보 표본을 읽기 전용으로 출력한다. 출력은 도구 안에서 파싱해 필요한 항목만 꺼낸다. `--hour YYYYMMDDHH --notes <JSON 배열 파일> --review <부분 v2 검토본>`은 메모와 실제 검증된 부분 검토본을 병합한다. --review는 선택 사항이고 기존 수신기 schema 검사를 통과해야 한다. 이 명령은 Telegram·발송 요청·확정 송신 상태를 건드리지 않는다.
- 회차마다 진행/종료 메모를 최신 main에 CAS로 저장한다. **진행 기록 커밋은 data/editorial-progress.json 하나만** 수정하며 요청 워크플로를 시작하지 않는다. 아래의 최종 발송 요청 커밋은 여전히 picks/request 두 파일만 원자적으로 반영한다. 충돌 시 최신 메모를 읽어 다른 실행의 작업을 보존한다.

## 준비 완료 조건

`scene`: 실제 확인한 핵심 이미지/연속 프레임을 1개 이상 갖춘다. 댓글·문자 캡처는 대화·출처·날짜를 확인하고 농담을 사실상 비난으로 바꾸지 않는다. 날짜가 확인되지 않는 옛 장면은 보류한다.

`major_news`: 영상 없이 사실 카드로 제작할 수 있을 만큼 확정 여부·규모·영향이 구체적이어야 한다. 제안/주장/이적설을 확정 사실로 쓰지 않는다. 유명인이나 숫자 하나로 큰 뉴스라고 판정하지 않는다. 실제로 보지 않은 영상은 source 링크일 뿐이다.

## 정확한 검토본 schema — edition version 2

아래와 **같은 키**를 사용한다. URL·날짜·내용·시각은 실제 검토 결과로 바꾼다.

```json
{
  "version": 2,
  "hour_utc": "YYYYMMDDHH",
  "reviewer": "ChatGPT",
  "generated_at": 1792235100,
  "coverage": {
    "queries": ["actual football search", "actual idol search", "actual current-affairs search", "actual major-sports search"],
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
- Category: `시사` / `축구` / `메이저 스포츠` / `아이돌`. kind: `community` / `social` / `official` / `article`.
- coverage.queries: 실제 검색 4~40개, 각 250자 이하. opened_urls: 실제 본문/자료를 연 공개 HTTPS URL 최대 80개. unavailable: 실패 설명 최대 30개, 각 180자 이하. 실패 URL은 opened에 넣지 않는다.
- picks: 순위별 검토본, 보통 10~13개. 수신기 schema 최대 20개는 과거 호환용 상한이다. 실제 메시지는 중복 필터 후 상위 **정확히 10개**다. 부족한 초안은 진단용이며 제출·부분 전송하지 않는다. empty_reason은 160자 이하, picks가 비었으면 필수다.
- 각 pick: title≤90, source≤40, event_key≤160, why≤180, angle≤150, why_now≤180, caution≤150자. caution만 빈 문자열을 허용한다. 왜·첫 장은 간결한 한 문장씩 쓴다. Markdown/Telegram HTML을 JSON 본문에 넣지 않는다.
- event_key는 소문자 안정적인 사건 식별자다. 같은 사건은 기존 키를 재사용한다. 다른 제목·매체·새 수집 시각은 새 사건이 아니다. 진짜 새 후속은 why_now에 새 사실을 명시한다.
- verified_at은 실제 원문/자료를 확인한 epoch 정수다. generated_at과 verified_at은 발송 때까지 **75분** 이내여야 한다. 값을 갱신해 검토한 척하지 않는다. published_at은 검증된 원문 게시 epoch 또는 null이며 사건일 추정값이 아니다.
- evidence: 1~3개, 정확히 url/note 키, note≤220자. materials: 0~3개, 정확히 url/label/kind, label≤25자. material kind는 image/video/source이며 **실제로 본 영상만 video**다. 모든 선택·근거·자료 URL은 coverage.opened_urls에도 있어야 한다.
- readiness: 정확히 mode/event_date/observation/checked_materials/outline. mode=scene|major_news, event_date는 출처로 확인한 실제 사건·새 발표의 YYYY-MM-DD이며 미래 날짜 금지. observation≤240자. checked_materials는 실제 본 image/video URL 최대 3개이며 그 pick의 materials와 opened에도 있어야 한다. scene은 1개 이상 필수다. outline은 확인된 사실과 장면만으로 구체적인 카드/컷 2~4개, 각 120자 이하다.
- `/info` 상세 하나도 Telegram 1메시지(3,900 UTF-16 단위) 안에 들어가야 한다. 본문을 무작정 길게 쓰지 않는다. 제목·선정 이유·첫 장은 메인 메시지에, 검증 근거·주의·제작 순서는 /info에 둔다.

## 제출·발송 절차

1. 쓰기 직전 최신 main ref/commit/tree와 state/request를 다시 읽는다. 대상 시간대 sent/already_sent+그 시간 안 updated_at이면 **stories=10,messages=1까지** 확인한다. 이전 부분 전송은 완료가 아니지만 이미 보낸 회차를 자동 재전송하지 않는다.
2. 같은 hour_utc 요청이 있으면 두 파일을 다시 쓰거나 새 해시로 재요청하지 않는다. 해당 Trend Radar delivery request 실행을 확인한다. queued/in_progress·정상 정각 대기는 접수 상태다. DeliveryUncertain/부분 전송/불명확 결과는 자동 재전송하지 않는다.
3. 정확한 picks 파일 바이트의 SHA-256을 구한다. request는 아래 한 줄 JSON+마지막 줄바꿈이다.

```json
{"version":2,"hour_utc":"YYYYMMDDHH","editorial_sha256":"64자리 소문자 SHA-256"}
```

4. 이 **두 파일만** 최신 main tree에서 `github_create_tree` → 최신 head 단일 parent `create_commit` → `expected_sha=그 head, force=false update_ref`로 한 커밋에 반영한다. 메시지: `Curate BTP digest <시간대> UTC`. 충돌이면 최신 state/request/ref를 다시 읽고 여전히 필요한 경우만 반영한다. 다른 코드·파일·credentials·대상·암호화 이력을 바꾸지 않는다.
5. 다가오는 정각 요청은 정각 전 **20분 안**에서만 유효하며 receiver가 정각까지 기다린다. 작업은 트리거 커밋의 두 파일과 해시를 고정해서 읽는다. 대기 후에도 검토 유효성을 재검사한다. 지난 시간대를 재생하지 않는다.
6. 현재 회차는 20~30초 간격 최대 6분 확인하며 한 번에 60초 넘게 기다리지 않는다. 해당 회차 state의 실제 sent/already_sent, stories=10, messages=1 또는 실제 전달 단계 TELEGRAM_REPORT_COMPLETE 1을 확인한다. 회귀 테스트의 모의 로그는 성공 근거가 아니다. 정각 전 대기는 접수 성공일 뿐 발송 완료라고 하지 않는다.

명시적인 새 사용자 요청(“지금 보내봐”)이 있을 때만 현재 시간대 version 3 요청을 쓴다. 정확히 version/hour_utc/editorial_sha256/mode 키, `mode="user_requested"`이며 같은 고정 해시로 한 번만 송신한다. 정기 자동화는 이 예외를 사용하지 않는다. 같은 사건의 7일 중복·불확실 전송 보호는 그대로 적용된다. 별도 명시적 변경이 없으면 추가 요청도 새 10개 기준을 따른다.

## 코드의 보장 범위와 상태 확인

- 시간: report_timing.require_report_slot이 정기 6개 한국시간 외 요청을 송신 전 거부한다.
- 수량: curated_report가 운송 전 10개 이상 검토되었는지, **최종 7일 sent/uncertain 필터 후 정확히 10개인지** 검사한다. 4/6/8/9개를 정상 보고로 보내지 않는다. 예비를 포함해도 부족하면 송신하지 않는다.
- 중복: 기존 승인 그룹 확인·암호화 공통 시간대/콘텐츠 이력·원본 사건 키를 유지한다. uncertain/부분 전송을 자동으로 다시 보내지 않는다.
- 마지막 발송: data/state.json은 확정된 실제 송신 상태를 담는다. 전송 실패/검토 부족으로 이전 성공을 지우지 않는다.
- 최근 시도: workflow가 data/editorial-status.json에 credential 없는 target/status/ready/required/missing/duplicates_excluded를 기록한다. insufficient_new_material은 **미발송**이며 성공이 아니다. 이 기록은 정각 전 대기 중인 작업이 끝나기 전에는 아직 없을 수 있다.
- 수집: data/candidates.json의 status와 errors/counts를 함께 본다. 일부 출처가 막혀도 나머지 성공 후보를 보존해 degraded로 기록하고, 후보 전체 0개는 실패다. 공개 간접 펨코 목록·커뮤니티와 Naver 스포츠 영상 발견 자료를 사용한다. 수집 상태와 발송 상태는 별개다.
- 정상 발송·이미 발송·정상 대기는 이 대화에 별도 알리지 않는다. 실패·수량 부족·지속되는 불확실은 확보/부족 수, 확인한 한국시각과 실행 링크(있을 때)를 짧게 알린다. 진행 중이라는 말로 무한히 기다리게 하지 않는다.
- 봇 토큰·Chat ID·암호화 데이터 내용을 읽거나 출력하지 않는다. Telegram API 직접 호출·테스트 송신은 하지 않고 기존 승인된 Python workflow만 실제 송신한다. 새 자동화 생성, 다른 자동화 변경, 자동 Instagram 업로드, 대상 변경을 하지 않는다. 한 번 성공했다고 이 정기 작업을 끄지 않는다. 연결 권한으로 완전히 막힌 경우에만 이 동일 작업을 중지하고 필요한 권한을 알린다.

프로필의 공개 표지 분석은 docs/btp-profile.md에 있다. Meta의 일반적인 공유 신호 설명은 https://about.fb.com/news/2023/06/how-ai-ranks-content-on-facebook-and-instagram/ 이며 BTP 성과의 인과관계나 보장으로 바꾸지 않는다.

