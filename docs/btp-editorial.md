# BTP 편집·발송 운영 — 2026-10-22 재설정

## 목표와 보고 시간

@bythepulse에서 바로 제작할 새 소재 **목표 10개**를 기존 승인된 Btp Telegram 그룹에 **메시지 1개**로 전달한다. 한국시간 **08·11·14·17·20·23시마다 반드시 보고**한다. 소재가 부족해도 회차를 누락하지 않는다. 검증한 새 소재가 0~9개면 확보한 만큼과 부족 수·구체적인 이유를 같은 메시지에 적고, 0개여도 현황 보고를 보낸다. 10개는 편집 목표이며 미달을 발송 금지로 쓰지 않는다. 보고 사이 후보 수집은 10분 간격, AI 검토는 매시간 이어받으며 3시간 상시 AI 분석으로 표현하지 않는다. 마지막 정기 보고는 23시다. 과거 회차 몰아 보내기·테스트 메시지·Instagram 자동 게재는 하지 않는다.

이 문서를 먼저 읽고 `docs/btp-profile.md`의 확인된 공개 표지와 사용자 반려 사례, `data/editorial-learning.json`의 최근 대조·검증할 가설을 기준으로 판단한다. 100만 조회수는 대중성과 공유 이유를 엄격히 보는 편집 목표다. 조회수 예측·보장이나 Instagram Insights 분석을 했다는 뜻이 아니다. 수집량·JSON 통과·발송 성공은 실제 제작 채택 성과와 구별한다.

## 2026-10-22 사용자 재설정 — 현재 선정 기준

사용자가 BTP와 가장 비슷한 결로 지정한 **펨코를 편집 취향의 기준**으로 삼는다. 목표는 펨코에 올라올 만한 사건·장면을 원본 공개 단계에서 먼저 찾아 알리는 것이다. 펨코 포텐 진입, 높은 조회수·추천수, 다른 커뮤니티의 재게시를 기다리지 않는다. 실제 펨코에 올라왔다거나 앞으로 뜬다고 보장하지 않는다. 이 절의 최신 사용자 지시는 아래의 과거 표지 가설과 이전 검색 습관보다 우선한다.

매 회차 다음 세 갈래를 모두 탐색한다. 최종 10개는 분야별 고정 할당 없이 전체 검증 후보에서 상대 순위를 매긴다.

1. **해외축구·국내축구:** 경기와 훈련의 사건사고, 실수·돌발 행동·세리머니·벤치/관중 반응, 라이벌끼리 놀릴 지점, 말과 행동의 대비, 인터뷰·기자회견의 직접 발언과 반박, 구단·협회 논란과 실제 후속. 평범한 스코어보다 “어떤 일이 벌어져 팬들이 누구에게 왜 이 장면을 보낼까”를 구체화한다.
2. **3~5세대 여자아이돌:** 공식·본인 YouTube 콘텐츠, 예능·자체 콘텐츠, 음방·앙코르·라이브·직캠에서 나온 대화·자막·실수·대처·엉뚱한 행동·멤버 간 티키타카·의외의 반전, 확인된 사건사고와 당사자 입장. 세대·이름·신곡이라는 이유만으로 선정하지 않고 클립의 실제 웃음·화제 포인트를 확인한다.
3. **일반 커뮤니티:** 밈·유머·웃긴 사건·황당한 실제 상황·공감되는 생활 사건, 정치인의 실제 발언·행동과 전후 대비, 사회적 논란·사건사고·시사. 정치·시사를 보조 분야로 밀어내거나 공식 대형 발표만 대상으로 좁히지 않는다. 낯선 인물도 한국 독자가 짧은 맥락으로 이해하고 공유할 분명한 포인트가 있으면 검토한다.

메이저 스포츠도 같은 웃음·놀람·논란·결정적 장면 또는 큰 확정 사건이 있으면 함께 비교한다. 낯선 종목의 통상 기록·대회 일정·일반 전망 기사로 10개를 채우지 않는다. 기존 category 스키마는 유지하며 밈·유머·일반 사건·정치·사회는 `시사`, 여돌은 `아이돌`로 기록한다. `시사`라는 이름 때문에 유머 후보를 제외하지 않는다.

