"""main.py — এন্ট্রি পয়েন্ট: আর্গুমেন্ট পার্স, GLUT উইন্ডো ও মেইন লুপ (Phase 0)।"""

import argparse
import sys

from OpenGL.GL import glClear, glClearColor, GL_COLOR_BUFFER_BIT
from OpenGL.GLUT import (
    glutCreateWindow,
    glutDisplayFunc,
    glutInit,
    glutInitDisplayMode,
    glutInitWindowSize,
    glutKeyboardFunc,
    glutMainLoop,
    glutSwapBuffers,
    GLUT_DOUBLE,
    GLUT_RGBA,
)

import config

# glutLeaveMainLoop freeglut-এ আছে; না থাকলে fallback হিসেবে sys.exit ব্যবহার করব।
try:
    from OpenGL.GLUT import glutLeaveMainLoop
except ImportError:
    glutLeaveMainLoop = None

ESC = b"\x1b"  # কীবোর্ডের ESC কী-এর বাইট মান (ASCII 27)


def parse_args():
    # কী করছে: কমান্ড লাইন থেকে --me (samee/rifat) আর --offline ফ্ল্যাগ পড়ছে
    # কেন লাগছে: কে অ্যাপ চালাচ্ছে সেটা ঠিক করে; ভুল/ফাঁকা --me দিলে usage দেখিয়ে বন্ধ হয়
    # real world-এ এটা কোথায় দেখা যায়: git, python-এর মতো সব CLI টুল এভাবেই অপশন নেয়
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Work•Sleep•Repeat — shared Pro AI status board",
    )
    parser.add_argument(
        "--me",
        required=True,
        choices=("samee", "rifat"),
        help="who is running this app (samee or rifat)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="run without Supabase sync",
    )
    return parser.parse_args()


def hex_to_rgb01(hex_color):
    # কী করছে: "#231c2b"-এর মতো হেক্স রঙকে 0–1 রেঞ্জের (r, g, b) ফ্লোটে বদলাচ্ছে
    # কেন লাগছে: glClearColor 0–1 ফ্লোট চায়, কিন্তু আমরা রঙ config.py-তে হেক্স হিসেবে রাখি
    # real world-এ এটা কোথায় দেখা যায়: CSS/ডিজাইন টুল হেক্স কোডকে GPU-র ফ্লোট কালারে রূপান্তর করে
    # (Phase 1-এ এই কাজ pixel.hex_to_rgb-তে যাবে; তখন main এখান থেকে import করবে।)
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def display():
    # কী করছে: পুরো উইন্ডোকে ব্যাকগ্রাউন্ড রঙে মুছে দুই বাফার সোয়াপ করছে
    # কেন লাগছে: প্রতি ফ্রেমে আগের ছবি মুছে নতুন আঁকতে হয়; Phase 0-তে শুধু ফাঁকা রঙ দেখাই
    # real world-এ এটা কোথায় দেখা যায়: সব গেম/অ্যাপের রেন্ডার লুপ প্রতি ফ্রেমে স্ক্রিন ক্লিয়ার করে
    glClear(GL_COLOR_BUFFER_BIT)
    glutSwapBuffers()


def keyboard(key, x, y):
    # কী করছে: ESC চাপলে অ্যাপ বন্ধ করছে (x, y = মাউসের অবস্থান, এখন লাগছে না)
    # কেন লাগছে: ইউজারকে উইন্ডো বন্ধ করার সহজ উপায় দিতে হয়
    # real world-এ এটা কোথায় দেখা যায়: প্রায় সব ডেস্কটপ অ্যাপে ESC/বন্ধ বোতাম দিয়ে বের হওয়া যায়
    if key == ESC:
        if glutLeaveMainLoop is not None:
            glutLeaveMainLoop()   # freeglut-এ মেইন লুপ পরিষ্কারভাবে থামায়
        else:
            sys.exit(0)


def main():
    # কী করছে: আর্গুমেন্ট পড়ে GLUT চালু করে 1440x576 উইন্ডো খোলে ও কলব্যাক বাঁধে, তারপর মেইন লুপে ঢোকে
    # কেন লাগছে: এটাই অ্যাপের শুরু — উইন্ডো, রঙ ও ইনপুট হ্যান্ডলার সেট করে সবকিছু চালু করে
    # real world-এ এটা কোথায় দেখা যায়: সব GUI প্রোগ্রামের main()/entry point এভাবেই সেটআপ করে
    args = parse_args()  # ভুল --me হলে argparse এখানেই usage দেখিয়ে বেরিয়ে যায়

    glutInit([sys.argv[0]])                        # GLUT চালু; নিজের --me/--offline ফ্ল্যাগ GLUT-কে দিচ্ছি না
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)   # ডাবল বাফার + RGBA কালার মোড
    glutInitWindowSize(config.WINDOW_W, config.WINDOW_H)
    # glutCreateWindow C-লেভেলে bytes (c_char_p) চায়, তাই str টাইটেলকে UTF-8 bytes-এ encode করছি
    glutCreateWindow(config.WINDOW_TITLE.encode("utf-8"))

    r, g, b = hex_to_rgb01(config.OUTLINE)         # ব্যাকগ্রাউন্ড রঙ config থেকে (#231c2b)
    glClearColor(r, g, b, 1.0)

    glutDisplayFunc(display)                        # প্রতি ফ্রেমে display() ডাকবে
    glutKeyboardFunc(keyboard)                      # কী চাপলে keyboard() ডাকবে

    glutMainLoop()                                  # ইভেন্ট লুপ শুরু; ESC না চাপা পর্যন্ত চলবে


if __name__ == "__main__":
    main()
