# TREND RADAR — 폰만으로 설치

네이버 많이 본 뉴스 / 네이버 스포츠 / 디시 실베 / 펨코 포텐을 GitHub Actions가 약 5분 간격으로 확인하고, 이전 스냅샷 대비 급상승 후보를 텔레그램으로 보냅니다.

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
`Actions → Trend Radar → Run workflow`를 한 번 눌러 초기 스냅샷을 만듭니다.
그 뒤 예약 실행이 작동합니다. 첫 실행은 비교 대상이 없으므로 보통 알림이 없습니다.

## 중요
GitHub Actions의 `schedule`은 최소 5분 표현을 지원하지만 혼잡 시 실행이 지연될 수 있어 정확한 실시간 5분 보장은 아닙니다. 또한 각 사이트의 HTML 구조/접근 정책이 바뀌면 해당 파서를 수정해야 합니다. 확인할 수 없는 조회·추천 수치는 만들어내지 않습니다.
