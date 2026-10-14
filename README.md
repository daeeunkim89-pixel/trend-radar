# TREND RADAR — 폰만으로 설치

현재 코드는 네이버 많이 본 뉴스 / 네이트 스포츠 / 디시 실베 / 펨코 포텐을 매시간 수집해 각 소스에서 최대 10개를 텔레그램으로 보냅니다. 이전 스냅샷 대비 급상승 비교는 현재 구현되어 있지 않습니다.

## 준비물
- GitHub 계정
- Telegram 계정

## 1. 텔레그램 봇 만들기
1. Telegram에서 `@BotFather` 검색
2. `/newbot` 입력 → 봇 이름/아이디 지정
3. 발급되는 Bot Token 복사
4. 만든 봇에게 아무 메시지나 한 번 보내기
5. 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates`를 열어 `chat.id` 숫자를 확인

여러 사람이 같이 받으려면 텔레그램 채널/그룹을 만들고 봇을 추가한 뒤 해당 채널/그룹의 chat id를 사용하세요.

## 2. GitHub에 올리기
1. GitHub에서 새 Repository 생성 (가능하면 Private)
2. 이 ZIP의 내용 전체를 저장소 루트에 업로드
3. 저장소 `Settings → Secrets and variables → Actions`
4. Repository secrets에 다음 2개 생성
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

## 3. 실행
`Actions → Trend Radar → Run workflow`를 눌러 즉시 수집하고 TOP 10을 전송할 수 있습니다.
그 뒤 매시간 예약 실행이 작동합니다. `data/state.json`에는 최신 수집 수, 전체 상태(`ok`/`degraded`), 소스별 오류가 저장됩니다.

## 중요
현재 예약은 `0 * * * *`입니다. GitHub Actions가 혼잡하면 실행이 지연될 수 있습니다. 또한 각 사이트의 HTML 구조/접근 정책이 바뀌면 해당 파서를 수정해야 합니다. 확인할 수 없는 조회·추천 수치는 만들어내지 않습니다.

## 펨코 수집 진단

텔레그램을 보내거나 운영 상태 파일을 변경하지 않고 검사하려면:

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
python monitor.py --check-fmkorea
```

`Actions → FMKorea validation → Run workflow`에서도 동일한 검사와 회귀 테스트를 실행할 수 있습니다. 관련 코드가 main에 반영되거나 PR이 열리면 이 검사가 자동 실행됩니다.

초기 HTTP 430 뒤 정상 페이지로 이동하는 경우에는 실제 게시물이 나타날 때까지 기다립니다. 보안 화면의 “비정상 접속이 의심되어 차단” 문구가 계속 나타나면 접근 차단으로 기록하며 정상 수집으로 처리하지 않습니다. 이 경우 현재 실행 환경의 접근 허용 여부를 확인해야 하며, 코드 수정만으로 차단 해제를 보장할 수 없습니다. 접근이 허용된 실행 환경 또는 사이트 측 접근 허용이 필요합니다.

2026-10-14 GitHub 실행 검사에서 브라우저를 기다린 뒤에도 PC·모바일 모두 HTTP 430과 “사람인지 확인” 보안 화면이 남았습니다. 자동 수집 복구는 아직 확인되지 않았으며, 해당 상태는 수집 실패로 기록됩니다.

소스 수집에 실패하면 정상 수집한 소스의 보고와 상태 저장을 마친 뒤 종료 코드 1을 반환합니다. 시간별 워크플로는 실패 상태에서도 최신 진단을 저장하므로 Actions의 녹색 성공만 보고 수집이 정상이라고 판단하지 않게 됩니다.

회귀 테스트:

```bash
python -m unittest discover -s tests -v
TREND_RADAR_BROWSER_TESTS=1 python -m unittest discover -s tests -v
```

두 번째 명령은 Chromium 설치 후 실행하며, 로컬 HTTP 서버로 430 후 복구·지속 차단·빈 목록을 검사합니다. 실제 펨코 연결 여부는 별도의 수집 검사 결과로 확인합니다.

