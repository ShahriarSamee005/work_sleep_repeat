import argparse
import queue
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

import pyglet
from pyglet.event import EVENT_HANDLED
from pyglet.window import key as pyglet_key

import activity
import alerts
import character
import clock
import config
import font
import lighting
import listener
import panel
import room
import state
import sync
import tray
import userconfig
from pixel import draw_box, draw_rect, draw_text, hex_to_rgb, text_width

TICK_SECONDS = 1.0 / 60.0         # অ্যানিমেশন টিকের ব্যবধান (আগের glutTimerFunc-এর ১৬ms)
LABEL_FONT = font.BITMAP_9X15     # নাম লেবেলের ফন্ট
DEBUG_FONT = font.BITMAP_8X13     # ডিবাগ লেবেলের ছোট ফন্ট

# অ্যাপের একমাত্র উইন্ডো — main() তৈরি করে; হ্যান্ডলারগুলো এটি দিয়ে উচ্চতা/দৃশ্যমানতা দেখে
_window = None

# ডিবাগ ভিউ state (design §11): D → পুরো overlay, G → শুধু গ্রিড। snapshot টুল _debug সেট করতে পারে।
_debug = False
_grid = False

# দুই ক্যারেক্টার — সব per-user state এখন এখানে (Phase 5-এর গ্লোবাল বুলিয়ান বাদ)
samee = character.Character("samee")
rifat = character.Character("rifat")

# অ্যানিমেশন ঘড়ি ও dt: স্বাভাবিক রানে বাস্তব সময়; snapshot টুল _fake_time সেট করে সময় ফ্রিজ করতে পারে
_start_time = time.perf_counter()
_fake_time = None

# --me: কোন ব্যবহারকারী এই অ্যাপ চালাচ্ছে (হুক এই জনের status চালায়); main() সেট করে
_me = "samee"

# ডিটেকশন অংশ (Phase 10) — main() তৈরি করে; হুক ইভেন্ট listener থ্রেড থেকে queue হয়ে আসে
_state = None        # state.AppState — working/since/today_seconds-এর একমাত্র সত্য
_activity = None     # activity.Activity — হুক ইভেন্ট → working (pure logic)
_listener = None     # listener.Listener — 127.0.0.1:47821
_sync = None         # sync.Sync — Supabase push/poll থ্রেড (--offline হলে None)
_last_push = 0.0     # সর্বশেষ কখন নিজের status আউটবক্সে দিয়েছি (প্রতি ৬০s পুশের হিসাব)
_events = queue.Queue()   # listener থ্রেড ভরে, main থ্রেড খালি করে (activity একাই main-এ চলে)
_dev = False         # --dev: কী 1/2 নকল ইভেন্ট ঢালে

# ট্রে ও অ্যালার্ট (Phase 13) — ট্রে নিজের থ্রেডে চলে, তাই সব উইন্ডো-কাজ কমান্ড কিউ হয়ে আসে
_tray = None
_commands = tray.make_commands()    # listener ও tray থ্রেড ভরে; main থ্রেড খালি করে
_alert_settings = None              # কোন টোস্ট চালু (config.json-এ সেভ হয়)
_alert_memory = alerts.Memory()     # dedupe স্মৃতি
_prev_snap = None                   # গত সেকেন্ডের snapshot (alerts তুলনা করে)
_animating = False                  # ৬০ FPS টিক চালু আছে? (উইন্ডো লুকালে বন্ধ রাখি)

# ওয়াল-ক্লক (সময় হিসাব ও দিন): virtual now = শুরু + অতিবাহিত বাস্তব সময় × TIME_SCALE।
# TIME_SCALE বাড়ালে কার্ড দ্রুত বাড়ে ও মধ্যরাত রিসেট দ্রুত টেস্ট করা যায়। snapshot _fake_wall সেট করতে পারে।
_wall_start = time.time()
_fake_wall = None


