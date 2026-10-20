"""Phase 9 spike — FALLBACK window layer test (OQ2), only if glut_tray.py fails.

Repeats the GLUT coexistence test with a pyglet window, and confirms that the
existing PyOpenGL immediate-mode drawing from phases 0-8 (glBegin/glVertex)
still renders inside a pyglet GL context — so swapping the window layer would
not force a rewrite of pixel.py / room.py / character.py etc.

Threading rule is the same: the tray runs on its own thread and only enqueues
commands; pyglet.clock drains the queue and does all window/GL work on the
main thread.

pyglet (unlike GLUT) makes hide/show and intercepting the close button easy:
  * window.set_visible(True/False)
  * on_close handler returns True to cancel the default (which would exit)

Requires:  pip install pyglet pystray pillow

Run:  python spike/pyglet_tray.py
"""

from __future__ import annotations

import queue
import sys
import threading
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "logs" / "tray_pyglet.txt"
cmd_q: "queue.Queue[str]" = queue.Queue()
_tray_icon = None


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


try:
    import pyglet
    from pyglet.gl import (
        glBegin,
        glClear,
        glClearColor,
        glColor3f,
        glEnd,
        glVertex2f,
        GL_COLOR_BUFFER_BIT,
        GL_QUADS,
    )
except Exception as exc:  # pragma: no cover
    print(f"pyglet import failed: {exc}", file=sys.stderr)
    print("Install with:  pip install pyglet", file=sys.stderr)
    raise SystemExit(1)

try:
    import pystray
    from PIL import Image
except Exception as exc:  # pragma: no cover
    print(f"pystray/Pillow import failed: {exc}", file=sys.stderr)
    print("Install with:  pip install pystray pillow", file=sys.stderr)
    raise SystemExit(1)


window = pyglet.window.Window(360, 240, caption="WSR spike - pyglet + tray",
                              visible=True)


@window.event
def on_draw():
    glClearColor(0.12, 0.14, 0.22, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    # Legacy immediate-mode quad — the same calls phases 0-8 use.
    glColor3f(0.92, 0.78, 0.35)
    glBegin(GL_QUADS)
    glVertex2f(120, 80)
    glVertex2f(240, 80)
    glVertex2f(240, 160)
    glVertex2f(120, 160)
    glEnd()


@window.event
def on_close():
    log("on_close fired (X button). Hiding window, cancelling default exit.")
    window.set_visible(False)
    return True  # handled -> pyglet does NOT close/exit


def _drain_queue(_dt):
    try:
        while True:
            cmd = cmd_q.get_nowait()
            log(f"main thread handling command: {cmd}")
            if cmd == "show":
                window.set_visible(True)
                window.activate()
            elif cmd == "hide":
                window.set_visible(False)
            elif cmd == "quit":
                if _tray_icon is not None:
                    _tray_icon.stop()
                log("Quit -> pyglet.app.exit()")
                pyglet.app.exit()
                return
    except queue.Empty:
        pass


def _make_icon_image():
    img = Image.new("RGB", (64, 64), (40, 44, 66))
    for x in range(16, 48):
        for y in range(16, 48):
            img.putpixel((x, y), (235, 200, 90))
    return img


def _run_tray():
    global _tray_icon
    menu = pystray.Menu(
        pystray.MenuItem("Show", lambda i, it: (log("TRAY Show"), cmd_q.put("show"))),
        pystray.MenuItem("Hide", lambda i, it: (log("TRAY Hide"), cmd_q.put("hide"))),
        pystray.MenuItem("Toast", lambda i, it: _toast(i)),
        pystray.MenuItem("Quit", lambda i, it: (log("TRAY Quit"), cmd_q.put("quit"))),
    )
    icon = pystray.Icon("wsr_spike_pyglet", _make_icon_image(), "WSR spike", menu)
    _tray_icon = icon
    log("Tray icon starting (tray thread).")
    icon.run()
    log("Tray icon run() returned.")


def _toast(icon):
    log("TRAY Toast -> icon.notify()")
    try:
        icon.notify("Work•Sleep•Repeat spike", "Toast from the tray")
        log("icon.notify() returned.")
    except Exception as exc:
        log(f"icon.notify() raised: {exc}")


def main() -> int:
    log("=== pyglet + pystray spike start ===")
    threading.Thread(target=_run_tray, name="tray", daemon=True).start()
    pyglet.clock.schedule_interval(_drain_queue, 0.05)
    log("Entering pyglet.app.run(). Use the tray menu and the X button now.")
    pyglet.app.run()
    log("pyglet.app.run() returned.")
    if _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception:
            pass
    log("=== spike end ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
