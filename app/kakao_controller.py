import ctypes
from ctypes import wintypes
import os
import re
import time
import uuid

from pywinauto import Desktop

from app.config import (
    EXPORT_DIR,
    FULLSCREEN_RETRY_INTERVAL_SEC,
    MAIN_WINDOW_CLASS,
    MAIN_WINDOW_TITLE,
    ROOM_TITLE,
)

user32 = ctypes.windll.user32

# 대화 내용 줄 패턴: "[발신자] [오전/오후 H:MM] 내용"
_MESSAGE_LINE_RE = re.compile(r"^\[(?P<sender>.+?)\] \[(?P<time>(오전|오후) \d{1,2}:\d{2})\] (?P<text>.*)$")

_SPECIAL_KEY_CHARS = set("+^%~(){}")


def _escape_for_type_keys(text: str) -> str:
    return "".join(f"{{{c}}}" if c in _SPECIAL_KEY_CHARS else c for c in text)


class KakaoBridgeError(RuntimeError):
    pass


class FullscreenBlockedError(KakaoBridgeError):
    """전체화면 앱(게임 등)이 떠 있어 작업을 진행할 수 없을 때"""


def _is_foreground_fullscreen() -> bool:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False

    monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(mi)):
        return False

    return (
        rect.left <= mi.rcMonitor.left
        and rect.top <= mi.rcMonitor.top
        and rect.right >= mi.rcMonitor.right
        and rect.bottom >= mi.rcMonitor.bottom
    )


def _wait_until_not_fullscreen(max_wait_sec: float | None = None) -> None:
    """전체화면 앱이 떠 있는 동안 주기적으로 재확인하며 대기한다."""
    waited = 0.0
    while _is_foreground_fullscreen():
        if max_wait_sec is not None and waited >= max_wait_sec:
            raise FullscreenBlockedError(
                "전체화면 앱이 실행 중이라 카카오톡 작업을 진행할 수 없습니다."
            )
        time.sleep(FULLSCREEN_RETRY_INTERVAL_SEC)
        waited += FULLSCREEN_RETRY_INTERVAL_SEC


def _find_main_window():
    spec = Desktop(backend="win32").window(
        title=MAIN_WINDOW_TITLE, class_name=MAIN_WINDOW_CLASS, top_level_only=True
    )
    if not spec.exists(timeout=5):
        raise KakaoBridgeError(
            "카카오톡 메인 창을 찾을 수 없습니다. 카카오톡이 실행 중이고 로그인되어 있는지 확인하세요."
        )
    spec.restore()
    spec.set_focus()
    time.sleep(0.3)
    return spec


def _find_room_window(timeout: float = 1.0):
    spec = Desktop(backend="win32").window(title=ROOM_TITLE, top_level_only=True)
    if not spec.exists(timeout=timeout):
        return None
    spec.restore()
    spec.set_focus()
    time.sleep(0.2)
    return spec


def _open_room_via_search(main_win):
    main_win.click_input(coords=(280, 57))
    time.sleep(0.4)
    main_win.type_keys("^a{DELETE}")
    time.sleep(0.2)
    main_win.type_keys(ROOM_TITLE, with_spaces=True)
    time.sleep(1.0)
    main_win.double_click_input(coords=(150, 167))
    time.sleep(1.0)

    room = _find_room_window(timeout=5)
    if room is None:
        raise KakaoBridgeError(
            f"'{ROOM_TITLE}' 채팅방을 열지 못했습니다. 카카오톡에서 해당 방을 한 번 직접 열어 "
            "채팅 목록에 나타나게 해주세요."
        )
    return room


def _open_room():
    room = _find_room_window()
    if room is not None:
        return room
    main_win = _find_main_window()
    return _open_room_via_search(main_win)


def _find_export_done_popup():
    """'대화 내보내기 완료' 팝업은 타이틀이 비어있을 때가 있어 제목으로는 믿을 수 없다.
    크기로 식별한다 (대략 300x227)."""
    for w in Desktop(backend="win32").windows(class_name="EVA_Window_Dblclk", top_level_only=True):
        try:
            rect = w.rectangle()
        except Exception:
            continue
        width, height = rect.width(), rect.height()
        if 280 <= width <= 320 and 205 <= height <= 250:
            return w
    return None


