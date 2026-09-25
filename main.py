"""main.py — এন্ট্রি পয়েন্ট: আর্গুমেন্ট পার্স, GLUT উইন্ডো, 2D প্রজেকশন ও মেইন লুপ (Phase 1)।"""

import argparse
import sys

from OpenGL.GL import (
    glBlendFunc,
    glClear,
    glClearColor,
    glEnable,
    glLoadIdentity,
    glMatrixMode,
    glPopMatrix,
    glPushMatrix,
    glTranslatef,
    glViewport,
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_MODELVIEW,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_PROJECTION,
    GL_SRC_ALPHA,
)
from OpenGL.GLU import gluOrtho2D
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
import room
from pixel import draw_rect, draw_sprite, hex_to_rgb
from sprites import HEAD_SLEEP, HEAD_SLEEP_COLORS

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


def init_gl():
    # কী করছে: ব্যাকগ্রাউন্ড রঙ, ভিউপোর্ট, 2D প্রজেকশন (y=0 উপরে) ও alpha blending সেট করছে
    # কেন লাগছে: gluOrtho2D গ্রিড কোঅর্ডিনেটকে স্ক্রিনে ম্যাপ করে; blending আলো/ছায়ায় স্বচ্ছতা দেয়
    # real world-এ এটা কোথায় দেখা যায়: প্রতিটি রেন্ডারারের init-এ ক্যামেরা/প্রজেকশন ও blend state সেট হয়
    r, g, b = hex_to_rgb(config.OUTLINE)                # ব্যাকগ্রাউন্ড রঙ config থেকে (#231c2b)
    glClearColor(r, g, b, 1.0)

    glViewport(0, 0, config.WINDOW_W, config.WINDOW_H)  # পুরো উইন্ডো জুড়ে আঁকা হবে
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, config.GRID_W, config.GRID_H, 0)      # left,right,bottom,top → y=0 উপরে (উল্টানো)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glEnable(GL_BLEND)                                   # স্বচ্ছতা চালু
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)   # স্বাভাবিক alpha blending সূত্র


def _draw_frame():
    # কী করছে: দৃশ্য এলাকার (x 0–191) চারপাশে ২-পিক্সেল OUTLINE ফ্রেম আঁকছে
    # কেন লাগছে: রুমগুলোর বাইরে একটি পরিষ্কার গাঢ় সীমানা দেয় (design §3)
    # real world-এ এটা কোথায় দেখা যায়: UI-তে কনটেন্ট এলাকার চারপাশে border/bezel
    t, w, h = config.FRAME_PX, config.SCENE_W, config.GRID_H
    draw_rect(0, 0, w, t, config.OUTLINE)          # উপরের বার
    draw_rect(0, h - t, w, t, config.OUTLINE)      # নিচের বার
    draw_rect(0, 0, t, h, config.OUTLINE)          # বাঁ বার
    draw_rect(w - t, 0, t, h, config.OUTLINE)      # ডান বার


def display():
    # কী করছে: স্ক্রিন ক্লিয়ার করে Samee-র রুম (translate 2,2) ও ঘুমন্ত মাথা এঁকে ফ্রেম বসিয়ে বাফার সোয়াপ করছে
    # কেন লাগছে: Phase 2-তে একটি স্ট্যাটিক idle রুম দেখানো; matrix push/pop রুম-লোকাল কোঅর্ডিনেট দেয়
    # real world-এ এটা কোথায় দেখা যায়: সিন গ্রাফ-এ প্রতিটি অবজেক্ট নিজের লোকাল স্পেসে এঁকে transform করা
    glClear(GL_COLOR_BUFFER_BIT)

    # ---- Samee-র রুম: translate(2, 2) matrix-এর ভেতরে (সব কোঅর্ডিনেট রুম-লোকাল) ----
    glPushMatrix()
    glTranslatef(config.SAMEE_ORIGIN[0], config.SAMEE_ORIGIN[1], 0)   # (2, 2, 0)
    room.draw_wall_and_floor()
    room.draw_decor()
    room.draw_rug((config.SAMEE_RUG, config.SAMEE_RUG_D, config.SAMEE_RUG_L))  # grey-blue রাগ
    room.draw_bed(messy=False)
    room.draw_desk()
    room.draw_chair()
    room.draw_screen(on=False)
    room.draw_lamp_shade(on=False, warn=False)
    draw_sprite(*config.HEAD_SLEEP_POS, HEAD_SLEEP, HEAD_SLEEP_COLORS)  # বালিশে ঘুমন্ত মাথা
    glPopMatrix()

    _draw_frame()   # ফ্রেম translate-এর বাইরে (গ্লোবাল কোঅর্ডিনেটে)

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
    # কী করছে: আর্গুমেন্ট পড়ে GLUT চালু করে উইন্ডো খোলে, init_gl() ডাকে, কলব্যাক বাঁধে ও মেইন লুপে ঢোকে
    # কেন লাগছে: এটাই অ্যাপের শুরু — উইন্ডো, প্রজেকশন, রঙ ও ইনপুট হ্যান্ডলার সেট করে সবকিছু চালু করে
    # real world-এ এটা কোথায় দেখা যায়: সব GUI প্রোগ্রামের main()/entry point এভাবেই সেটআপ করে
    args = parse_args()  # ভুল --me হলে argparse এখানেই usage দেখিয়ে বেরিয়ে যায়

    glutInit([sys.argv[0]])                          # GLUT চালু; নিজের ফ্ল্যাগ GLUT-কে দিচ্ছি না
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)     # ডাবল বাফার + RGBA কালার মোড
    glutInitWindowSize(config.WINDOW_W, config.WINDOW_H)
    # glutCreateWindow C-লেভেলে bytes (c_char_p) চায়, তাই str টাইটেলকে UTF-8 bytes-এ encode করছি
    glutCreateWindow(config.WINDOW_TITLE.encode("utf-8"))

    init_gl()                                         # প্রজেকশন, রঙ ও blending সেটআপ

    glutDisplayFunc(display)                          # প্রতি ফ্রেমে display() ডাকবে
    glutKeyboardFunc(keyboard)                        # কী চাপলে keyboard() ডাকবে

    glutMainLoop()                                    # ইভেন্ট লুপ শুরু; ESC না চাপা পর্যন্ত চলবে


if __name__ == "__main__":
    main()
