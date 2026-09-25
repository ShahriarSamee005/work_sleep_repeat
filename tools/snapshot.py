"""tools/snapshot.py — dev tool: main.display()-এর ফ্রেম PNG-তে রেন্ডার করে (দৃশ্যমান লুপ ছাড়া)।

একক ছবি:
    python tools/snapshot.py out.png [--samee idle|work] [--rifat idle|work] [--t 0.0]
কন্টাক্ট শিট (এক পাশ toggle করে কয়েকটি মুহূর্ত পাশাপাশি):
    python tools/snapshot.py --sheet out.png --toggle samee --frames 0,0.2,0.6,1.2,2.0,2.5,3.2

--samee/--rifat দুই রুমের settled অবস্থা; --t নকল অ্যানিমেশন ঘড়ি (সেকেন্ড, টাইপিং frame যাচাইয়ে)।
--sheet মোড: দুজন idle থেকে শুরু করে t=0-এ --toggle-এর জনকে work করে, --frames সময়ে Samee-র রুম আঁকে।
Pillow লাগে (requirements-dev.txt)। এটি অ্যাপের অংশ নয়, শুধু যাচাইয়ের টুল।
"""

import argparse
import os
import sys

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
from PIL import Image, ImageDraw

import character as C
import config
import main as app

W, H = config.WINDOW_W, config.WINDOW_H
_DT = 1.0 / 60.0
FAKE_NOW = 1_700_000_000.0   # স্থির virtual epoch — snapshot-এ টাইম কার্ড deterministic রাখতে


def _setup_context():
    # কী করছে: GLUT উইন্ডো/কনটেক্সট বানায়, display callback বাঁধে ও display list তৈরি করে
    # কেন লাগছে: রেন্ডার করতে GL কনটেক্সট ও রুমের list দরকার (একবারই)
    # real world-এ এটা কোথায় দেখা যায়: হেডলেস রেন্ডার টেস্টে অফস্ক্রিন কনটেক্সট সেটআপ
    glutInit([sys.argv[0]])
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(W, H)
    glutCreateWindow(b"snapshot")
    glutDisplayFunc(app.display)
    app.init_scene()
    for _ in range(3):
        glutMainLoopEvent()


def _grab():
    # কী করছে: app.display() একবার এঁকে front buffer পড়ে উল্টে দিয়ে PIL Image ফেরত দেয়
    # কেন লাগছে: একই render path (display) ব্যবহার করে বর্তমান অবস্থার ছবি নিতে
    # real world-এ এটা কোথায় দেখা যায়: screenshot regression test-এ framebuffer capture
    app.display()
    for _ in range(2):
        glutMainLoopEvent()
    glReadBuffer(GL_FRONT)
    glPixelStorei(GL_PACK_ALIGNMENT, 1)
    data = glReadPixels(0, 0, W, H, GL_RGB, GL_UNSIGNED_BYTE)
    if hasattr(data, "tobytes"):
        data = data.tobytes()
    return Image.frombytes("RGB", (W, H), bytes(data)).transpose(Image.FLIP_TOP_BOTTOM)


def _settle(samee_work, rifat_work, seconds=4.0):
    # কী করছে: দুই চরিত্রের target সেট করে যথেষ্ট সময় সিমুলেট করে থিতু (settled) অবস্থায় নেয়
    # কেন লাগছে: --samee work দিলে বসা + device চালু থিতু অবস্থার ছবি চাই (মাঝপথের নয়)
    # real world-এ এটা কোথায় দেখা যায়: টেস্টে "warm up" করে steady state-এ পৌঁছানো
    app.samee.set_working(samee_work)
    app.rifat.set_working(rifat_work)
    for _ in range(int(seconds / _DT)):
        app.samee.update(_DT)
        app.rifat.update(_DT)


def render_single(out, samee, rifat, t, me="samee", samee_worked=0.0, rifat_worked=0.0):
    # কী করছে: দুই রুম নির্দিষ্ট অবস্থায় থিতু করে, প্যানেলের --me সেট করে, কাজ-করা চরিত্রের কার্ড
    #           সময় deterministic করে (since পিছিয়ে), t সময়ে একটি ফ্রেম PNG-তে সেভ করে
    # কেন লাগছে: idle/work, প্যানেল, ও নির্দিষ্ট কার্ড-সময় (যেমন "1h 05m") যাচাই করতে
    # real world-এ এটা কোথায় দেখা যায়: নির্দিষ্ট state-এর reference screenshot
    app._me = me
    app._fake_wall = FAKE_NOW                       # সময় ফ্রিজ — context warm-up-এর display()-ও
                                                    # যেন FAKE_NOW-এই দিন সেট করে (নাহলে দিন mismatch-এ
                                                    # মধ্যরাত রিসেট since মুছে দেয়)
    _setup_context()
    _settle(samee == "work", rifat == "work")
    # কাজ-করা চরিত্রের since পিছিয়ে সেট করে কার্ডে নির্দিষ্ট সময় দেখাই (worked সেকেন্ড)
    if samee == "work":
        app.samee.today_seconds = 0.0
        app.samee.since = FAKE_NOW - samee_worked
    if rifat == "work":
        app.rifat.today_seconds = 0.0
        app.rifat.since = FAKE_NOW - rifat_worked
    app._fake_time = t
    _grab().save(out)
    print("wrote", os.path.abspath(out))