def _dismiss_stale_export_dialog():
    """이전 호출에서 닫지 못하고 남은 '대화 내보내기 완료' 팝업이 있으면 닫는다."""
    for _ in range(10):
        popup = _find_export_done_popup()
        if popup is None:
            return
        popup.click_input(coords=(225, 178))
        time.sleep(0.5)


def _wait_enabled(win, timeout: float = 5.0):
    """윈도우가 다른 대화상자에 의해 비활성화된 상태가 풀릴 때까지 잠시 기다린다."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if user32.IsWindowEnabled(win.handle):
            return
        _dismiss_stale_export_dialog()
        time.sleep(0.3)
    raise KakaoBridgeError(
        "카카오톡 창이 다른 대화상자에 의해 막혀 있어 작업을 진행할 수 없습니다."
    )


def send_message(text: str, max_wait_sec: float | None = None) -> None:
    """'나와의 채팅' 방에 메시지를 전송한다."""
    _wait_until_not_fullscreen(max_wait_sec)
    _dismiss_stale_export_dialog()
    room = _open_room()
    _wait_enabled(room)
    edit = room.child_window(class_name="RICHEDIT50W")
    edit.set_focus()
    time.sleep(0.2)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            edit.type_keys("+{ENTER}")  # Shift+Enter = 메시지 내 줄바꿈 (Enter만 누르면 바로 전송됨)
        if line:
            edit.type_keys(_escape_for_type_keys(line), with_spaces=True)
    time.sleep(0.2)
    edit.type_keys("{ENTER}")
    time.sleep(0.3)


def _parse_last_message(export_text: str):
    lines = export_text.splitlines()
    last_start = None
    for i, line in enumerate(lines):
        if _MESSAGE_LINE_RE.match(line):
            last_start = i
    if last_start is None:
        return None

    m = _MESSAGE_LINE_RE.match(lines[last_start])
    body_lines = [m.group("text")]
    for line in lines[last_start + 1 :]:
        if line.startswith("---------------"):
            break
        body_lines.append(line)
    while body_lines and body_lines[-1] == "":
        body_lines.pop()

    return {
        "sender": m.group("sender"),
        "time": m.group("time"),
        "text": "\n".join(body_lines),
    }


def read_last_message(max_wait_sec: float | None = None):
    """'나와의 채팅' 방을 .txt로 내보내어 마지막 메시지를 읽는다."""
    _wait_until_not_fullscreen(max_wait_sec)
    _dismiss_stale_export_dialog()
    room = _open_room()
    _wait_enabled(room)

    os.makedirs(EXPORT_DIR, exist_ok=True)
    export_path = os.path.join(EXPORT_DIR, f"export_{uuid.uuid4().hex}.txt")

    room.set_focus()
    time.sleep(0.2)
    room.type_keys("^s")
    time.sleep(0.5)

    save_dlg_spec = Desktop(backend="win32").window(title="다른 이름으로 저장", top_level_only=True)
    if not save_dlg_spec.exists(timeout=5):
        raise KakaoBridgeError("'대화 내보내기' 저장 대화상자를 열지 못했습니다.")

    filename_edit = save_dlg_spec.child_window(class_name="Edit", found_index=0)
    filename_edit.set_edit_text(export_path)
    time.sleep(0.2)
    save_btn = save_dlg_spec.child_window(title="저장(&S)", class_name="Button")
    save_btn.click_input()

    # "대화 내보내기 완료" 팝업은 EVA 프레임워크의 커스텀 드로잉이라 자식 컨트롤이 없다.
    # 확인 버튼 위치를 고정 좌표로 클릭해야 한다.
    time.sleep(0.5)  # 진행률 100% 도달 및 버튼 활성화 대기
    _dismiss_stale_export_dialog()

    for _ in range(20):
        if os.path.exists(export_path):
            break
        time.sleep(0.3)
    else:
        raise KakaoBridgeError("대화 내보내기 결과 파일을 찾지 못했습니다.")

    with open(export_path, encoding="utf-8") as f:
        content = f.read()

    try:
        os.remove(export_path)
    except OSError:
        pass

    return _parse_last_message(content)