def wall_now():
    # কী করছে: সময় হিসাবের virtual "now" (epoch সেকেন্ড) দেয় — _fake_wall থাকলে সেটি,
    #           নাহলে শুরু থেকে অতিবাহিত বাস্তব সময়কে TIME_SCALE দিয়ে গুণ করে এগিয়ে নেওয়া মান
    # কেন লাগছে: টাইম কার্ড ও মধ্যরাত রিসেট বাস্তব সময়ে চলে; TIME_SCALE দিয়ে দ্রুত টেস্ট, snapshot-এ ফ্রিজ
    # real world-এ এটা কোথায় দেখা যায়: সিমুলেশন/গেমে "scaled clock" (time warp) ও টেস্টে ফিক্সড ঘড়ি
    if _fake_wall is not None:
        return _fake_wall
    return _wall_start + (time.time() - _wall_start) * config.TIME_SCALE

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
    parser.add_argument(
        "--tray",
        action="store_true",
        help="start hidden in the tray (used by autostart)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="dev mode: keys 1/2 inject fake hook events, FPS in the debug view",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="dev only (needs --dev): listen on another port, to run two copies on one PC",
    )
    parser.add_argument(
        "--idle",
        type=int,
        help="dev only (needs --dev): override IDLE_TIMEOUT in seconds for manual tests",
    )
    args = parser.parse_args()
    if not args.dev and (args.port is not None or args.idle is not None):
        parser.error("--port and --idle are dev-only; add --dev to use them")
    return args


def init_gl(fb_w=config.WINDOW_W, fb_h=config.WINDOW_H):
    # কী করছে: ব্যাকগ্রাউন্ড রঙ, ভিউপোর্ট, 2D প্রজেকশন (y=0 উপরে) ও alpha blending সেট করছে
    # কেন লাগছে: gluOrtho2D গ্রিড কোঅর্ডিনেটকে স্ক্রিনে ম্যাপ করে; blending আলো/ছায়ায় স্বচ্ছতা দেয়
    # real world-এ এটা কোথায় দেখা যায়: প্রতিটি রেন্ডারারের init-এ ক্যামেরা/প্রজেকশন ও blend state সেট হয়
    # fb_w/fb_h: উইন্ডোর framebuffer মাপ (DPI স্কেলিং-এ WINDOW_W×WINDOW_H-এর চেয়ে বড় হতে পারে);
    #            ortho গ্রিডকে পুরো ভিউপোর্টে ম্যাপ করে, তাই মাপ যা হোক ২৪০×৯৬ গ্রিড একইভাবে বসে
    r, g, b = hex_to_rgb(config.OUTLINE)                # ব্যাকগ্রাউন্ড রঙ config থেকে (#231c2b)
    glClearColor(r, g, b, 1.0)

    glViewport(0, 0, fb_w, fb_h)                        # পুরো উইন্ডো জুড়ে আঁকা হবে
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, config.GRID_W, config.GRID_H, 0)      # left,right,bottom,top → y=0 উপরে (উল্টানো)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glEnable(GL_BLEND)                                   # স্বচ্ছতা চালু
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)   # স্বাভাবিক alpha blending সূত্র


def init_scene(fb_w=config.WINDOW_W, fb_h=config.WINDOW_H):
    # কী করছে: GL state সেট করে (init_gl) তারপর রুমের display list গুলো তৈরি করছে
    # কেন লাগছে: display list বানাতে GL কনটেক্সট লাগে; উইন্ডো তৈরির পর একবারই এটি ডাকা হয়
    # real world-এ এটা কোথায় দেখা যায়: গেম ইঞ্জিনের "assets GPU-তে আপলোড" ধাপ, লুপ শুরুর আগে
    init_gl(fb_w, fb_h)
    room.build_room_lists()


def _draw_room(char, translate_x, mirror, warn=False, offline=False):
    # কী করছে: এক রুম আঁকছে design §8-এর স্তর ক্রমে — স্ট্যাটিক রুম → নিভানো স্ক্রিন/ল্যাম্প (ম্লান হবে) →
    #           চরিত্র → অন্ধকার overlay → glow → রশ্মি → স্ক্রিন আভা → জ্বলন্ত স্ক্রিন/ল্যাম্প (উজ্জ্বল, উপরে)
    #           → ডিবাগ overlay। সব এক push/pop matrix-এর ভেতরে (translate, Rifat হলে reflect)।
    # কেন লাগছে: আলো স্তর হিসেবে উপরে বসে; নিভানো device overlay-তে ম্লান হয়, জ্বলন্ত device পরে এঁকে উজ্জ্বল থাকে
    #           warn=True হলে (দুজনেই কাজ, ব্লিঙ্ক ফ্রেম) ল্যাম্প শেড লাল হয় (দ্বন্দ্ব সতর্কতা, appflow §7)
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
        room.draw_lamp_shade(on=True, warn=warn)          # দ্বন্দ্ব ব্লিঙ্ক ফ্রেমে warn=True → লাল

    # সঙ্গী অফলাইন: পুরো রুমে বাড়তি অন্ধকার (design §3) — emissive-এর পরেও, যাতে স্ক্রিন/ল্যাম্পও ম্লান হয়
    if offline:
        lighting.draw_offline()

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