### 선발굴 경로

- 처음 6~12개 집중 검색은 국내/해외축구, 3~5세대 여돌, 일반 밈·유머/정치·시사에 나눠 쓴다. 축구·여돌을 먼저 살피되 세 갈래 중 하나를 검색 없이 “없음”으로 처리하지 않는다.
- 펨코의 접근 가능한 최신 게시·공개 색인·인용에서 현재의 제목 각도와 장면 단서를 익히고, 같은 회차에 원본 단계도 직접 찾는다. 구단·리그·방송사 경기/훈련 클립·기자회견, 아티스트/제작사 YouTube·음방 채널, 본인 SNS·당사자 원문·공식 기록을 살핀다. 해외축구는 영문 원문도 찾는다.
- 더쿠·인스티즈·개드립·루리웹·엠팍 등은 초기 단서와 교차 발견에 쓴다. 이미 커진 글의 재요약에만 머무르지 않고 원본의 처음 공개 시각과 새 포인트를 찾는다. 확인하지 못한 원본은 보류 이유와 다음 경로를 남긴다.
- 낮은 조회수·댓글 0개·아직 펨코에 없음은 탈락 사유가 아니다. 실제 관측한 확산 지표는 보조 근거로만 쓰고, 추측한 조회수·펨코 반응은 만들지 않는다. 접근 차단은 반복·우회하지 않고 독립 원본으로 전환한다.

### 상대 순위 판단

원본·날짜·사실·중복 확인을 마친 뒤 **펨코에서 통할 구체적인 포인트 → 첫 장/첫 컷의 전달력 → 웃음·반전·놀림·논란·공감의 설명력 → 지금 알릴 새로움 → BTP 제작 가능성** 순으로 비교한다. 수치 점수와 절대 합격선을 만들지 않는다.

각 후보의 why에는 “누가 누구에게, 무엇이 웃기거나 놀랍거나 말이 안 돼서 보낼지”를 쓴다. angle과 outline에는 확인한 대사·동작·전후 대비·결과를 2~4컷으로 구체화한다. “1장 핵심 수치/2장 변화/3장 영향” 같은 모든 후보 공통 문구는 쓰지 않는다. 원본에서 실제로 본 한 장면이나 실제 문장을 제목의 중심에 둔다.

팬만 이해하던 작은 장면도 맥락 한 줄과 실제 재미로 전달되면 평가한다. 장난·놀림·우스운 실수·재미있는 팬서비스를 일괄 제외하지 않는다. 특정 사건에 대한 과거 반려는 그 사건에 적용하며 닮은꼴·충돌·항의·농담 전체를 영구 금지하지 않는다. 확인 안 된 비난·악의적인 짜깁기·단순 외모 소비·일상 근황·홍보 티저·억지 밈은 제외한다. 정치 성향을 채택하거나 편들기보다 실제 발언·행동·결정과 맥락을 확인한다.

기존 12시간 최초 공개, 75분 실제 검토, 동일 사건·7일 발송 중복 보호, 사실과 주장 구분, 상위 10개·한 메시지·승인된 Python 송신은 유지한다. 100만 조회수는 목표이며 보장·절대 문턱이 아니다. 소재가 10개 이상 검증됐으면 1~3위와 8~10위의 강도가 다르다는 이유로 빈칸을 만들지 않는다.

Python 수집·키워드 점수는 발견 보조이며 실제 선정은 위 기준으로 ChatGPT가 원문을 검토해 결정한다. 설정 재정비는 발송 잠금이나 과거 sent/uncertain 이력을 초기화한다는 뜻이 아니다.


## 보고 사이의 누적 조사

