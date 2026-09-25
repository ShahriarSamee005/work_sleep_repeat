"""main.py — এন্ট্রি পয়েন্ট: আর্গুমেন্ট পার্স, GLUT উইন্ডো, দুই রুম, ডিভাইডার, নাম লেবেল ও মেইন লুপ (Phase 3)।"""

import argparse
import sys
import time

from OpenGL.GL import (
    glBlendFunc,
    glCallList,
    glClear,
    glClearColor,
    glEnable,
    glLoadIdentity,
    glMatrixMode,
    glPopMatrix,
    glPushMatrix,
    glScalef,
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
    glutBitmapWidth,
    glutCreateWindow,
    glutDisplayFunc,
    glutIdleFunc,
    glutInit,
    glutInitDisplayMode,
    glutInitWindowSize,
    glutKeyboardFunc,
    glutMainLoop,
    glutPostRedisplay,
    glutSwapBuffers,
    GLUT_BITMAP_9_BY_15,
    GLUT_DOUBLE,
    GLUT_RGBA,
)

import config
import room
from pixel import draw_rect, draw_sprite, draw_text, hex_to_rgb
from sprites import HEAD_SLEEP, HEAD_SLEEP_COLORS

# glutLeaveMainLoop freeglut-এ আছে; না থাকলে fallback হিসেবে sys.exit ব্যবহার করব।
try:
    from OpenGL.GLUT import glutLeaveMainLoop
except ImportError:
    glutLeaveMainLoop = None

ESC = b"\x1b"                     # কীবোর্ডের ESC কী-এর বাইট মান (ASCII 27)
LABEL_FONT = GLUT_BITMAP_9_BY_15  # নাম লেবেলের ফন্ট

# FPS কাউন্টার state (Phase 10-এ পুরো কাউন্টার সরিয়ে ফেলব)
_fps_count = 0
_fps_t0 = None


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


def init_scene():
    # কী করছে: GL state সেট করে (init_gl) তারপর রুমের display list গুলো তৈরি করছে
    # কেন লাগছে: display list বানাতে GL কনটেক্সট লাগে; উইন্ডো তৈরির পর একবারই এটি ডাকা হয়
    # real world-এ এটা কোথায় দেখা যায়: গেম ইঞ্জিনের "assets GPU-তে আপলোড" ধাপ, লুপ শুরুর আগে
    init_gl()
    room.build_room_lists()


def _draw_room(rug_name, translate_x, mirror):
    # কী করছে: এক রুম আঁকছে — matrix push করে translate (ও Rifat হলে reflect), cached list call,
    #           তারপর dynamic অংশ (স্ক্রিন, ল্যাম্প শেড, ঘুমন্ত মাথা) আঁকে, শেষে pop
    # কেন লাগছে: দুই রুমই একই কোড ব্যবহার করে; শুধু transform আলাদা (এটাই reflection technique)
    # real world-এ এটা কোথায় দেখা যায়: সিন গ্রাফে একই মডেল ভিন্ন transform-এ বারবার আঁকা (instancing)
    glPushMatrix()
    glTranslatef(translate_x, config.RIFAT_ORIGIN[1], 0)  # y=2 দুই রুমেই এক
    if mirror:
        glScalef(-1, 1, 1)                                # অনুভূমিক প্রতিফলন (reflection)
    glCallList(room.ROOM_LISTS[(rug_name, False)])        # neat (কেউ বিছানায়) স্ট্যাটিক রুম
    room.draw_screen(on=False)                            # dynamic — list-এ নেই
    room.draw_lamp_shade(on=False, warn=False)            # dynamic — list-এ নেই
    draw_sprite(*config.HEAD_SLEEP_POS, HEAD_SLEEP, HEAD_SLEEP_COLORS)  # dynamic — list-এ নেই
    glPopMatrix()


def _draw_frame():
    # কী করছে: দৃশ্য এলাকার (x 0–191) চারপাশে ২-পিক্সেল OUTLINE ফ্রেম আঁকছে
    # কেন লাগছে: রুমগুলোর বাইরে একটি পরিষ্কার গাঢ় সীমানা দেয় (design §3)
    # real world-এ এটা কোথায় দেখা যায়: UI-তে কনটেন্ট এলাকার চারপাশে border/bezel
    t, w, h = config.FRAME_PX, config.SCENE_W, config.GRID_H
    draw_rect(0, 0, w, t, config.OUTLINE)          # উপরের বার
    draw_rect(0, h - t, w, t, config.OUTLINE)      # নিচের বার
    draw_rect(0, 0, t, h, config.OUTLINE)          # বাঁ বার
    draw_rect(w - t, 0, t, h, config.OUTLINE)      # ডান বার


def _draw_divider():
    # কী করছে: দুই রুমের মাঝে x95 ও x96 কলামে দুটি ভিন্ন রঙের ১-পিক্সেল লাইন আঁকছে
    # কেন লাগছে: দুই রুমকে চোখে আলাদা করতে; গ্লোবাল কোঅর্ডিনেটে (কোনো রুম transform ছাড়া)
    # real world-এ এটা কোথায় দেখা যায়: split-screen গেমে দুই ভিউয়ের মাঝের বিভাজক রেখা
    draw_rect(config.DIVIDER_X, config.DIVIDER_Y, 1, config.DIVIDER_H, config.DIVIDER_L)
    draw_rect(config.DIVIDER_X + 1, config.DIVIDER_Y, 1, config.DIVIDER_H, config.DIVIDER_R)