def _draw_centered_text(cx, y, text, color, label_font):
    # কী করছে: cx-কে কেন্দ্র ধরে text-এর প্রস্থ (window px) মেপে গ্রিড এককে বাঁয়ে সরিয়ে আঁকছে
    # কেন লাগছে: নাম লেবেল রাগের নিচে ঠিক মাঝ বরাবর বসাতে হয়
    # real world-এ এটা কোথায় দেখা যায়: UI-তে টেক্সট center-align করা
    width_px = text_width(text, label_font)
    start_x = cx - (width_px / config.PIXEL) / 2.0
    draw_text(start_x, y, text, color, label_font)


def _draw_labels():
    # কী করছে: "Samee" ও "Rifat" নাম দুই রাগের নিচে আঁকছে — mirror matrix-এর বাইরে (সোজা লেখা)
    # কেন লাগছে: mirror matrix-এর ভেতরে লেখা আঁকলে তা আয়নার মতো উল্টো দেখাত
    # real world-এ এটা কোথায় দেখা যায়: আয়নায় লেখা উল্টো — তাই UI টেক্সট কখনো mirror করা হয় না
    sx = config.SAMEE_ORIGIN[0] + config.LABEL_CX                      # Samee লেবেল কেন্দ্র (global x)
    rx = (config.RIFAT_ORIGIN[0] + config.ROOM_W) - config.LABEL_CX   # Rifat mirror কেন্দ্র (global x)
    y = config.SAMEE_ORIGIN[1] + config.LABEL_Y                       # baseline (global y)
    _draw_centered_text(sx, y, "Samee", config.TEXT, LABEL_FONT)
    _draw_centered_text(rx, y, "Rifat", config.TEXT, LABEL_FONT)


def _draw_plaques(views):
    # কী করছে: যে রুমের মানুষ অফলাইন, সেই রুমে একটি ছোট "OFFLINE" ফলক আঁকে (বাক্স + লেখা)
    # কেন লাগছে: শুধু অন্ধকার দেখে বোঝা যায় না কেন রুম ম্লান; লেখাটি কারণ বলে দেয় (design §3)
    # real world-এ এটা কোথায় দেখা যায়: disabled কার্ডের উপর "offline" ব্যাজ
    # নোট: নামের লেবেলের মতোই গ্লোবাল কোঅর্ডিনেটে — mirror matrix-এর ভেতরে হলে লেখা উল্টো হতো
    px, py, pw, ph = config.PLAQUE_BOX
    for name, origin, flip in (("samee", config.SAMEE_ORIGIN, False),
                               ("rifat", config.RIFAT_ORIGIN, True)):
        if views[name].online:
            continue
        ox, oy = origin
        # Rifat-এর রুম আয়নায় আঁকা হয়, তাই ফলকের x রুমের ডান কিনারা থেকে মাপি
        bx = (ox + config.ROOM_W - px - pw) if flip else (ox + px)
        cx = (ox + config.ROOM_W - config.PLAQUE_CX) if flip else (ox + config.PLAQUE_CX)
        draw_box(bx, oy + py, pw, ph, config.NIGHT, outline=config.OFFLINE_GREY)
        _draw_centered_text(cx, oy + config.PLAQUE_Y, "OFFLINE",
                            config.OFFLINE_GREY, DEBUG_FONT)


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
    #           ফ্রেম ও নাম লেবেল আঁকছে; শেষে FPS গোনে
    # কেন লাগছে: এটাই প্রতি ফ্রেমের পুরো দৃশ্য; দুই রুম cached list দিয়ে দ্রুত আঁকা হয়
    # real world-এ এটা কোথায় দেখা যায়: গেমের render loop — clear → scene → UI → (swap)
    # নোট: বাফার সোয়াপ এখানে নেই — pyglet on_draw শেষে নিজেই flip করে (আগে glutSwapBuffers ছিল)
    if _window is not None and not _window.visible:
        return                               # ট্রে-তে লুকানো — আঁকার কিছু নেই (Phase 13)
    glClear(GL_COLOR_BUFFER_BIT)

    now = wall_now()
    snap = _state.snapshot(now)              # প্রতি ফ্রেমে একবার snapshot (techspec §7)
    views = _views(snap)

    # দ্বন্দ্ব: দুজনেই কাজ করছে → ল্যাম্প শেড প্রতি 0.5s লাল-হলুদ ব্লিঙ্ক (appflow §7)
    conflict = views["samee"].working and views["rifat"].working
    blink_on = int(anim_time() / config.CONFLICT_BLINK_SECONDS) % 2 == 0
    warn = conflict and blink_on

    _draw_room(samee, config.SAMEE_ORIGIN[0], False, warn,
               offline=not views["samee"].online)                        # translate(2, 2)
    _draw_room(rifat, config.RIFAT_ORIGIN[0] + config.ROOM_W, True, warn,
               offline=not views["rifat"].online)       # translate(97+93, 2) + reflect

    _draw_divider()
    _draw_frame()
    _draw_labels()   # mirror matrix-এর বাইরে, তাই লেখা সোজা
    _draw_plaques(views)   # "OFFLINE" ফলক — লেখা, তাই mirror-এর বাইরে

    # প্যানেল (design §2) — পুরো snapshot দিই; প্যানেল শুধু সেটিই পড়ে, লক ধরে না
    panel.draw_panel(snap)

    if _debug:
        _draw_debug_labels()   # ডিবাগ text-ও mirror matrix-এর বাইরে

    _tick_fps()