- `python editorial_cycle.py`는 공개 state/request/status/history와 후보 갱신 시각만 읽어 현재 단계·대상 회차·기존 요청 잠금·수집 지연을 출력한다. `research`는 중간 조사, `prepare`는 1시간 이내 준비, `report`는 현재 보고 시간대의 미발송 보완이다. `may_submit=false`이면 발송 요청을 쓰지 않는다. `await_delivery`는 기존 요청을 관찰하며 재요청하지 않는다. `day_complete`/`off_hours`는 야간 새 회차를 만들지 않는다.
- 정기 자동화는07~23시 매시간 검토한다. 보고가 이미 끝났어도 그날 다음 회차의 미발송 후보를 검토하고 진행을 저장한다. 3시간 내내 AI 프로세스가 켜져 있는 것으로 표현하지 않는다. ChatGPT 자동 실행의 최대 빈도는 매시간이며 실제 웹 수집은 별도 Python이 수행한다.
- 기존 수집 workflow는07~23시10분 간격과 `data/editorial-progress.json` 변경으로 시작한다. GitHub 예약 실행이 늦더라도 AI가 시작·중간·종료 진행을 저장하면 수집을 다시 깨운다. 최근8분 이내 유효한 수집이 있으면 중복 조회를 생략한다. 자체 후보 파일 갱신은 재트리거하지 않는다. 수집 성공과 실제 본문·장면 검증은 다르다.
- 후보 generated_at이20분 넘게 오래됐거나 unavailable이면 최신 수집으로 취급하지 않는다. 진행 파일에 실제 시작 기록을 CAS 저장해 수집을 깨우고, 직접 공개 원문 조사도 계속한다. 다음 회차가 아직1시간 이상 남았다는 이유로 종료하지 않는다.
- 조기 완성본은 **현재 실제 UTC 시간대**의 임시 v2 검토본으로 검사하고 `python editorial_progress.py --hour <다가오는 보고 UTC> --research-only --review <임시 JSON> --stage researching`으로 저장한다. `--research-only`는 진행 저장 전용이며 현재/당일 다음4시간 안의 정기 회차만 받는다. 발송 잠금과 준비 가능 시간은 바뀌지 않는다. 원래 verified_at을 보존하고 발송까지75분을 넘길 자료는 마지막 준비 때 실제 재확인한다.
- 최종 발송은 may_submit=true인 현재/1시간 이내 회차에서 기존 v2 picks/request로 한다. 목표 10개이며 부족하면 검증한 0~9개도 제출한다. 같은 시간대 요청·sent·uncertain·실제 부분 전송은 새 해시로 재요청하지 않는다. 0~9개를 정상적으로 한 메시지에 보낸 것은 새 수량 정책에 따른 확정 보고이며, 목표 달성으로 포장하지 않는다.

## 후보를 실제 추천으로 완성하기

1. 실제 확인한 동작·대사·캡처·전후 대비 또는 새로 확정된 사실을 첫 장으로 특정한다.
2. 한국 독자가 누구에게 무슨 이유로 공유할지 설명한다. 축구 팬의 놀림·라이벌 구도, 여돌 콘텐츠의 웃긴 대화·돌발 대처, 일상 공감·황당함·정치사회 논란의 쟁점을 구체적으로 쓴다.
3. 다음 카드에서 행동·반응·결과를 확인된 자료로 회수한다. 보지 못한 표정·반응·댓글을 만들어 넣지 않는다.
4. 사건 발생일·최초 공개일·업로드일을 구별한다. 이미 오래된 밈이나 장면의 재업로드를 12시간 이내 새 사건으로 바꾸지 않는다.
5. 제목·도메인이 달라도 같은 사건의 event_key를 맞추고 실제 sent/uncertain·BTP 게재 사건과 대조한다.

사용자가 반려한 커 감독 닮은꼴, 중국 유소년 감독 항의 재연, 야말·베르날 충돌, 프랑스 시위 피해 집계 갱신은 그대로 재추천하지 않는다. 이 사례에서 모든 축구 놀림거리·소소한 여돌 장면·일반 밈을 금지하는 규칙을 만들지 않는다.

