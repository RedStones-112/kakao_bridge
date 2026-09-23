# kakao_bridge

카카오톡 "나와의 채팅"을 다른 프로젝트에서 로컬 HTTP API로 읽고 쓸 수 있게 해주는 브릿지 서버.

**완전히 공식 API 기반이다.** 카카오톡 창을 띄우거나 UI를 자동화하지 않는다.

## 구조

카카오 공식 API는 "나에게 보내기"(쓰기)만 지원하고 대화 내용을 읽어올 방법이 없기 때문에,
읽기/쓰기를 서로 다른 공식 메커니즘으로 나눠서 구현했다.

- **쓰기**: 카카오 로그인(OAuth) + [카카오톡 메시지 API `/v2/api/talk/memo/default/send`](https://developers.kakao.com/docs/latest/ko/kakaotalk-message/rest-api#default-send-me) ("나에게 보내기")
- **읽기**: 카카오톡 **채널**(비즈니스 계정)을 하나 만들고, 여기에 **카카오 i 오픈빌더** 챗봇을 연결.
  채널로 메시지가 오면 카카오가 우리 스킬 서버(웹훅)로 POST해주고, 그 내용을 로컬에 저장했다가 API로 돌려준다.
  즉 "나와의 채팅"이 아니라 **별도로 만든 채널("PC Bridge")과 대화**하는 방식이다.

### 왜 읽기/쓰기가 서로 다른 대화방인가

`POST /send`는 "나와의 채팅"에, 채널로 보낸 메시지는 "PC Bridge" 채널방에 남아서 두 대화방이 분리되어 보인다.
하나로 합치려면 오픈빌더의 **이벤트 API**(봇이 먼저 메시지를 보내는 기능)를 써야 하는데, 이건 **사업자등록번호가
있는 정식 "비즈니스 인증"**이 필요해서 개인 프로젝트로는 통합이 불가능하다. 대신 `/send`로 나가는 메시지 앞에
`[PC Bridge]` 라벨을 붙여서 "나와의 채팅"에서도 브릿지가 보낸 메시지인지 구분되게 해뒀다.

## 사전 준비 (최초 1회, 카카오 디벨로퍼스/비즈니스 콘솔에서 수동 설정 필요)

1. [카카오 디벨로퍼스](https://developers.kakao.com)에서 앱 생성 (예: `톡_PC_Bridge`)
2. **카카오 로그인** 활성화
   - `앱 > 플랫폼 키 > REST API 키`에서 **카카오 로그인 리다이렉트 URI**에
     `http://localhost:8765/oauth/callback` 등록
   - `카카오 로그인 > 동의항목`에서 **카카오톡 메시지 전송(`talk_message`)** 스코프를 "선택 동의"로 설정
   - `앱 > 일반`에서 **앱 아이콘 등록** 후 **개인 개발자 비즈 앱 전환** (사업자번호 없이 본인인증으로 가능).
     talk_message 스코프가 실제로 토큰에 붙으려면 비즈 앱 전환이 필요하다.
3. [카카오비즈니스](https://business.kakao.com)에서 **카카오톡 채널** 생성 (검색용 ID 등)
   - 채널 홈에서 **채널 공개**, **검색 허용**은 필요할 때만 켜고 평소엔 꺼두는 걸 권장 (개인용 브릿지라 불특정 다수가 찾을 필요 없음)
   - **채널 관리 > 채팅 설정 > 채팅을 반드시 OFF로 유지할 것** — 이게 켜져 있으면 들어오는 메시지가
     챗봇이 아니라 사람이 받는 1:1 상담 채팅으로 가로채여서 웹훅이 전혀 호출되지 않는다 (실제로 겪은 문제).
4. [카카오 i 오픈빌더](https://i.kakao.com)에서 카카오톡 챗봇 생성
   - **스킬** 생성: URL에 `<외부에서 접근 가능한 주소>/kakao/skill` 등록
   - **시나리오 > 폴백 블록**에서 스킬을 위 스킬로 지정하고, 봇 응답을 "스킬데이터 사용"으로 변경
     (기본 텍스트 응답을 쓰면 우리 웹훅이 절대 호출되지 않는다)
   - **설정**에서 운영 채널을 위에서 만든 채널로 연결
   - **배포** 탭에서 전체 배포 실행

## 설치

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.env` 파일을 만든다 (gitignore됨, 절대 커밋하지 말 것):

```
KAKAO_REST_API_KEY=<REST API 키>
KAKAO_CLIENT_SECRET=<클라이언트 시크릿>
KAKAO_REDIRECT_URI=http://localhost:8765/oauth/callback
```

## 실행

```powershell
# 1) 서버 실행
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8765 --host 127.0.0.1

# 2) 외부(카카오 서버)에서 웹훅에 접근할 수 있도록 터널 실행 (예: cloudflared quick tunnel)
cloudflared tunnel --url http://localhost:8765
```

`cloudflared tunnel --url ...`로 뜨는 `https://xxxx.trycloudflare.com` 주소는 **재시작할 때마다 바뀐다.**
바뀔 때마다 오픈빌더의 스킬 URL(`.../kakao/skill`)을 새 주소로 다시 저장해야 웹훅이 계속 동작한다.
상시 운영하려면 고정 도메인이 있는 터널(예: named Cloudflare Tunnel, 자체 서버 배포 등)로 바꾸는 걸 권장.

### 최초 1회: 카카오 로그인 연동

브라우저에서 `http://127.0.0.1:8765/oauth/authorize` 열고 로그인 동의 → 자동으로 콜백 처리되며
토큰이 `app/.kakao_token.json`에 저장된다 (gitignore됨). 이후 만료 시 refresh_token으로 자동 갱신.

## API

- `GET /health` → `{"status": "ok"}`
- `POST /send` — "나에게 보내기"로 메시지 전송
  - body: `{"message": "보낼 내용"}`
  - 응답: `{"status": "ok"}`
- `GET /messages/last` — 채널로 마지막에 들어온 메시지 조회
  - 응답 예: `{"sender": "...", "text": "내용", "received_at": 1790165451.52}`
  - 메시지가 없으면 404
- `POST /kakao/skill` — 오픈빌더 스킬 서버(웹훅). 카카오 서버가 호출하는 용도이며 직접 호출할 일은 없다.

## 파일 구성

```
app/
  main.py           # FastAPI 서버, 엔드포인트 정의
  kakao_oauth.py     # 카카오 로그인 OAuth + "나에게 보내기" 메시지 API 래퍼
  kakao_channel.py   # 오픈빌더 웹훅으로 받은 메시지 저장/조회
  .kakao_token.json  # (gitignore) OAuth 토큰 저장 파일, 실행 중 자동 생성
  .last_inbound.json # (gitignore) 마지막으로 받은 메시지 저장 파일, 실행 중 자동 생성
.env                 # (gitignore) 카카오 앱 키/시크릿
```

## 주의사항

- `.env`와 `app/.kakao_token.json`에는 민감 정보(클라이언트 시크릿, refresh token)가 들어있다. 절대 커밋하지 말 것.
- 다른 프로젝트에서 쓰려면 이 서버(`:8765`)와 cloudflared 터널이 계속 떠 있어야 한다.