def _tick_fps():
    # কী করছে: প্রতি ফ্রেম গুনে সেকেন্ডে একবার FPS কনসোলে ছাপে — শুধু ডিবাগ ভিউতে (appflow §15)
    # কেন লাগছে: display list ঠিকমতো কাজ করছে ও রেন্ডার যথেষ্ট দ্রুত কিনা তা যাচাই করতে;
    #           স্বাভাবিক রানে কনসোল পরিষ্কার থাকে, তাই ডিটেকশনের লাইনগুলো চোখে পড়ে
    # real world-এ এটা কোথায় দেখা যায়: গেমের performance HUD — ডিবাগ বিল্ডে/ভিউতে দেখানো
    global _fps_count, _fps_t0
    if not _debug:
        return
    now = time.perf_counter()
    if _fps_t0 is None:
        _fps_t0 = now
    _fps_count += 1
    if now - _fps_t0 >= 1.0:
        print("FPS:", _fps_count)
        _fps_count = 0
        _fps_t0 = now


def _views(snap):
    # কী করছে: snapshot-এর me/peer ভিউ দুটিকে {"samee": view, "rifat": view} রূপে সাজায়
    # কেন লাগছে: রুম ও কার্ড সবসময় বাঁয়ে Samee, ডানে Rifat — কে অ্যাপ চালাচ্ছে তা নির্বিশেষে
    # real world-এ এটা কোথায় দেখা যায়: "me/them" মডেলকে স্থির UI স্লটে ম্যাপ করা
    return {snap.me.user_id: snap.me, snap.peer.user_id: snap.peer}


def _drain_events():
    # কী করছে: listener থ্রেড যা জমা করেছে সব হুক ইভেন্ট নিয়ে activity-কে দেয়; কতটা পেল তা বলে
    # কেন লাগছে: activity-তে কোনো থ্রেড/লক নেই — তাই শুধু main থ্রেড তাকে ছোঁয় (techspec §3)
    # real world-এ এটা কোথায় দেখা যায়: producer/consumer queue — I/O থ্রেড জমায়, লুপ থ্রেড প্রক্রিয়া করে
    count = 0
    while True:
        try:
            event = _events.get_nowait()
        except queue.Empty:
            return count
        _activity.handle(event, wall_now())
        count += 1


def _push_status(now):
    # কী করছে: নিজের বর্তমান অবস্থা sync-এর আউটবক্সে দেয় (--offline হলে কিছুই করে না)
    # কেন লাগছে: working বদলালে, মধ্যরাত পেরোলে ও কাজ চলার সময় প্রতি ৬০s-এ সার্ভারে জানাতে হয় (§6.5)
    # real world-এ এটা কোথায় দেখা যায়: লোকাল পরিবর্তন → outbox → ব্যাকগ্রাউন্ড sync
    global _last_push
    if _sync is None:
        return
    _last_push = now
    _sync.queue_status(sync.status_fields(_state.snapshot(now), now))


