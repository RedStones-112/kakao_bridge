"""현재 포그라월드(최상위) 창이 전체화면 앱인지 판단한다."""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def get_foreground_info():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

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
    user32.GetMonitorInfoW(monitor, ctypes.byref(mi))

    is_fullscreen = (
        rect.left <= mi.rcMonitor.left
        and rect.top <= mi.rcMonitor.top
        and rect.right >= mi.rcMonitor.right
        and rect.bottom >= mi.rcMonitor.bottom
    )
    return {
        "hwnd": hwnd,
        "title": title,
        "window_rect": (rect.left, rect.top, rect.right, rect.bottom),
        "monitor_rect": (mi.rcMonitor.left, mi.rcMonitor.top, mi.rcMonitor.right, mi.rcMonitor.bottom),
        "is_fullscreen": bool(is_fullscreen),
    }

if __name__ == "__main__":
    print(get_foreground_info())
