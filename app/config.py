import os
import tempfile

# "나와의 채팅" 방의 실제 창 제목. 카카오톡에서 이 이름으로 표시되는 방을 찾아 사용한다.
ROOM_TITLE = os.environ.get("KAKAO_ROOM_TITLE", "메모장")

MAIN_WINDOW_TITLE = "카카오톡"
MAIN_WINDOW_CLASS = "EVA_Window_Dblclk"

EXPORT_DIR = os.path.join(tempfile.gettempdir(), "kakao_bridge_export")

# 전체화면 앱이 떠 있을 때 재시도 주기(초)
FULLSCREEN_RETRY_INTERVAL_SEC = 300
