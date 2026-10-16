# 펨코 수집 접근 허용 요청

## 현재 상태

**미해결 — 전송 복구 또는 차단 해제 완료가 아닙니다.**

2026-10-16 16:07 KST 실행에서 PC·모바일 모두 HTTP 430과 사람 인증 미완료 화면이 남았습니다. 포텐 수집은 0개이며, 다른 세 소스만 정상 전송했습니다.

- [현재 운영 상태](../data/state.json)
- [실제 실패와 전송 기록](https://github.com/daeeunkim89-pixel/trend-radar/actions/runs/38864938979)
- 요청 주소: https://www.fmkorea.com/best 및 https://m.fmkorea.com/best
- 실제 게시물 목록을 받기 전에 보안 확인에서 멈춥니다. 특정 IP만의 문제라고 단정할 수 없습니다.
- 공식 자동수집 API 또는 정상 RSS의 제공 여부는 확인하지 못했습니다. 검색에 노출된 RSS 형태 URL도 정상 피드 응답으로 검증되지 않았습니다.
- 검색 결과를 실제 최신 포텐 TOP 10으로 대체하지 않았습니다.

## 필요한 확인

운영진에게 공개 목록의 자동수집 허용 여부, 공식 API·피드, 허용 빈도와 접근 승인 조건을 문의합니다. 허용된 연결 방식이 확인되면 수집기에 연결하고 실제 10개 글과 제공 가능한 반응 지표, 텔레그램 전송을 다시 검증해야 합니다. 별도 실행 환경이 필요하면 승인 조건에 맞춰 구성합니다.

공식 차단 안내는 잘못 차단된 요청에 대해 접근 주소·입력 내용 등과 함께 help@fmkorea.com으로 문의하도록 안내합니다.

참고: https://www.fmkorea.com/firewall_denied.html

## 발송 전 검토용 문의문

**아직 발송하지 않았습니다.** 현재 연결된 도구에는 메일 발송 기능이 없습니다.

[메일 앱에서 문의문 열기](mailto:help@fmkorea.com?subject=%ED%8F%AC%ED%85%90%20%EA%B3%B5%EA%B0%9C%20%EB%AA%A9%EB%A1%9D%20%EC%9E%90%EB%8F%99%EC%88%98%EC%A7%91%20%ED%97%88%EC%9A%A9%20%EB%B0%8F%20%EA%B3%B5%EC%8B%9D%20%EC%A0%9C%EA%B3%B5%20%EA%B2%BD%EB%A1%9C%20%EB%AC%B8%EC%9D%98&body=%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94.%20btp%20%EC%BD%98%ED%85%90%EC%B8%A0%20%EC%97%90%EB%94%94%ED%84%B0%EC%9A%A9%20%EC%86%8C%EC%9E%AC%20%EB%AA%A8%EB%8B%88%ED%84%B0%EB%A5%BC%20%EC%9A%B4%EC%98%81%ED%95%98%EA%B3%A0%20%EC%9E%88%EC%8A%B5%EB%8B%88%EB%8B%A4.%0A%0A%ED%8F%AC%ED%85%90%20%EB%AA%A9%EB%A1%9D%EC%97%90%EC%84%9C%201%EC%8B%9C%EA%B0%84%EB%A7%88%EB%8B%A4%20%EC%B5%9C%EB%8C%80%2010%EA%B0%9C%20%EA%B3%B5%EA%B0%9C%20%EA%B8%80%EC%9D%98%20%EC%A0%9C%EB%AA%A9%C2%B7%EC%9B%90%EB%AC%B8%20%EB%A7%81%ED%81%AC%EC%99%80%20%EC%A0%9C%EA%B3%B5%20%EA%B0%80%EB%8A%A5%ED%95%9C%20%EC%A1%B0%ED%9A%8C%C2%B7%EC%B6%94%EC%B2%9C%20%EC%A7%80%ED%91%9C%EB%A5%BC%20%EB%82%B4%EB%B6%80%20%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8%20%EC%86%8C%EC%9E%AC%ED%95%A8%EC%97%90%20%EB%AA%A8%EC%9C%BC%EA%B3%A0%EC%9E%90%20%ED%95%A9%EB%8B%88%EB%8B%A4.%20%EA%B2%8C%EC%8B%9C%EB%AC%BC%20%EC%A0%84%EB%AC%B8%C2%B7%EB%8C%93%EA%B8%80%20%EC%9B%90%EB%AC%B8%C2%B7%ED%9A%8C%EC%9B%90%EC%A0%95%EB%B3%B4%C2%B7%EC%82%AC%EC%A7%84%C2%B7%EC%98%81%EC%83%81%20%ED%8C%8C%EC%9D%BC%EC%9D%80%20%EC%88%98%EC%A7%91%ED%95%98%EC%A7%80%20%EC%95%8A%EC%9D%84%20%EA%B3%84%ED%9A%8D%EC%9E%85%EB%8B%88%EB%8B%A4.%0A%0A%ED%98%84%EC%9E%AC%20GitHub%20Actions%20%EC%8B%A4%ED%96%89%20%ED%99%98%EA%B2%BD%EC%97%90%EC%84%9C%20PC%C2%B7%EB%AA%A8%EB%B0%94%EC%9D%BC%20%EB%AA%A9%EB%A1%9D%EC%9D%B4%20%EB%AA%A8%EB%91%90%20HTTP%20430%EA%B3%BC%20%EC%82%AC%EB%9E%8C%20%EC%9D%B8%EC%A6%9D%20%EB%AF%B8%EC%99%84%EB%A3%8C%20%ED%99%94%EB%A9%B4%EC%9C%BC%EB%A1%9C%20%EC%9D%91%EB%8B%B5%ED%95%A9%EB%8B%88%EB%8B%A4.%0A%EC%9E%90%EB%8F%99%EC%88%98%EC%A7%91%20%ED%97%88%EC%9A%A9%20%EA%B0%80%EB%8A%A5%20%EC%97%AC%EB%B6%80%2C%20%EA%B6%8C%EC%9E%A5%ED%95%98%EB%8A%94%20%EA%B3%B5%EC%8B%9D%20API%2FRSS%20%EB%98%90%EB%8A%94%20%EC%A0%91%EA%B7%BC%20%EC%8A%B9%EC%9D%B8%20%EC%A0%88%EC%B0%A8%EC%99%80%20%EC%9A%94%EC%B2%AD%20%EC%A3%BC%EA%B8%B0%EB%A5%BC%20%EC%95%88%EB%82%B4%20%EB%B6%80%ED%83%81%EB%93%9C%EB%A6%BD%EB%8B%88%EB%8B%A4.%20%EA%B3%A0%EC%A0%95%20IP%20%EB%93%B1%EC%9D%98%20%EC%A1%B0%EA%B1%B4%EC%9D%B4%20%ED%95%84%EC%9A%94%ED%95%98%EB%A9%B4%20%EC%95%8C%EB%A0%A4%EC%A3%BC%EC%84%B8%EC%9A%94.%0A%0A%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8%3A%20https%3A%2F%2Fgithub.com%2Fdaeeunkim89-pixel%2Ftrend-radar%0A%EC%8B%A4%ED%96%89%20%EA%B8%B0%EB%A1%9D%3A%20https%3A%2F%2Fgithub.com%2Fdaeeunkim89-pixel%2Ftrend-radar%2Factions%2Fruns%2F38864938979%0A%0A%EA%B0%90%EC%82%AC%ED%95%A9%EB%8B%88%EB%8B%A4.)

받는 사람: help@fmkorea.com  
제목: 포텐 공개 목록 자동수집 허용 및 공식 제공 경로 문의

안녕하세요. btp 콘텐츠 에디터용 소재 모니터를 운영하고 있습니다.

포텐 목록에서 1시간마다 최대 10개 공개 글의 제목·원문 링크와 제공 가능한 조회·추천 지표를 내부 텔레그램 소재함에 모으고자 합니다. 게시물 전문·댓글 원문·회원정보·사진·영상 파일은 수집하지 않을 계획입니다.

현재 GitHub Actions 실행 환경에서 PC·모바일 목록이 모두 HTTP 430과 사람 인증 미완료 화면으로 응답합니다.
자동수집 허용 가능 여부, 권장하는 공식 API/RSS 또는 접근 승인 절차와 요청 주기를 안내 부탁드립니다. 고정 IP 등의 조건이 필요하면 알려주세요.

프로젝트: https://github.com/daeeunkim89-pixel/trend-radar
실행 기록: https://github.com/daeeunkim89-pixel/trend-radar/actions/runs/38864938979

감사합니다.
