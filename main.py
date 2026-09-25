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
    glutInit,
    glutInitDisplayMode,
    glutInitWindowSize,
    glutKeyboardFunc,
    glutMainLoop,
    glutPostRedisplay,
    glutSwapBuffers,
    glutTimerFunc,
    GLUT_BITMAP_8_BY_13,
    GLUT_BITMAP_9_BY_15,
    GLUT_DOUBLE,
    GLUT_RGBA,
)

import character
import config
import lighting
import room
from pixel import draw_rect, draw_text, hex_to_rgb

# glutLeaveMainLoop freeglut-এ আছে; না থাকলে fallback হিসেবে sys.exit ব্যবহার করব।
try:
    from OpenGL.GLUT import glutLeaveMainLoop
except ImportError:
    glutLeaveMainLoop = None

ESC = b"\x1b"                     # কীবোর্ডের ESC কী-এর বাইট মান (ASCII 27)
LABEL_FONT = GLUT_BITMAP_9_BY_15  # নাম লেবেলের ফন্ট
DEBUG_FONT = GLUT_BITMAP_8_BY_13  # ডিবাগ লেবেলের ছোট ফন্ট

# ডিবাগ ভিউ state (design §11): D → পুরো overlay, G → শুধু গ্রিড। snapshot টুল _debug সেট করতে পারে।
_debug = False
_grid = False

# দুই ক্যারেক্টার — সব per-user state এখন এখানে (Phase 5-এর গ্লোবাল বুলিয়ান বাদ)
samee = character.Character("samee")
rifat = character.Character("rifat")

# অ্যানিমেশন ঘড়ি ও dt: স্বাভাবিক রানে বাস্তব সময়; snapshot টুল _fake_time সেট করে সময় ফ্রিজ করতে পারে
_start_time = time.perf_counter()
_last_tick = _start_time
_fake_time = None

# FPS কাউন্টার state (Phase 10-এ পুরো কাউন্টার সরিয়ে ফেলব)
_fps_count = 0
_fps_t0 = None


def anim_time():
    # কী করছে: অ্যানিমেশনের বর্তমান সময় (সেকেন্ড) দেয় — _fake_time সেট থাকলে সেটি, নাহলে বাস্তব সময়
    # কেন লাগছে: টাইপিং frame সময়ের উপর নির্ভর করে; snapshot টুল নির্দিষ্ট সময়ের ছবি নিতে সময় ফ্রিজ করে
    # real world-এ এটা কোথায় দেখা যায়: গেমে "game clock" — টেস্টে সময় নিয়ন্ত্রণ করা যায়
    return _fake_time if _fake_time is not None else (time.perf_counter() - _start_time)


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


def _draw_room(char, translate_x, mirror):
    # কী করছে: এক রুম আঁকছে design §8-এর স্তর ক্রমে — স্ট্যাটিক রুম → নিভানো স্ক্রিন/ল্যাম্প (ম্লান হবে) →
    #           চরিত্র → অন্ধকার overlay → glow → রশ্মি → স্ক্রিন আভা → জ্বলন্ত স্ক্রিন/ল্যাম্প (উজ্জ্বল, উপরে)
    #           → ডিবাগ overlay। সব এক push/pop matrix-এর ভেতরে (translate, Rifat হলে reflect)।
    # কেন লাগছে: আলো স্তর হিসেবে উপরে বসে; নিভানো device overlay-তে ম্লান হয়, জ্বলন্ত device পরে এঁকে উজ্জ্বল থাকে
    # real world-এ এটা কোথায় দেখা যায়: রেন্ডারারে scene → lighting pass → emissive pass ক্রমে আঁকা
    lit = char.monitor_on or char.lamp_on                 # রুমে কোনো device চালু = "কাজ হচ্ছে"
    glPushMatrix()
    glTranslatef(translate_x, config.RIFAT_ORIGIN[1], 0)  # y=2 দুই রুমেই এক
    if mirror:
        glScalef(-1, 1, 1)                                # অনুভূমিক প্রতিফলন (reflection)

    # ১. স্ট্যাটিক রুম (cached) + নিভানো স্ক্রিন/ল্যাম্প — এগুলো অন্ধকার overlay-তে ম্লান হবে
    glCallList(room.ROOM_LISTS[(char.name, char.bed_is_messy())])  # IN_BED হলে neat, নাহলে messy
    room.draw_screen(on=False)                            # নিভানো স্ক্রিনের ভিত্তি (base)
    room.draw_lamp_shade(on=False, warn=False)            # নিভানো শেডের ভিত্তি (base)

    # ২. চরিত্র (ঘুম/হাঁটা/বসা/টাইপিং)
    char.draw(anim_time())

    # ৩–৬. আলো স্তর: অন্ধকার → উষ্ণ glow → রশ্মি → স্ক্রিন আভা
    lighting.draw_darkness(lit)
    if char.lamp_on:
        lighting.draw_glow()
        if not _debug:                                    # ডিবাগে রশ্মি লাল/সবুজে আলাদা আঁকা হবে
            lighting.draw_rays(debug=False)
    if char.monitor_on:
        lighting.draw_screen_glow()

    # ৭. emissive: জ্বলন্ত স্ক্রিন ও ল্যাম্প শেড — আলোর পরে এঁকি যেন উজ্জ্বল থাকে (ম্লান না হয়)
    if char.monitor_on:
        room.draw_screen(on=True)
    if char.lamp_on:
        room.draw_lamp_shade(on=True, warn=False)

    # ডিবাগ overlay (দুই রুমেই, matrix-এর ভেতরে যাতে transform মেলে; text লেবেল বাইরে আঁকা হয়)
    if _debug:
        lighting.draw_rays(debug=True)                    # লাল (কাটার আগে) + সবুজ (কাটার পরে)
        lighting.draw_debug(grid_only=False)              # গ্রিড + clip rect + Bezier + কন্ট্রোল পয়েন্ট
    elif _grid:
        lighting.draw_debug(grid_only=True)               # শুধু গ্রিড

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


