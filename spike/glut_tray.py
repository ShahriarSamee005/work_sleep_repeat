"""Phase 9 spike — GLUT window + pystray tray icon coexistence test (OQ2).

Answers: can a freeglut window and a pystray tray icon live together on
Windows, with the tray menu driving the GLUT window, and does the window's X
button *hide* the window (so the app keeps running in the tray) instead of
killing the process?

Threading rule (important): GLUT is not thread-safe. The tray icon runs on its
own thread; its menu handlers only push a string onto a thread-safe queue.
A glutTimerFunc on the GLUT (main) thread drains the queue and performs the
actual GLUT calls. We never call GLUT from the tray thread.

Requires:  pip install pystray pillow   (Pillow already in the project)
           freeglut (already provided via PyOpenGL on this machine)

Run:  python spike/glut_tray.py
Then exercise the tray menu (Show / Hide / Toast / Quit) and click the window's
X button. Watch the console and spike/logs/tray.txt for what each action does.
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "logs" / "tray.txt"

# ---- command queue: tray thread -> GLUT thread -------------------------------
cmd_q: "queue.Queue[str]" = queue.Queue()

_window_visible = True
_should_quit = False
_tray_icon = None  # set once pystray icon is created


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---- imports that may be missing: fail with a clear message ------------------
try:
    from OpenGL.GLUT import (
        GLUT_ACTION_CONTINUE_EXECUTION,
        GLUT_ACTION_ON_WINDOW_CLOSE,
        GLUT_DOUBLE,
        GLUT_RGB,
        glutCloseFunc,
        glutCreateWindow,
        glutDisplayFunc,
        glutHideWindow,
        glutInit,
        glutInitDisplayMode,
        glutInitWindowSize,
        glutMainLoop,
        glutSetOption,
        glutShowWindow,
        glutSwapBuffers,
        glutTimerFunc,
    )
    from OpenGL.GL import glClear, glClearColor, GL_COLOR_BUFFER_BIT
except Exception as exc:  # pragma: no cover
    print(f"GLUT/OpenGL import failed: {exc}", file=sys.stderr)
    raise SystemExit(1)

try:
    import pystray
    from PIL import Image
except Exception as exc:  # pragma: no cover
    print(f"pystray/Pillow import failed: {exc}", file=sys.stderr)
    print("Install with:  pip install pystray pillow", file=sys.stderr)
    raise SystemExit(1)


# ---- GLUT callbacks (run on the main/GLUT thread only) -----------------------
def _display():
    glClearColor(0.12, 0.14, 0.22, 1.0)  # dark slate; changes to show redraws
    glClear(GL_COLOR_BUFFER_BIT)
    glutSwapBuffers()


def _on_close():
    """Window X button. With GLUT_ACTION_CONTINUE_EXECUTION this should return
    control to us rather than exiting the process. We try to hide instead and
    log exactly what we observe."""
    global _window_visible
    log("CLOSE callback fired (X button). Attempting glutHideWindow().")
    try:
        glutHideWindow()
        _window_visible = False
        log("glutHideWindow() returned — if the process is still alive and the "
            "tray icon remains, X=hide works.")
    except Exception as exc:
        log(f"glutHideWindow() raised: {exc}")


def _drain_queue(_value):
    """glutTimerFunc: run queued tray commands on the GLUT thread."""
    global _window_visible, _should_quit
    try:
        while True:
            cmd = cmd_q.get_nowait()
            log(f"GLUT thread handling command: {cmd}")
            if cmd == "show":
                glutShowWindow()
                _window_visible = True
            elif cmd == "hide":
                glutHideWindow()
                _window_visible = False
            elif cmd == "quit":
                _should_quit = True
                if _tray_icon is not None:
                    _tray_icon.stop()
                log("Quit requested — leaving GLUT main loop.")
                try:
                    from OpenGL.GLUT import glutLeaveMainLoop
                    glutLeaveMainLoop()
                except Exception:
                    # Fallback: hard exit if freeglut lacks glutLeaveMainLoop
                    import os
                    os._exit(0)
                return
    except queue.Empty:
        pass
    if not _should_quit:
        glutTimerFunc(50, _drain_queue, 0)


# ---- tray (runs on its own thread; only enqueues commands) -------------------
def _make_icon_image():
    # simple 64x64 two-tone square
    img = Image.new("RGB", (64, 64), (40, 44, 66))
    for x in range(16, 48):
        for y in range(16, 48):
            img.putpixel((x, y), (235, 200, 90))
    return img


def _tray_show(icon, item):
    log("TRAY menu: Show -> enqueue 'show'")
    cmd_q.put("show")


def _tray_hide(icon, item):
    log("TRAY menu: Hide -> enqueue 'hide'")
    cmd_q.put("hide")


def _tray_toast(icon, item):
    # notify() is a tray-thread operation (not GLUT), safe to call here.
    log("TRAY menu: Toast -> icon.notify()")
    try:
        icon.notify("Work•Sleep•Repeat spike", "Toast from the tray")
        log("icon.notify() returned without error.")
    except Exception as exc:
        log(f"icon.notify() raised: {exc}")


def _tray_quit(icon, item):
    log("TRAY menu: Quit -> enqueue 'quit'")
    cmd_q.put("quit")


def _run_tray():
    global _tray_icon
    menu = pystray.Menu(
        pystray.MenuItem("Show", _tray_show),
        pystray.MenuItem("Hide", _tray_hide),
        pystray.MenuItem("Toast", _tray_toast),
        pystray.MenuItem("Quit", _tray_quit),
    )
    icon = pystray.Icon("wsr_spike", _make_icon_image(), "WSR spike", menu)
    _tray_icon = icon
    log("Tray icon starting (run on tray thread).")
    icon.run()  # blocks this thread until icon.stop()
    log("Tray icon run() returned.")


def main() -> int:
    log("=== GLUT + pystray spike start ===")
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(360, 240)
    glutCreateWindow(b"WSR spike - GLUT + tray")
    # Ask freeglut to keep running when the window is closed, instead of exiting.
    glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION)
    glutDisplayFunc(_display)
    glutCloseFunc(_on_close)
    glutTimerFunc(50, _drain_queue, 0)

    tray_thread = threading.Thread(target=_run_tray, name="tray", daemon=True)
    tray_thread.start()

    log("Entering glutMainLoop(). Use the tray menu and the X button now.")
    try:
        glutMainLoop()
    except Exception as exc:
        log(f"glutMainLoop() raised/returned via exception: {exc}")
    log("glutMainLoop() returned (GLUT_ACTION_CONTINUE_EXECUTION path, or quit).")
    if _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception:
            pass
    log("=== spike end ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