def render_sheet(out, toggle_user, frames, start_work=False):
    # কী করছে: শুরুর অবস্থা (idle বা work) থেকে t=0-এ toggle_user উল্টে দিয়ে প্রতিটি frame সময়ে
    #           toggle_user-এর রুমের টাইল বানিয়ে কন্টাক্ট শিট বানায়
    # কেন লাগছে: এক নজরে ওঠা→হাঁটা→বসা→device-অন (বা উল্টো) ক্রম পাশাপাশি দেখাতে; Rifat হলে পথ mirrored
    # real world-এ এটা কোথায় দেখা যায়: অ্যানিমেশনের contact sheet / frame strip
    _setup_context()
    app.samee = C.Character("samee")     # তাজা অবস্থা (দুজনেই IN_BED)
    app.rifat = C.Character("rifat")
    who = app.samee if toggle_user == "samee" else app.rifat
    if start_work:                       # আগে work-এ থিতু করে তারপর t=0-এ bed-এ টগল
        who.set_working(True)
        for _ in range(int(4.0 / _DT)):
            app.samee.update(_DT)
            app.rifat.update(_DT)
        who.set_working(False)
    else:
        who.set_working(True)            # t=0-এ work-এ টগল

    # কোন পাশ crop করব — যাকে toggle করছি তার রুম
    if toggle_user == "samee":
        box = (0, 0, (config.SAMEE_ORIGIN[0] + config.ROOM_W + 1) * config.PIXEL, H)
    else:
        box = (config.DIVIDER_X * config.PIXEL, 0, config.SCENE_W * config.PIXEL, H)

    sim_t = 0.0
    tiles = []
    for f in frames:
        while sim_t < f - 1e-9:          # সিমুলেশন f সময় পর্যন্ত এগোই
            step = min(_DT, f - sim_t)
            app.samee.update(step)
            app.rifat.update(step)
            sim_t += step
        app._fake_time = f
        full = _grab()
        tiles.append((f, full.crop(box)))
    _compose(tiles).save(out)
    print("wrote", os.path.abspath(out))


def _compose(tiles):
    # কী করছে: টাইলগুলো ছোট করে পাশাপাশি বসিয়ে প্রতিটির উপরে সময় লেবেল দিয়ে একটি শিট বানায়
    # কেন লাগছে: একাধিক মুহূর্ত একসাথে তুলনা করা সহজ হয়
    # real world-এ এটা কোথায় দেখা যায়: sprite sheet / storyboard কম্পোজিশন
    tw, th, label_h, gap = 190, 190, 20, 8
    n = len(tiles)
    sheet = Image.new("RGB", (n * tw + (n + 1) * gap, th + label_h + 2 * gap), (20, 16, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (f, tile) in enumerate(tiles):
        x = gap + i * (tw + gap)
        sheet.paste(tile.resize((tw, th), Image.NEAREST), (x, label_h + gap))
        draw.text((x + 4, 4), "t=%.1f" % f, fill=(240, 235, 220))
    return sheet


def main():
    # কী করছে: আর্গুমেন্ট পড়ে একক ছবি বা কন্টাক্ট শিট রেন্ডার করে
    # কেন লাগছে: এক টুল দিয়ে দুই ধরনের যাচাই-ছবি বানাতে
    # real world-এ এটা কোথায় দেখা যায়: dev CLI-র দুই সাব-মোড
    parser = argparse.ArgumentParser(prog="snapshot.py")
    parser.add_argument("out", nargs="?", help="output PNG (single-frame mode)")
    parser.add_argument("--samee", choices=("idle", "work"), default="idle")
    parser.add_argument("--rifat", choices=("idle", "work"), default="idle")
    parser.add_argument("--t", type=float, default=0.0, help="fake animation clock (seconds)")
    parser.add_argument("--sheet", help="output PNG for contact-sheet mode")
    parser.add_argument("--toggle", choices=("samee", "rifat"), default="samee")
    parser.add_argument("--frames", help="comma-separated seconds, e.g. 0,0.2,0.6,1.2")
    parser.add_argument("--start", choices=("idle", "work"), default="idle",
                        help="contact-sheet starting state before the t=0 toggle")
    parser.add_argument("--debug", action="store_true",
                        help="turn on the debug overlay (grid, Bezier, clip rects, red/green rays)")
    parser.add_argument("--me", choices=("samee", "rifat"), default="samee",
                        help="which user's panel toggle to show")
    parser.add_argument("--samee-worked", type=float, default=0.0,
                        help="seconds to show on Samee's card when Samee is working")
    parser.add_argument("--rifat-worked", type=float, default=0.0,
                        help="seconds to show on Rifat's card when Rifat is working")
    args = parser.parse_args()

    app._debug = args.debug   # ডিবাগ overlay চালু/বন্ধ (main-এর module global সেট করছি)

    if args.sheet:
        frames = [float(x) for x in args.frames.split(",")] if args.frames else [0.0]
        render_sheet(args.sheet, args.toggle, frames, start_work=(args.start == "work"))
    else:
        render_single(args.out or "out.png", args.samee, args.rifat, args.t,
                      me=args.me, samee_worked=args.samee_worked, rifat_worked=args.rifat_worked)

    if app.glutLeaveMainLoop is not None:
        app.glutLeaveMainLoop()


if __name__ == "__main__":
    main()