def _draw_debug_labels():
    # কী করছে: ডিবাগ text — Samee-র ৪টি কন্ট্রোল পয়েন্টের নাম (P0..P3) ও নিচে ছোট legend আঁকে,
    #           সব গ্লোবাল কোঅর্ডিনেটে (mirror matrix-এর বাইরে)
    # কেন লাগছে: mirror matrix-এর ভেতরে text আঁকলে আয়নার মতো উল্টো হতো; তাই লেবেল বাইরে গ্লোবালে
    # real world-এ এটা কোথায় দেখা যায়: ডিবাগ HUD — জ্যামিতি transform-এ থাকলেও লেবেল সবসময় সোজা
    ox, oy = config.SAMEE_ORIGIN
    points = (config.WALK_P0, config.WALK_P1, config.WALK_P2, config.WALK_P3)
    for i, (px, py) in enumerate(points):                 # Samee: গ্লোবাল = লোকাল + origin
        draw_text(ox + px + 2, oy + py, "P%d" % i, config.DEBUG_CTRL, DEBUG_FONT)
    draw_text(config.SAMEE_ORIGIN[0], config.GRID_H - 3,
              "D=debug  G=grid   red=unclipped  green=clipped",
              config.TEXT, DEBUG_FONT)


def display():
    # কী করছে: স্ক্রিন ক্লিয়ার করে Samee (translate) ও Rifat (translate+reflect) রুম, ডিভাইডার,
    #           ফ্রেম ও নাম লেবেল এঁকে বাফার সোয়াপ করছে; শেষে FPS গোনে
    # কেন লাগছে: এটাই প্রতি ফ্রেমের পুরো দৃশ্য; দুই রুম cached list দিয়ে দ্রুত আঁকা হয়
    # real world-এ এটা কোথায় দেখা যায়: গেমের render loop — clear → scene → UI → swap
    glClear(GL_COLOR_BUFFER_BIT)

    _draw_room(samee, config.SAMEE_ORIGIN[0], False)                     # translate(2, 2)
    _draw_room(rifat, config.RIFAT_ORIGIN[0] + config.ROOM_W, True)      # translate(97+93, 2) + reflect

    _draw_divider()
    _draw_frame()
    _draw_labels()   # mirror matrix-এর বাইরে, তাই লেখা সোজা
    if _debug:
        _draw_debug_labels()   # ডিবাগ text-ও mirror matrix-এর বাইরে

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


def timer(value):
    # কী করছে: প্রতি ~16ms-এ বাস্তব dt বের করে দুই চরিত্র update করে, রিড্র চায় ও নিজেকে আবার schedule করে
    # কেন লাগছে: অ্যানিমেশন বাস্তব সময়ের সাথে চলতে হয়; dt দিয়ে গতি frame-rate নিরপেক্ষ থাকে
    # real world-এ এটা কোথায় দেখা যায়: গেম লুপের update(dt) — প্রতি টিকে সময় এগিয়ে state আপডেট
    global _last_tick
    now = time.perf_counter()
    dt = now - _last_tick          # গত টিক থেকে কত সময় গেছে (Character.update dt clamp করে)
    _last_tick = now
    samee.update(dt)
    rifat.update(dt)
    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)


def keyboard(key, x, y):
    # কী করছে: ESC → বন্ধ; '1'/'2' → Samee/Rifat টগল; 'D' → ডিবাগ overlay, 'G' → শুধু গ্রিড টগল
    # কেন লাগছে: টগল শুধু লক্ষ্য বদলায় (animation মেলায়); D/G দিয়ে ক্লিপিং/পথ চোখে দেখানো (viva)
    # real world-এ এটা কোথায় দেখা যায়: ডেমো কী দিয়ে target state ও ডিবাগ view পাল্টানো
    global _debug, _grid
    if key == ESC:
        if glutLeaveMainLoop is not None:
            glutLeaveMainLoop()   # freeglut-এ মেইন লুপ পরিষ্কারভাবে থামায়
        else:
            sys.exit(0)
    elif key == b"1":
        samee.set_working(not samee.target_working)
    elif key == b"2":
        rifat.set_working(not rifat.target_working)
    elif key in (b"d", b"D"):
        _debug = not _debug       # পুরো ডিবাগ overlay (গ্রিডও দেখায়)
    elif key in (b"g", b"G"):
        _grid = not _grid         # শুধু গ্রিড লাইন
    glutPostRedisplay()           # ডিবাগ টগলের ফল সাথে সাথে দেখাতে রিড্র চাই


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
    glutTimerFunc(16, timer, 0)                       # ~60 FPS টাইমার (Phase 6-এ dt সহ পূর্ণ হবে)

    glutMainLoop()                                    # ইভেন্ট লুপ শুরু; ESC না চাপা পর্যন্ত চলবে


if __name__ == "__main__":
    main()
