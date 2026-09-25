"""tools/snapshot.py — dev tool: main.display()-এর একটি ফ্রেম PNG-তে রেন্ডার করে (দৃশ্যমান লুপ ছাড়া)।

ব্যবহার:
    python tools/snapshot.py out.png [--samee idle|work] [--rifat idle|work] [--t 0.0]
--samee/--rifat দুই রুমের অবস্থা সেট করে; --t হলো নকল অ্যানিমেশন ঘড়ি (সেকেন্ড), টাইপিং frame যাচাইয়ে।
GLUT উইন্ডো তৈরি করে এক ফ্রেম আঁকে, ফ্রেমটি পড়ে PNG-তে সেভ করে, glutMainLoop-এ ঢোকে না।
Pillow লাগে (requirements-dev.txt)। এটি অ্যাপের অংশ নয়, শুধু যাচাইয়ের টুল।
"""

import argparse
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
    app.init_scene()                 # projection/blending + display list তৈরি (context লাগে)

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
    # কী করছে: আউটপুট পাথ ও অবস্থা/সময় আর্গুমেন্ট পড়ে অ্যাপের state সেট করে render_to_png ডাকে
    # কেন লাগছে: নির্দিষ্ট অবস্থা (idle/work) ও নির্দিষ্ট সময়ের (typing frame) ছবি তুলতে
    # real world-এ এটা কোথায় দেখা যায়: টেস্ট হার্নেস নির্দিষ্ট state সেট করে screenshot নেয়
    parser = argparse.ArgumentParser(prog="snapshot.py")
    parser.add_argument("out", help="output PNG path")
    parser.add_argument("--samee", choices=("idle", "work"), default="idle")
    parser.add_argument("--rifat", choices=("idle", "work"), default="idle")
    parser.add_argument("--t", type=float, default=0.0, help="fake animation clock (seconds)")
    args = parser.parse_args()

    app.samee_working = (args.samee == "work")   # অ্যাপের state সরাসরি সেট করি
    app.rifat_working = (args.rifat == "work")
    app._fake_time = args.t                       # ঘড়ি ফ্রিজ করি এই সময়ে

    render_to_png(args.out)
    print("wrote", os.path.abspath(args.out))
    if app.glutLeaveMainLoop is not None:
        app.glutLeaveMainLoop()


if __name__ == "__main__":
    main()