def _apply_activity(now):
    # কী করছে: activity.tick() চালিয়ে নিজের working অবস্থা AppState-এ লেখে (বদল হলে since-ও বসে),
    #           আর বদল/মধ্যরাত/৬০s পেরোলে সার্ভারে পুশের জন্য আউটবক্সে দেয়
    # কেন লাগছে: এটাই "হুক → আমার চরিত্র → সঙ্গীর স্ক্রিন" পথের মাঝের ধাপ
    # real world-এ এটা কোথায় দেখা যায়: ডিটেকশনের ফল একটিই state store-এ লেখা, তারপর প্রচার
    rolled = _state.roll_day(now)              # মধ্যরাত (Dhaka) পেরোলে আজকের কাউন্টার ০
    changed = _state.set_working(_activity.tick(now), now)
    snap = _state.snapshot(now)
    if changed:
        print("WSR: working ->", snap.me.working)
    due = snap.me.working and (now - _last_push) >= config.PUSH_WHILE_WORKING
    if changed or rolled or due:
        _push_status(now)


def tick(dt):
    # কী করছে: প্রতি ~16ms-এ snapshot থেকে দুই চরিত্রের লক্ষ্য বসায় ও অ্যানিমেশন এগিয়ে নেয়
    # কেন লাগছে: অ্যানিমেশন বাস্তব সময়ের সাথে চলতে হয়; dt দিয়ে গতি frame-rate নিরপেক্ষ থাকে
    # real world-এ এটা কোথায় দেখা যায়: গেম লুপের update(dt)
    # নোট: উইন্ডো লুকানো থাকলে এই টিক unschedule করা হয় (কেউ দেখছে না, CPU খরচেরও মানে নেই);
    #      ইভেন্ট নেওয়া ও ট্রে কমান্ড _pump-এ, যা সবসময় চলে
    now = wall_now()
    views = _views(_state.snapshot(now))
    for name, char in (("samee", samee), ("rifat", rifat)):
        view = views[name]
        char.set_working(view.working, now)      # চরিত্র শুধু লক্ষ্য অনুসরণ করে
        if view.online:
            char.update(dt)                      # অফলাইন সঙ্গীর চরিত্র যেখানে ছিল সেখানেই থাকে (design §3)
    _redraw()


def _redraw():
    # কী করছে: এক ফ্রেম আঁকে — কনটেক্সট ধরে, on_draw ডাকে, বাফার ফ্লিপ করে
    # কেন লাগছে: pyglet.app.run(interval=None) দিয়ে চলছি, অর্থাৎ pyglet নিজে থেকে রিড্র করে না।
    #           তাই আঁকা হয় শুধু অ্যানিমেশন টিক থেকে — আর টিক বন্ধ মানে আঁকাও বন্ধ (লুকানো অবস্থায়
    #           CPU প্রায় শূন্য; ডিফল্ট ৬০ Hz রিড্র চালু থাকলে লুকিয়েও ~২০% কোর খেত)
    # real world-এ এটা কোথায় দেখা যায়: নিজের হাতে রেন্ডার লুপ চালানো (manual present/swap)
    if _window is None or not _window.visible:
        return
    _window.switch_to()
    _window.dispatch_event("on_draw")
    _window.flip()


def _pump(dt):
    # কী করছে: হুক ইভেন্ট ও ট্রে/দ্বিতীয়-কপির কমান্ড নিয়ে কাজ করে — উইন্ডো দেখানো/লুকানো/বন্ধ করা
    # কেন লাগছে: ট্রে ও listener আলাদা থ্রেডে চলে; উইন্ডো ছোঁয়া শুধু এই থ্রেডেই বৈধ (techspec §3)।
    #           অ্যানিমেশন বন্ধ থাকলেও এটি চলে, তাই লুকানো অবস্থাতেও ট্রে মেনু সাড়া দেয়
    # real world-এ এটা কোথায় দেখা যায়: UI থ্রেডের message pump — বাইরের কমান্ড এখানেই প্রয়োগ হয়
    if _drain_events():
        _apply_activity(wall_now())
    while True:
        try:
            command = _commands.get_nowait()
        except queue.Empty:
            return
        if command == tray.SHOW:
            show_window()
        elif command == tray.HIDE:
            hide_window()
        elif command == tray.QUIT:
            quit_app()


