# kakao_bridge

카카오톡 데스크톱 앱의 "나와의 채팅"(메모장) 방을 다른 프로젝트에서 로컬 HTTP API로 읽고 쓸 수 있게 해주는 브릿지 서버.

카카오 공식 API는 "나에게 보내기"(쓰기)만 지원하고 대화 내용을 읽어올 방법이 없기 때문에, 이 프로젝트는
Windows UI 자동화(pywinauto)로 PC 카카오톡 앱을 직접 조작한다. 메시지 목록 컨트롤은 완전히 커스텀 렌더링이라
화면에서 텍스트를 직접 읽을 수 없어서, 읽기는 카카오톡의 "대화 내보내기" 기능(.txt 저장)을 이용해 마지막
메시지만 파싱해서 돌려준다.

## 사전 준비

1. 카카오톡 PC 앱이 설치되어 있고 로그인되어 있어야 한다.
2. **"나와의 채팅" 방을 한 번은 직접 열어야 한다.** (내 프로필 클릭 → 나에게 채팅하기 등) 그래야 채팅
   목록에 나타나서 이후 검색으로 찾을 수 있다.
3. 기본으로는 방 이름이 **"메모장"**이라고 가정한다. 다르면 `KAKAO_ROOM_TITLE` 환경 변수로 바꿀 수 있다.

## 설치

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> 참고: 카카오톡은 32비트 프로세스라서, 파이썬이 어떤 비트수여도(64비트 포함) 동작은 하지만
> `pywinauto`가 경고를 출력할 수 있다. 무시해도 된다.
> venv를 만드는 python이 MSYS2/UCRT64 등 특수 빌드면 `pydantic-core` 같은 컴파일 패키지의 wheel을
> 못 찾을 수 있다. 이 경우 `C:\Users\<사용자>\AppData\Local\Programs\Python\Python3xx\python.exe` 같은
> 공식 Windows 배포판 파이썬으로 venv를 새로 만들어야 한다.

## 실행

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8765 --host 127.0.0.1
```

## API

### `POST /send` — 메시지 전송

```json
{ "message": "안녕", "wait_for_fullscreen": true }
```

- `wait_for_fullscreen` (기본 true): 전체화면 앱(게임 등)이 떠 있으면 카카오톡 창을 조작할 수 없다.
  `true`면 5분 간격으로 재확인하며 전체화면이 끝날 때까지 요청을 대기시킨다(계속 열려있는 요청).
  `false`면 즉시 `503`을 반환한다.

응답: `{"status": "ok"}`

### `GET /messages/last` — 마지막 메시지 읽기

쿼리 파라미터: `wait_for_fullscreen` (기본 true, 위와 동일)

응답 예:
```json
{"sender": "이재혁", "time": "오후 12:49", "text": "연속 테스트\n두번째 줄"}
```

메시지가 하나도 없으면 `404`.

## 동작 방식 / 주의사항

- **창 노출**: 전체화면 앱이 없으면 카카오톡 창을 그냥 띄워서(포커스를 가져와서) 작업한다. 일반
  창 모드 앱(게임 로비, 브라우저 등) 위에서는 카카오톡 창이 잠깐 보였다가 사라질 수 있다.
  전체화면 앱이 감지되면 작업을 미루고 5분마다 재시도한다 (`app/config.py`의
  `FULLSCREEN_RETRY_INTERVAL_SEC`로 조절 가능).
- **읽기는 "대화 내보내기"(Ctrl+S)를 이용한다.** 매 호출마다 `%TEMP%\kakao_bridge_export`에 임시
  .txt를 저장했다가 마지막 메시지만 파싱하고 바로 삭제한다. 대화방이 매우 크면 내보내기 자체가
  조금 걸릴 수 있다.
- 카카오톡의 채팅방 목록/메시지 목록 UI는 접근성 API(UI Automation/MSAA)로 텍스트를 전혀 읽을 수
  없는 완전 커스텀 컨트롤이라, 좌표 기반 클릭에 의존하는 부분이 있다 (검색 결과 더블클릭, 내보내기
  완료 팝업의 "확인" 버튼 등). 카카오톡 클라이언트 UI가 크게 바뀌면 `app/kakao_controller.py`의
  좌표값을 다시 잡아야 할 수 있다.
- `tools/inspect_ui.py`, `tools/screenshot.py`, `tools/check_fullscreen.py`는 UI 구조를 다시
  조사하거나 디버깅할 때 쓰는 보조 스크립트다.

## 설정

`app/config.py` 또는 환경 변수로 조절:

- `KAKAO_ROOM_TITLE` (기본 `메모장`): "나와의 채팅" 방의 실제 제목.