def _draw_centered_text(cx, y, text, color, font):
    # কী করছে: cx-কে কেন্দ্র ধরে text-এর প্রস্থ (window px) মেপে গ্রিড এককে বাঁয়ে সরিয়ে আঁকছে
    # কেন লাগছে: নাম লেবেল রাগের নিচে ঠিক মাঝ বরাবর বসাতে হয়
    # real world-এ এটা কোথায় দেখা যায়: UI-তে টেক্সট center-align করা
    width_px = sum(glutBitmapWidth(font, ord(c)) for c in text)
    start_x = cx - (width_px / config.PIXEL) / 2.0
    draw_text(start_x, y, text, color, font)


def _draw_labels():
    # কী করছে: "Samee" ও "Rifat" নাম দুই রাগের নিচে আঁকছে — mirror matrix-এর বাইরে (সোজা লেখা)
    # কেন লাগছে: mirror matrix-এর ভেতরে লেখা আঁকলে তা আয়নার মতো উল্টো দেখাত
    # real world-এ এটা কোথায় দেখা যায়: আয়নায় লেখা উল্টো — তাই UI টেক্সট কখনো mirror করা হয় না
    sx = config.SAMEE_ORIGIN[0] + config.LABEL_CX                      # Samee লেবেল কেন্দ্র (global x)
    rx = (config.RIFAT_ORIGIN[0] + config.ROOM_W) - config.LABEL_CX   # Rifat mirror কেন্দ্র (global x)
    y = config.SAMEE_ORIGIN[1] + config.LABEL_Y                       # baseline (global y)
    _draw_centered_text(sx, y, "Samee", config.TEXT, LABEL_FONT)
    _draw_centered_text(rx, y, "Rifat", config.TEXT, LABEL_FONT)


def display():
    # কী করছে: স্ক্রিন ক্লিয়ার করে Samee (translate) ও Rifat (translate+reflect) রুম, ডিভাইডার,
    #           ফ্রেম ও নাম লেবেল এঁকে বাফার সোয়াপ করছে; শেষে FPS গোনে
    # কেন লাগছে: এটাই প্রতি ফ্রেমের পুরো দৃশ্য; দুই রুম cached list দিয়ে দ্রুত আঁকা হয়
    # real world-এ এটা কোথায় দেখা যায়: গেমের render loop — clear → scene → UI → swap
    glClear(GL_COLOR_BUFFER_BIT)

    _draw_room("samee", config.SAMEE_ORIGIN[0], mirror=False)                 # translate(2, 2)
    _draw_room("rifat", config.RIFAT_ORIGIN[0] + config.ROOM_W, mirror=True)  # translate(97+93, 2) + reflect

    _draw_divider()
    _draw_frame()
    _draw_labels()   # mirror matrix-এর বাইরে, তাই লেখা সোজা

    glutSwapBuffers()
    _tick_fps()


def _tick_fps():
    # কী করছে: প্রতি ফ্রেম গুনে সেকেন্ডে একবার FPS কনসোলে ছাপে (Phase 10-এ সরিয়ে ফেলব)
    # কেন লাগছে: display list ঠিকমতো কাজ করছে ও রেন্ডার যথেষ্ট দ্রুত কিনা তা যাচাই করতে
    # real world-এ এটা কোথায় দেখা যায়: গেমের performance HUD/console-এ FPS দেখানো
    global _fps_count, _fps_t0
    now = time.perf_counter()
    if _fps_t0 is None:
        _fps_t0 = now
    _fps_count += 1
    if now - _fps_t0 >= 1.0:
        print("FPS:", _fps_count)
        _fps_count = 0
        _fps_t0 = now


def _idle():
    # কী করছে: অলস সময়ে বারবার রিড্র চায় (glutPostRedisplay)
    # কেন লাগছে: টানা রেন্ডার হলে তবেই FPS মাপা যায়; Phase 6-এ এটি timer দিয়ে বদলাবে
    # real world-এ এটা কোথায় দেখা যায়: গেম লুপ প্রতিনিয়ত নতুন ফ্রেম চায়
    glutPostRedisplay()


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
    # কী করছে: আর্গুমেন্ট পড়ে GLUT চালু করে উইন্ডো খোলে, init_scene() ডাকে, কলব্যাক বাঁধে ও মেইন লুপে ঢোকে
    # কেন লাগছে: এটাই অ্যাপের শুরু — উইন্ডো, প্রজেকশন, display list ও ইনপুট হ্যান্ডলার সেট করে সব চালু করে
    # real world-এ এটা কোথায় দেখা যায়: সব GUI প্রোগ্রামের main()/entry point এভাবেই সেটআপ করে
    args = parse_args()  # ভুল --me হলে argparse এখানেই usage দেখিয়ে বেরিয়ে যায়

    glutInit([sys.argv[0]])                          # GLUT চালু; নিজের ফ্ল্যাগ GLUT-কে দিচ্ছি না
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)     # ডাবল বাফার + RGBA কালার মোড
    glutInitWindowSize(config.WINDOW_W, config.WINDOW_H)
    # glutCreateWindow C-লেভেলে bytes (c_char_p) চায়, তাই str টাইটেলকে UTF-8 bytes-এ encode করছি
    glutCreateWindow(config.WINDOW_TITLE.encode("utf-8"))

    init_scene()                                      # প্রজেকশন/blending + display list তৈরি

    glutDisplayFunc(display)                          # প্রতি ফ্রেমে display() ডাকবে
    glutKeyboardFunc(keyboard)                        # কী চাপলে keyboard() ডাকবে
    glutIdleFunc(_idle)                               # টানা রিড্র (FPS মাপতে; Phase 10-এ সরাবে)

    glutMainLoop()                                    # ইভেন্ট লুপ শুরু; ESC না চাপা পর্যন্ত চলবে


if __name__ == "__main__":
    main()
