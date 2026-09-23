"""
KakaoTalk UI Automation 탐색 도구.

카카오톡이 실행 중이고 로그인된 상태에서 실행하면,
열려있는 창 목록과 각 창의 컨트롤 트리를 출력해준다.
이 출력을 보고 kakao_controller.py의 selector를 맞춘다.

사용법:
    python tools/inspect_ui.py            # 열려있는 모든 창 제목 나열
    python tools/inspect_ui.py "창제목일부"   # 해당 창의 전체 컨트롤 트리 출력
"""
import sys
from pywinauto import Desktop
from pywinauto.application import Application


def list_windows(backend="uia"):
    print(f"=== 현재 열려있는 창 목록 (backend={backend}) ===")
    for w in Desktop(backend=backend).windows():
        try:
            title = w.window_text()
            cls = w.friendly_class_name()
            if title.strip():
                print(f"- title={title!r} class={cls!r} handle={w.handle}")
        except Exception:
            continue


def dump_window(title_substr, backend="uia", depth=12, handle=None):
    if handle:
        w = Desktop(backend=backend).window(handle=int(handle))
        windows = [w]
    else:
        windows = Desktop(backend=backend).windows(title_re=f".*{title_substr}.*")
    if not windows:
        print(f"'{title_substr}' 포함 창을 찾지 못함 (backend={backend})")
        return
    for w in windows:
        title = w.window_text()
        print(f"=== 창: {title!r} (backend={backend}, handle={w.handle}) ===")
        app = Application(backend=backend).connect(handle=w.handle)
        spec = app.window(handle=w.handle)
        spec.print_control_identifiers(depth=depth)


if __name__ == "__main__":
    args = sys.argv[1:]
    backend = "uia"
    handle = None
    if "--backend" in args:
        i = args.index("--backend")
        backend = args[i + 1]
        del args[i:i + 2]
    if "--handle" in args:
        i = args.index("--handle")
        handle = args[i + 1]
        del args[i:i + 2]
    if args:
        dump_window(args[0], backend=backend, handle=handle)
    else:
        list_windows(backend=backend)