def state_tick(dt):
    # কী করছে: প্রতি সেকেন্ডে activity.tick() চালায়, ট্রে আইকন/টুলটিপ মেলায় ও টোস্ট বাজায়
    # কেন লাগছে: কোনো ইভেন্ট না এলেও সময় পেরোলে working নিজে থেকে False হতে হবে (appflow §5);
    #           আর অ্যালার্ট তুলনা করে দুই পরপর snapshot-এর মধ্যে (techspec §9)
    # real world-এ এটা কোথায় দেখা যায়: periodic reaper + state diff → notifications
    global _prev_snap
    now = wall_now()
    _apply_activity(now)
    snap = _state.snapshot(now)
    status = panel.status_line(snap)[0]          # টুলটিপ = প্যানেলের স্ট্যাটাস লেখা (design §4)
    for toast in alerts.check(_prev_snap, snap, _alert_memory):
        if _alert_settings is not None and not _alert_settings.is_enabled(toast.kind):
            continue                             # এই অ্যালার্ট ব্যবহারকারী বন্ধ করে রেখেছেন
        print("WSR: toast:", toast.title, "—", toast.body)
        if _tray is not None:
            _tray.notify(toast.title, toast.body)
    if _tray is not None:
        _tray.update(snap, status)
    _prev_snap = snap


def show_window():
    # কী করছে: উইন্ডো দেখায়, সামনে আনে ও অ্যানিমেশন টিক আবার চালু করে
    # কেন লাগছে: ট্রে মেনু "Open rooms" ও দ্বিতীয় কপির POST /show — দুটোই এখানে আসে (appflow §13)
    # real world-এ এটা কোথায় দেখা যায়: tray অ্যাপে "restore window"
    global _animating
    _window.set_visible(True)
    _window.activate()
    if not _animating:
        pyglet.clock.schedule_interval(tick, TICK_SECONDS)
        _animating = True


def hide_window():
    # কী করছে: উইন্ডো লুকিয়ে ফেলে ও ৬০ FPS টিক unschedule করে
    # কেন লাগছে: ট্রে-তে থাকা অবস্থায় কেউ দেখছে না — তখন আঁকা/হিসাব করা মানে শুধু ব্যাটারি খরচ।
    #           ডিটেকশন, sync ও অ্যালার্ট চলতেই থাকে (সেগুলো ১ Hz ও ১০ Hz টিকে)
    # real world-এ এটা কোথায় দেখা যায়: লুকানো উইন্ডোতে রেন্ডার লুপ থামানো (throttle when hidden)
    global _animating
    _window.set_visible(False)
    if _animating:
        pyglet.clock.unschedule(tick)
        _animating = False


def request_close():
    # কী করছে: X বোতাম ও ESC — অ্যাপ বন্ধ না করে উইন্ডো লুকিয়ে ট্রে-তে পাঠায় (appflow §13)
    # কেন লাগছে: অ্যাপ চলতে থাকলে তবেই হুক ধরা ও সঙ্গীকে দেখা চলতে থাকে; বন্ধ করার পথ ট্রে → Quit
    # real world-এ এটা কোথায় দেখা যায়: ব্যাকগ্রাউন্ড অ্যাপে X = hide, Quit আলাদা
    # Phase 10-এ এটি pyglet.app.exit() ছিল; Phase 13-এ শুধু এই ফাংশনটাই বদলাতে হলো
    hide_window()


def quit_app():
    # কী করছে: সত্যিকারের বন্ধ — ট্রে আইকন থামিয়ে মেইন লুপ থেকে বেরোয় (main-এর finally বাকিটা করে)
    # কেন লাগছে: ট্রে মেনুর Quit-ই এখন বন্ধ করার একমাত্র পথ (gate: থ্রেড/পোর্ট পরিষ্কারভাবে ছাড়া)
    # real world-এ এটা কোথায় দেখা যায়: tray অ্যাপের Quit — আইকন সরিয়ে প্রসেস শেষ
    if _tray is not None:
        _tray.stop()
    pyglet.app.exit()


def on_close():
    # কী করছে: উইন্ডোর X চাপলে আমাদের request_close() ডাকে ও pyglet-কে জানায় "সামলে নিয়েছি"
    # কেন লাগছে: True ফেরত না দিলে pyglet নিজের ডিফল্ট close চালাত (উইন্ডো ধ্বংস + exit)
    # real world-এ এটা কোথায় দেখা যায়: GUI-তে close ইভেন্ট intercept করে "সত্যিই বন্ধ?"/tray-তে পাঠানো
    request_close()
    return EVENT_HANDLED


