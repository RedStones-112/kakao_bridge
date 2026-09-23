import sys
import time
from pywinauto.application import Application

HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else 199564
OUT = sys.argv[2] if len(sys.argv) > 2 else "shot.png"

app = Application(backend="win32").connect(handle=HANDLE)
w = app.window(handle=HANDLE)
w.restore()
w.set_focus()
time.sleep(0.5)
img = w.capture_as_image()
img.save(OUT)
print("saved", OUT, img.size)
