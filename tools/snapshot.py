"""tools/snapshot.py — dev tool: main.display()-এর একটি ফ্রেম PNG-তে রেন্ডার করে (দৃশ্যমান লুপ ছাড়া)।

ব্যবহার:
    python tools/snapshot.py out.png
GLUT উইন্ডো তৈরি করে এক ফ্রেম আঁকে, ফ্রেমটি পড়ে PNG-তে সেভ করে, glutMainLoop-এ ঢোকে না।
Pillow লাগে (requirements-dev.txt)। এটি অ্যাপের অংশ নয়, শুধু যাচাইয়ের টুল।
"""

import os
import sys

# tools/ এর প্যারেন্ট (প্রজেক্ট রুট) import path-এ যোগ করছি, যাতে main/config পাওয়া যায়
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from OpenGL.GL import (
    glPixelStorei,
    glReadBuffer,
    glReadPixels,
    GL_FRONT,
    GL_PACK_ALIGNMENT,
    GL_RGB,
    GL_UNSIGNED_BYTE,
)
from OpenGL.GLUT import (
    glutCreateWindow,
    glutDisplayFunc,
    glutInit,
    glutInitDisplayMode,
    glutInitWindowSize,
    glutMainLoopEvent,
    GLUT_DOUBLE,
    GLUT_RGBA,
)
from PIL import Image

import config
import main as app


def render_to_png(path):
    # কী করছে: একটি GLUT উইন্ডো/কনটেক্সট বানিয়ে main.display() একবার চালিয়ে front buffer পড়ে PNG সেভ করছে
    # কেন লাগছে: প্রতি ফেজে চোখে না দেখে ছবি মিলিয়ে যাচাই করা যায়; মেইন লুপ ছাড়া তাই ব্লক করে না
    # real world-এ এটা কোথায় দেখা যায়: গেম/গ্রাফিক্সে অটোমেটেড "render test"/screenshot regression
    glutInit([sys.argv[0]])
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(config.WINDOW_W, config.WINDOW_H)
    glutCreateWindow(b"snapshot")
    glutDisplayFunc(app.display)     # অ্যাপের আসল display() ব্যবহার করছি
    app.init_gl()

    for _ in range(3):              # উইন্ডো realize হতে কয়েকটি ইভেন্ট পাম্প
        glutMainLoopEvent()
    app.display()                  # এক ফ্রেম আঁকে ও swap করে → front buffer-এ ফ্রেমটি থাকে
    for _ in range(2):
        glutMainLoopEvent()

    glReadBuffer(GL_FRONT)         # swap-এর পর আঁকা ছবি front buffer-এ
    glPixelStorei(GL_PACK_ALIGNMENT, 1)
    data = glReadPixels(0, 0, config.WINDOW_W, config.WINDOW_H, GL_RGB, GL_UNSIGNED_BYTE)
    if hasattr(data, "tobytes"):
        data = data.tobytes()

    img = Image.frombytes("RGB", (config.WINDOW_W, config.WINDOW_H), bytes(data))
    img = img.transpose(Image.FLIP_TOP_BOTTOM)   # GL origin নিচে-বাঁয়ে → ছবির origin উপরে-বাঁয়ে
    img.save(path)
    return img


def main():
    # কী করছে: কমান্ড লাইন থেকে আউটপুট পাথ নিয়ে render_to_png ডাকে ও পরিষ্কারভাবে বের হয়
    # কেন লাগছে: `python tools/snapshot.py out.png` কল করার এন্ট্রি পয়েন্ট
    # real world-এ এটা কোথায় দেখা যায়: যেকোনো CLI স্ক্রিপ্টের main() যেভাবে আর্গুমেন্ট নেয়
    out = sys.argv[1] if len(sys.argv) > 1 else "out.png"
    render_to_png(out)
    print("wrote", os.path.abspath(out))
    if app.glutLeaveMainLoop is not None:
        app.glutLeaveMainLoop()


if __name__ == "__main__":
    main()