def _inject(event_name):
    # কী করছে: --dev মোডে একটি নকল হুক ইভেন্ট আসল পথেই (queue → activity) ঢেলে দেয়
    # কেন লাগছে: Claude Code না খুলেই ডিটেকশনের পথ পরীক্ষা করতে; --dev ছাড়া কী 1/2 নিষ্ক্রিয় (§4.5)
    # real world-এ এটা কোথায় দেখা যায়: ডেভ বিল্ডে "simulate event" শর্টকাট
    if not _dev:
        return
    _events.put({"hook_event_name": event_name, "session_id": config.DEV_SESSION_ID})
    print("WSR: dev inject", event_name)


def on_key_press(symbol, modifiers):
    # কী করছে: ESC → বন্ধ; '1'/'2' → (--dev হলে) নকল prompt / session end; 'D' → ডিবাগ overlay,
    #           'G' → শুধু গ্রিড টগল
    # কেন লাগছে: ম্যানুয়াল টগল আর নেই — status এখন হুক থেকে আসে; D/G দিয়ে ক্লিপিং/পথ চোখে দেখানো
    # real world-এ এটা কোথায় দেখা যায়: ডিবাগ কী ও ডেভ-মোড ইভেন্ট ইনজেকশন
    # নোট: ESC-ও request_close() দিয়েই যায় (pyglet-এর ডিফল্ট ESC হ্যান্ডলার নয়), তাই
    #      Phase 13-এ X ও ESC একসাথে "hide to tray" হবে (appflow §13)
    global _debug, _grid
    if symbol == pyglet_key.ESCAPE:
        request_close()
    elif symbol in (pyglet_key._1, pyglet_key.NUM_1):
        _inject("UserPromptSubmit")      # --dev ছাড়া কিছুই হয় না
    elif symbol in (pyglet_key._2, pyglet_key.NUM_2):
        _inject("SessionEnd")
    elif symbol == pyglet_key.D:
        _debug = not _debug       # পুরো ডিবাগ overlay (গ্রিডও দেখায়)
    elif symbol == pyglet_key.G:
        _grid = not _grid         # শুধু গ্রিড লাইন
    return EVENT_HANDLED


def make_window(visible=True):
    # কী করছে: অ্যাপের pyglet উইন্ডো বানায় (legacy GL কনটেক্সট চেয়ে) ও আমাদের হ্যান্ডলার বাঁধে
    # কেন লাগছে: ফেজ ০–৮-এর আঁকা পুরোটাই immediate mode (glBegin) ও display list — core profile-এ
    #           এগুলো নেই, তাই স্পষ্ট করে ২.১ compatibility কনটেক্সট চাই
    # real world-এ এটা কোথায় দেখা যায়: পুরনো GL কোড চালাতে compatibility profile চেয়ে নেওয়া
    # visible=False → --tray মোডে লুকিয়ে শুরু (appflow §13); GL কনটেক্সট তবু তৈরি হয়
    gl_config = pyglet.gl.Config(double_buffer=True, major_version=2, minor_version=1)
    win = pyglet.window.Window(
        visible=visible,
        width=config.WINDOW_W,
        height=config.WINDOW_H,
        caption=config.WINDOW_TITLE,
        resizable=False,
        config=gl_config,
    )
    # হ্যান্ডলার সরাসরি বসাই — pyglet-এর ডিফল্ট on_close/on_key_press যেন না চলে
    # মাউস হ্যান্ডলার আর নেই: টগল বাদ (Phase 10), আর dibs বাটন আসবে Phase 14-এ
    win.on_draw = display
    win.on_close = on_close
    win.on_key_press = on_key_press
    return win


def _start_sync(offline, peer, settings):
    # কী করছে: --offline না হলে ও credentials পেলে sync থ্রেড চালু করে; নাহলে None দিয়ে বলে দেয় কেন
    # কেন লাগছে: নেট/কনফিগ ছাড়াও অ্যাপ পুরোপুরি চলবে — শুধু সঙ্গীকে দেখা যাবে না (appflow §10)
    # real world-এ এটা কোথায় দেখা যায়: ঐচ্ছিক ব্যাকএন্ড — না থাকলে অ্যাপ "লোকাল মোডে" চলে
    if offline:
        print("WSR: --offline — no Supabase sync this run")
        return None
    if not settings.has_supabase:
        print("WSR: no Supabase URL/key found (checked config.json, .env, environment)"
              " — running local only")
        return None
    engine = sync.Sync(_state, sync.Client(settings.supabase_url, settings.supabase_key),
                       me=_me, peer=peer)
    engine.start()
    print("WSR: syncing with Supabase (credentials from %s)" % settings.source)
    return engine