사용자 긍정 예시인 레드벨벳 자막 피드백(https://m.fmkorea.com/best/10454601662)은 실제 요청과 전후 대비가 핵심이다. 이 사례 자체를 새 추천으로 보내거나 한 글이 수정을 일으켰다고 추정하지 않는다.

## 실제 조사와 작업량

- 실제 현재 한국시각·UTC YYYYMMDDHH·정각 epoch를 도구로 구한다. `report_timing.editorial_target(now)`처럼 현재 시간이 보고 시간이면 현재 회차, 아니면 다음 정각이 보고 시간이면 다음 회차를 준비한다. 예: 07:00→08시, 지연된 08:45→현재 08시, 09시→발송 안 함. 조사 후와 쓰기 직전에 다시 확인한다. 미래 요청의 접수 범위는 정각 전 60분이며 실제 송신은 정각부터다.
- main의 state/request/picks/editorial-history/candidates를 읽는다. 도구 안에서 파싱하여 필요한 발송 event_key·신선한 유망 후보·실패 출처만 출력한다. 전문을 반복 출력하지 않는다. 최초 새 파일 404는 정상이다.
- `data/editorial-history.json`의 **sent/uncertain** 사건과 event_key를 먼저 제외한다. 수집된 적만 있는 미발송 후보는 제외하지 않는다. BTP 공개 표지의 확인 가능한 기존 게재도 대조하되, 실제 게시와 추천이 게재의 원인이 됐다는 판단을 구별한다.
- 위 세 갈래와 선발굴 경로를 따라 6~12개 집중 검색으로 시작한다. 펨코 취향과 원본의 초기 포인트를 함께 확인하고, 빠진 원본·날짜·장면만 보완한다. 해외축구는 영문도 쓰며 검색량·조회수 하한을 통과 조건으로 삼지 않는다.
- 후보 스냅샷은 발견용이다. 원문 본문·실제 사진·핵심 동작과 결과를 포괄하는 연속 프레임을 열어 확인한다. 검색 요약, 플레이어, 썸네일, 인터뷰의 묘사는 영상 시청이 아니다. Naver 공개 영상 후보의 `video_viewed=false`를 유지한 채 발견 링크로 사용하고 실제 검토 후에만 추천한다. 업로드 날짜를 원래 경기·사건 날짜로 바꾸지 않는다.
- 보호 확인이 끝나지 않는 펨코 직접 경로를 반복하지 않는다. 접근 가능한 인용본·독립 원본으로 확인하고, 읽지 않은 펨코 본문을 봤다고 쓰지 않는다. 실패는 coverage.unavailable에 남긴다. 공개·독립 자료를 사용하며 차단·인증·지역 제한을 우회하지 않는다.
- 프로필 공개 그리드는 매 보고 준비 때 한 번 확인하고 이전 post_id와 비교해 새로 확인한 표지만 분석한다. 같은 표지 전문·실패한 상세 경로를 반복하지 않는다. 로그인 때문에 상세가 안 보이면 범위를 기록한다. 도달·저장·공유·유지율을 꾸미지 않는다.
- 가장 강한 1순위부터 목표 10개와 검증된 예비 최대 3개를 준비한다. 중간 조사에서는 미검토 유망 후보의 원본·날짜·장면을 계속 확인하고 진행을 저장한다. 보고 시각을 소재 수량 때문에 넘기지 말고 확인된 개수로 제출한다. 검증된 후보 전체에서 상위 10개를 고르며 상대적으로 약한 하위 순위라는 이유로 칸을 비우지 않는다. 중복·소문·미확인 영상은 수량과 별개로 제외한다. 부족 수와 실제 장애는 empty_reason에 적고 Telegram 한 메시지에 함께 전달한다.

## 회차 사이의 수집과 검토 이어가기

수집기는 한국시간 07~23시에 10분 간격으로 공개 목록을 갱신한다. GitHub 예약 실행은 지연될 수 있으므로 `generated_at`으로 마지막 실제 갱신을 확인한다. 최근 48시간 후보를 최대 3,000개 누적하며 목록에서 사라진 미검토 후보를 바로 지우지 않는다. `first_seen_at`/`observed_at`은 발견 시각이며 사건일·게시일·검토일이 아니다. `fresh_count`/`retained_count`를 구별하고 이번 수집이 모두 실패했다면 이전 후보를 남겨도 status=unavailable로 기록한다. 수집은 모델을 호출하거나 소재를 승인하지 않는다.

`data/discovery-history.json`은 수집 전용 공개 기록이다. 수집기는 `data/history.json`이나 암호화 송신 이력을 쓰지 않으며 송신의 production 잠금도 점유하지 않는다. 본문 확인을 위한 자료 링크를 모았다는 이유로 `video_viewed`를 true로 바꾸지 않는다.

편집자는 매 회차 `data/editorial-progress.json`을 먼저 읽어 이전의 미발송 검토·보류 이유를 이어받는다. 없으면 아래 형식으로 시작한다. 이 파일은 **진행 메모**이며 게재·발송 이력이 아니다.

```json
{"version":1,"updated_at":1792375200,"items":[],"attempts":[]}
```

- 메모 항목은 `event_key,url,title,category,status,note,next_action,recorded_at`이다. status는 `needs_facts`/`needs_date`/`needs_visual`/`rejected`. 확인하지 못한 조건과 다음 확인 경로를 구체적으로 적는다. 메모 작성 시각을 원문·영상 검증 시각으로 쓰지 않는다.
- 실제 완성한 항목은 status=`reviewed`, 같은 식별자·url·title·category·recorded_at과 전체 v2 `pick`, 그때 실제 수행한 `coverage`를 보관한다. 완성한 3개도 저장하되 발송 파일이나 요청은 만들지 않는다. 확인한 시각은 유지하고 75분을 넘으면 `needs_recheck`로 취급해 원문·현재 사실을 다시 확인한다. 메모 저장만으로 verified_at을 갱신하지 않는다.
- attempts의 회차별 hour_utc/at/status/required/ready/missing/unfinished를 기록한다. researching/research_incomplete는 검토 진행 상태이고, review_complete는 목표 10개 검토 완료다. submitted는 실제 제출을 뜻하며 0~9개도 가능하다. 이 파일 자체는 실제 송신 성공 증거가 아니며 state/status/history·전달 로그로 확인한다.
- 작업 메모는 48시간·300개, 회차 기록은 7일·42개를 보관한다. sent/uncertain 공개 이력만 실제 중복 제외에 사용한다. 같은 사건의 다른 URL은 event_key를 맞춰 사람이 확인한다. 미검토 목록이나 이전 반려 메모를 발송 증거로 쓰지 않는다.
- `python editorial_progress.py`는 발송 이력을 먼저 뺀 완성/보류/미검토 수와 서로 다른 출처의 후보 표본을 읽기 전용으로 출력한다. 출력은 도구 안에서 파싱해 필요한 항목만 꺼낸다. `--hour YYYYMMDDHH --notes <JSON 배열 파일> --review <부분 v2 검토본>`은 메모와 실제 검증된 부분 검토본을 병합한다. --review는 선택 사항이고 기존 수신기 schema 검사를 통과해야 한다. 이 명령은 Telegram·발송 요청·확정 송신 상태를 건드리지 않는다.
- 회차마다 진행/종료 메모를 최신 main에 CAS로 저장한다. **진행 기록 커밋은 data/editorial-progress.json 하나만** 수정하며 요청 워크플로를 시작하지 않는다. 아래의 최종 발송 요청 커밋은 여전히 picks/request 두 파일만 원자적으로 반영한다. 충돌 시 최신 메모를 읽어 다른 실행의 작업을 보존한다.

## 게재 대조와 놓친 소재 복기

매 회차 초반 약 2분 안에서 BTP 공개 그리드와 직전 추천·보류 기록을 대조한다. 조회·로그인 제한이면 마지막 성공 관찰을 보존하고 이번 확인 실패 시각을 기록한다. 확인 실패를 ‘새 게시물 없음’으로 바꾸지 않는다. 이 분석은 기존 3시간 회차에 포함하며 수집기의 10분 갱신을 AI의 상시 분석이라고 표현하지 않는다.

`data/editorial-learning.json`은 version=1, updated_at, profile_checks, observations, rules를 갖는다. profile_checks는 at/profile_url/status/visible_post_ids/newly_documented_ids/limits를 기록하고 최근 42회만 보관한다. observations는 게시 식별자별로 보관하며 이미 본 항목을 중복 추가하지 않고 최근 100건을 유지한다. 각 항목에 post_url, 실제 observed_at, 확인 범위(scope), 화면 표시 날짜와 정확한 published_at(미확인이면 null), 실제 관찰한 내용, 비교한 발송 이력의 commit·회차수·기간·일치 결과, 놓친 단계(miss_stage), 근거·불확실성, 다음 변경을 남긴다. 원문 미열람 후보 URL은 discovery_urls로만 두고 검증 증거로 세지 않는다. metrics는 실제 보이는 공개 수치와 관찰 시각만 기록하고 안 보이면 null이다.

놓친 단계는 source_gap(당시 수집 누락), triage_gap(수집했으나 미검토), verification_gap(검증 중단), judgment_gap(검토 후 오판), delivery_gap(선정했으나 미전달), undetermined 중 증거로 확인되는 것으로 쓴다. 게시 전 추천 기회가 있었는지는 당시 후보 스냅샷·게시 시각을 대조해야 한다. 현재 목록이나 7일 미만의 이력에 없다는 이유로 과거 전체 미추천·미수집을 단정하지 않는다. 추천과 게시가 겹쳐도 추천 때문에 게시됐다는 뜻이 아니다. 미게시도 사용자의 반려라고 추정하지 않는다.

새로 본 사례 1~2개에서 구체적인 다음 행동을 만든다. 소스 누락이면 독립 원본 경로, 미검토면 우선순위, 검증 중단이면 필요한 날짜·자료, 오판이면 통과/탈락 기준을 지정한다. rules는 id/status/rule/evidence_ids/introduced_at/next_check/outcome을 가진 최대 12개다. 표본에서 나온 가설은 hypothesis로 두고 다음 두 회차의 실제 예시·사용자 피드백으로 유지·수정·폐기를 판단한다. 확인되지 않은 기준을 매번 늘리거나 100만 조회수 예측·반응 수치를 만들지 않는다. 기존 사건일·원본·장면 검증 기준을 완화하지 않는다.

다음 추천은 기존 강한 가설과 최신 사용자 피드백을 읽고 첫 장의 증거·왜 공유할지·새 사실·구체적 제작 순서를 제시한다. 이미 BTP에 게재된 같은 사건은 원문 도메인을 바꿔 다시 보내지 않는다. 큰 구단의 경쟁 구도 변화는 단순 스코어와 구별하고, 오래된 원 사건의 새 공개 사실은 재포장과 구별한다. 법적 분쟁은 주장·확정 사실을 분리한다.

학습 기록은 최신 main 기반 CAS로 **data/editorial-learning.json 하나만** 별도 커밋할 수 있다. 앞의 진행 파일과 함께 각각 허용되는 운영 기록 예외이며 발송 요청이나 실제 발송 이력은 건드리지 않는다. 최종 picks/request는 여전히 두 파일 원자 커밋이다. 점검·학습만을 위한 추가 Telegram 보고는 보내지 않는다.

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
- picks는 순위별 0~13개를 사용한다. 실제 메시지는 7일 sent/uncertain 중복 제외 후 상위 최대 10개다. 0~9개면 확보 수·부족 수·이유를 명시하여 한 메시지로 보낸다. empty_reason은 160자 이하이며, 부족한 검토본에는 구체적인 부족 이유를 쓴다.
- 각 pick: title≤90, source≤40, event_key≤160, why≤180, angle≤150, why_now≤180, caution≤150자. caution만 빈 문자열을 허용한다. 왜·첫 장은 간결한 한 문장씩 쓴다. Markdown/Telegram HTML을 JSON 본문에 넣지 않는다.
- event_key는 소문자 안정적인 사건 식별자다. 같은 사건은 기존 키를 재사용한다. 다른 제목·매체·새 수집 시각은 새 사건이 아니다. 진짜 새 후속은 why_now에 새 사실을 명시한다.
- verified_at은 실제 원문/자료를 확인한 epoch 정수다. generated_at과 verified_at은 발송 때까지 **75분** 이내여야 한다. 값을 갱신해 검토한 척하지 않는다. published_at은 검증된 원문 게시 epoch 또는 null이며 사건일 추정값이 아니다.
- evidence: 1~3개, 정확히 url/note 키, note≤220자. materials: 0~3개, 정확히 url/label/kind, label≤25자. material kind는 image/video/source이며 **실제로 본 영상만 video**다. 모든 선택·근거·자료 URL은 coverage.opened_urls에도 있어야 한다.
- readiness: 정확히 mode/event_date/observation/checked_materials/outline. mode=scene|major_news, event_date는 출처로 확인한 실제 사건·새 발표의 YYYY-MM-DD이며 미래 날짜 금지. observation≤240자. checked_materials는 실제 본 image/video URL 최대 3개이며 그 pick의 materials와 opened에도 있어야 한다. scene은 1개 이상 필수다. outline은 확인된 사실과 장면만으로 구체적인 카드/컷 2~4개, 각 120자 이하다.
- `/info` 상세 하나도 Telegram 1메시지(3,900 UTF-16 단위) 안에 들어가야 한다. 본문을 무작정 길게 쓰지 않는다. 제목·선정 이유·첫 장은 메인 메시지에, 검증 근거·주의·제작 순서는 /info에 둔다.

## 제출·발송 절차

1. 쓰기 직전 최신 main ref/commit/tree와 state/request를 다시 읽는다. 대상 회차 sent/already_sent와 messages=1은 실제 stories가 0~10개라도 다시 보내지 않는다. stories/missing/target_met를 확인하여 실제 수량을 기록하며, 목표 10개를 채웠는지는 별도로 판단한다.
2. 같은 hour_utc 요청이 있으면 두 파일을 다시 쓰거나 새 해시로 재요청하지 않는다. 해당 Trend Radar delivery request 실행을 확인한다. queued/in_progress·정상 정각 대기는 접수 상태다. DeliveryUncertain/부분 전송/불명확 결과는 자동 재전송하지 않는다.
3. 정확한 picks 파일 바이트의 SHA-256을 구한다. request는 아래 한 줄 JSON+마지막 줄바꿈이다.

```json
{"version":2,"hour_utc":"YYYYMMDDHH","editorial_sha256":"64자리 소문자 SHA-256"}
```

4. 이 **두 파일만** 최신 main tree에서 `github_create_tree` → 최신 head 단일 parent `create_commit` → `expected_sha=그 head, force=false update_ref`로 한 커밋에 반영한다. 메시지: `Curate BTP digest <시간대> UTC`. 충돌이면 최신 state/request/ref를 다시 읽고 여전히 필요한 경우만 반영한다. 다른 코드·파일·credentials·대상·암호화 이력을 바꾸지 않는다.
5. 다가오는 정각 요청은 정각 전 **60분 안**에서 유효하며 receiver가 정각까지 기다린다. 작업은 트리거 커밋의 두 파일과 해시를 고정해서 읽는다. 대기 후 연결을 새로 확인하고 송신 직전에도 현재 시간대와 75분 검토 유효성을 재검사한다. 지난 시간대를 재생하지 않는다.
6. 현재 회차는 20~30초 간격 최대 6분 확인하며 한 번에 60초 넘게 기다리지 않는다. 해당 회차 state의 실제 sent/already_sent, stories=10, messages=1 또는 실제 전달 단계 TELEGRAM_REPORT_COMPLETE 1을 확인한다. 회귀 테스트의 모의 로그는 성공 근거가 아니다. 정각 전 대기는 접수 성공일 뿐 발송 완료라고 하지 않는다.

명시적인 새 사용자 요청(지금 보내봐 등)에는 현재 시간대 version=3, mode=user_requested 고정 해시 요청을 한 번만 쓴다. 정기 회차는 version=2다. 현재 요청도 목표 10개이며 부족하면 검증한 만큼 또는 0개 현황을 보낸다. 7일 중복과 불확실 전송 보호는 유지한다.

## 코드의 보장 범위와 상태 확인

- 시간: report_timing.require_report_slot이 정기 6개 한국시간 외 요청을 송신 전 거부한다.
- 수량: 목표 10개, 실제 최대 10개다. 중복 필터 후 0~9개도 한 메시지로 발송하고 실제 stories/missing/target_met=false를 기록한다. 부족을 이유로 연결 전 또는 필터 후 발송을 중단하지 않는다.
- 중복: 기존 승인 그룹 확인·암호화 공통 시간대/콘텐츠 이력·원본 사건 키를 유지한다. uncertain/부분 전송을 자동으로 다시 보내지 않는다.
- 마지막 발송: data/state.json은 확정된 실제 송신 상태를 담는다. 전송 실패/검토 부족으로 이전 성공을 지우지 않는다.
- 최근 시도: workflow가 data/editorial-status.json에 credential 없는 target/status/ready/required/missing/duplicates_excluded를 기록한다. insufficient_new_material은 **미발송**이며 성공이 아니다. 이 기록은 정각 전 대기 중인 작업이 끝나기 전에는 아직 없을 수 있다.
- 전송 실패와 불확실도 같은 status 파일에 `delivery_failed`/`delivery_uncertain` 및 비밀값 없는 reason_code로 남긴다. state.json의 오래된 성공 기록만으로 현재 회차가 성공했다고 판단하지 않는다. 공개 sent/uncertain 회차는 검토 유효기간이 지나도 연결을 열기 전에 차단하고, 암호화 공통 이력도 기존대로 확인한다.
- delivery-request workflow는 여섯 보고 시간대의 :00에 실행하고 :05·:20·:35·:50에 같은 시간대 잠금으로 재확인한다. 유효한 현재 version=2 요청이 없으면 editorial-progress의 완성된 v2 검토 중 75분 이내인 것만 사용한다. 발송 시각까지 검증 유효성을 다시 확인하며 검증 시간을 갱신하지 않는다. 유효한 후보가 없어도 0개·부족 사유 현황을 보낸다. 후보 수집 목록을 자동 추천으로 승인하거나 새 AI 검색을 한 것처럼 쓰지 않는다. 이미 sent/uncertain이면 재전송하지 않는다. 연결 수립 전 ConnectTimeout만 안전 재시도하며 응답 유실 등은 uncertain으로 보존한다.
- 수집: data/candidates.json의 status와 errors/counts를 함께 본다. 일부 출처가 막혀도 나머지 성공 후보를 보존해 degraded로 기록하고, 후보 전체 0개는 실패다. 공개 간접 펨코 목록·커뮤니티와 Naver 스포츠 영상 발견 자료를 사용한다. 수집 상태와 발송 상태는 별개다.
- 정상 발송·이미 발송·정상 정각 대기는 이 대화에 별도 알리지 않는다. 0~9개 보고도 수량·부족 사유가 Telegram에 포함됐다면 추가 알림으로 반복하지 않는다. 실제 전송 실패·지속되는 불확실만 한국시각·실행 링크로 짧게 알린다.
- 봇 토큰·Chat ID·암호화 데이터 내용을 읽거나 출력하지 않는다. Telegram API 직접 호출·테스트 송신은 하지 않고 기존 승인된 Python workflow만 실제 송신한다. 새 자동화 생성, 다른 자동화 변경, 자동 Instagram 업로드, 대상 변경을 하지 않는다. 한 번 성공했다고 이 정기 작업을 끄지 않는다. 연결 권한으로 완전히 막힌 경우에만 이 동일 작업을 중지하고 필요한 권한을 알린다.

프로필의 공개 표지 분석은 docs/btp-profile.md에 있다. Meta의 일반적인 공유 신호 설명은 https://about.fb.com/news/2023/06/how-ai-ranks-content-on-facebook-and-instagram/ 이며 BTP 성과의 인과관계나 보장으로 바꾸지 않는다.