def main():
    # কী করছে: আর্গুমেন্ট পড়ে পোর্ট দখল করে (একটাই কপি), listener চালু করে, উইন্ডো খোলে,
    #           দুটি টিক schedule করে ও মেইন লুপে ঢোকে; শেষে listener বন্ধ করে
    # কেন লাগছে: appflow §2-এর স্টার্টআপ ক্রম — bind → state → থ্রেড → উইন্ডো → লুপ
    # real world-এ এটা কোথায় দেখা যায়: সব GUI প্রোগ্রামের main()/entry point এভাবেই সেটআপ করে
    args = parse_args()  # ভুল --me হলে argparse এখানেই usage দেখিয়ে বেরিয়ে যায়
    global _me, _window, _state, _activity, _listener, _dev, _sync, _tray, _alert_settings
    global _animating
    _me = args.me        # আমার হুক এই জনের status চালায়; অন্যজন সঙ্গী (peer)
    _dev = args.dev
    peer = "rifat" if _me == "samee" else "samee"
    port = config.LISTEN_PORT if args.port is None else args.port
    idle = config.IDLE_TIMEOUT if args.idle is None else args.idle

    _state = state.AppState(_me, peer, wall_now())
    _activity = activity.Activity(idle_timeout=idle)
    _listener = listener.Listener(on_event=_events.put,
                                  on_show=lambda: _commands.put(tray.SHOW),
                                  port=port)

    if not _listener.try_bind():          # পোর্ট দখল = আরেকটি কপি চলছে (appflow §2)
        if listener.ping_show(port=port):
            print("Work•Sleep•Repeat is already running — showed its window.")
            return 0
        print("Port %d is busy but did not answer — is another app using it?" % port)
        return 1
    _listener.start()
    print("WSR: listening on http://%s:%d  (idle timeout %ds%s)"
          % (config.LISTEN_HOST, port, idle, ", dev mode" if _dev else ""))

    settings = userconfig.load(me=_me)
    _alert_settings = tray.AlertSettings(store=userconfig.save_alerts)
    _alert_settings.load(dict(settings.alerts))       # আগে বন্ধ করা অ্যালার্ট বন্ধই থাকে
    _sync = _start_sync(args.offline, peer, settings)

    _window = make_window(visible=not args.tray)      # উইন্ডো + GL কনটেক্সট (এখন GLUT নয়, pyglet)
    init_scene(*_window.get_framebuffer_size())       # প্রজেকশন/blending + display list তৈরি

    _tray = tray.Tray(_commands, settings_store=_alert_settings)
    _tray.start()                                     # নিজের থ্রেডে; উইন্ডো ছোঁয় না (techspec §3)

    if not args.tray:                                 # লুকিয়ে শুরু হলে অ্যানিমেশন টিক লাগে না
        pyglet.clock.schedule_interval(tick, TICK_SECONDS)                # ~60 FPS অ্যানিমেশন টিক
        _animating = True
    pyglet.clock.schedule_interval(_pump, config.PUMP_SECONDS)            # ট্রে কমান্ড + হুক ইভেন্ট
    pyglet.clock.schedule_interval(state_tick, config.STATE_TICK_SECONDS)  # ডিটেকশন + অ্যালার্ট

    _push_status(wall_now())                          # শুরুতেই নিজের অবস্থা জানিয়ে দিই
    print("WSR: tray ready%s" % (" (started hidden)" if args.tray else ""))

    try:
        # interval=None → pyglet নিজে রিড্র schedule করে না; আঁকা হয় tick() থেকে (_redraw)
        pyglet.app.run(interval=None)                 # ইভেন্ট লুপ; ট্রে → Quit না চাপা পর্যন্ত চলবে
    finally:
        if _tray is not None:
            _tray.stop()                              # ট্রে আইকন সরিয়ে দিই (zombie আইকন থাকবে না)
        if _sync is not None:
            _sync.stop()
        _listener.stop()                              # পোর্ট ছেড়ে দিই, যাতে পরের কপি bind করতে পারে
    return 0


if __name__ == "__main__":
    sys.exit(main())
