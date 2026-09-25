"""pixel.py — নিচু স্তরের ড্রয়িং হেল্পার: hex→rgb, set_color, pixel/rect/box/sprite/text।"""

from functools import lru_cache

from OpenGL.GL import (
    glBegin,
    glBitmap,
    glColor4f,
    glEnd,
    glPixelStorei,
    glRasterPos2f,
    glVertex2f,
    GL_QUADS,
    GL_UNPACK_ALIGNMENT,
)
from OpenGL.GLUT import glutBitmapCharacter, glutBitmapWidth

import config

BULLET = "•"                                # '•' — GLUT bitmap font এই কোড (8226) আঁকতে পারে না
_BULLET_BITS = bytes((0xF0, 0xF0, 0xF0, 0xF0))   # 4×4 ভরাট বর্গ (প্রতি বাইটের উপরের ৪টি বিট সেট)
DASH = "—"                                   # '—' em-dash (U+2014, 8212) — একইভাবে bitmap font আঁকে না
_DASH_BITS = bytes((0xFC, 0xFC))             # 6×2 অনুভূমিক বার (প্রতি বাইটের উপরের ৬টি বিট সেট)


@lru_cache(maxsize=None)
def hex_to_rgb(hex_color):
    # কী করছে: "#4a6aa8"-এর মতো হেক্স স্ট্রিংকে 0–1 রেঞ্জের (r, g, b) ফ্লোটে বদলাচ্ছে
    # কেন লাগছে: OpenGL রঙ চায় 0–1 ফ্লোটে, কিন্তু আমরা config-এ রঙ রাখি পড়ার সুবিধায় হেক্সে
    # real world-এ এটা কোথায় দেখা যায়: CSS/ডিজাইন টুল হেক্স কোডকে GPU-র ফ্লোট কালারে রূপান্তর করে
    # lru_cache: রঙ গোনা মুষ্টিমেয়, তাই একবার পার্স করে মনে রাখলে প্রতি ফ্রেমে বারবার পার্স লাগে না (দ্রুত)
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def set_color(color, alpha=1.0):
    # কী করছে: হেক্স রঙ ও alpha থেকে বর্তমান OpenGL ড্র-কালার সেট করছে (glColor4f)
    # কেন লাগছে: এরপর যা আঁকা হবে সব এই রঙে আঁকবে; alpha দিয়ে স্বচ্ছতা (আলো/ছায়া) আসে
    # real world-এ এটা কোথায় দেখা যায়: গ্রাফিক্স API-র "current color" state; পেইন্টে রঙ বেছে নেওয়া
    r, g, b = hex_to_rgb(color)
    glColor4f(r, g, b, alpha)


def draw_rect(x, y, w, h, color, alpha=1.0):
    # কী করছে: (x, y) থেকে w×h মাপের একটি ভরাট আয়তক্ষেত্র একটিমাত্র quad হিসেবে আঁকছে
    # কেন লাগছে: প্রতি পিক্সেল আলাদা না এঁকে এক quad-এ আঁকলে অনেক দ্রুত হয় (Python-এ জরুরি)
    # real world-এ এটা কোথায় দেখা যায়: সব 2D রেন্ডারার rectangle/sprite quad দিয়ে আঁকে
    set_color(color, alpha)
    glBegin(GL_QUADS)                 # চার কোণা দিয়ে একটি চতুর্ভুজ শুরু
    glVertex2f(x, y)                  # উপরে-বাঁ
    glVertex2f(x + w, y)             # উপরে-ডান
    glVertex2f(x + w, y + h)        # নিচে-ডান
    glVertex2f(x, y + h)           # নিচে-বাঁ
    glEnd()


def draw_pixel(x, y, color, alpha=1.0):
    # কী করছে: এক গ্রিড সেল (1×1) রঙ করছে — আসলে ১×১ মাপের একটি ছোট rectangle
    # কেন লাগছে: স্প্রাইট ও সূক্ষ্ম ডিটেইল পিক্সেল-বাই-পিক্সেল আঁকতে লাগে
    # real world-এ এটা কোথায় দেখা যায়: পিক্সেল-আর্ট এডিটরে (যেমন Aseprite) একেকটা ঘর রঙ করা
    draw_rect(x, y, 1, 1, color, alpha)


def draw_box(x, y, w, h, fill, outline=config.OUTLINE):
    # কী করছে: w×h আয়তক্ষেত্র fill রঙে ভরে তার চারপাশে ১-পিক্সেল outline বর্ডার আঁকছে
    # কেন লাগছে: design.md-এর box() মানেই "ভরাট + ১px আউটলাইন"; আসবাবকে আলাদা করে দেখাতে
    # real world-এ এটা কোথায় দেখা যায়: UI-তে border সহ বাটন/কার্ড; পিক্সেল আর্টে আউটলাইনড অবজেক্ট
    draw_rect(x, y, w, h, fill)                # ভেতরটা ভরাট
    draw_rect(x, y, w, 1, outline)            # উপরের বর্ডার
    draw_rect(x, y + h - 1, w, 1, outline)   # নিচের বর্ডার
    draw_rect(x, y, 1, h, outline)          # বাঁ বর্ডার
    draw_rect(x + w - 1, y, 1, h, outline)  # ডান বর্ডার


def draw_sprite(x, y, rows, color_map):
    # কী করছে: টেক্সট-গ্রিড স্প্রাইট আঁকছে; প্রতিটি অক্ষর color_map-এর রঙে এক পিক্সেল, '.' বাদ
    # কেন লাগছে: ক্যারেক্টার/গাছ/আইকন টেক্সট আকারে লিখে রেখে সহজে আঁকা ও এডিট করা যায়
    # real world-এ এটা কোথায় দেখা যায়: রেট্রো গেমে টাইল/স্প্রাইট শিট থেকে অক্ষর-ম্যাপ করে আঁকা
    for dy, row in enumerate(rows):               # dy = উপর থেকে সারি নম্বর (y নিচের দিকে বাড়ে)
        for dx, ch in enumerate(row):             # dx = বাঁ থেকে কলাম নম্বর
            if ch == "." or ch not in color_map:  # '.' বা অচেনা অক্ষর = স্বচ্ছ, আঁকা হবে না
                continue
            draw_pixel(x + dx, y + dy, color_map[ch])


def draw_text(x, y, text, color, font):
    # কী করছে: (x, y) গ্রিড অবস্থানে GLUT bitmap font দিয়ে text আঁকছে; '•' পেলে হাতে ছোট বর্গ
    #           এঁকে pen-কে একটি স্বাভাবিক অক্ষরের সমান ডানে সরিয়ে দিচ্ছে
    # কেন লাগছে: GLUT bitmap font শুধু 1–255 কোডের অক্ষর চেনে, তাই '•' (U+2022 = 8226)-এর প্রস্থ 0;
    #           এমনি আঁকলে বুলেট উধাও হয় ও পরের অক্ষর এগোয় না — তাই বুলেট নিজে এঁকে pen সরাই
    # real world-এ এটা কোথায় দেখা যায়: ফন্টে না-থাকা glyph-এর বদলে fallback চিহ্ন আঁকা (tofu box)
    set_color(color)
    glRasterPos2f(x, y)                          # লেখা শুরুর অবস্থান (গ্রিড কোঅর্ডিনেট)
    advance = glutBitmapWidth(font, ord("o"))    # একটি "স্বাভাবিক" অক্ষরের প্রস্থ (window pixel-এ)
    for ch in text:
        if ch == BULLET:
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)   # 4-চওড়া bitmap ঠিকভাবে পড়তে alignment=1
            # 4×4 বর্গ আঁকে (লেখার উল্লম্ব মাঝ বরাবর) এবং pen-কে normal char-এর সমান সরায়
            glBitmap(4, 4, -2.0, -2.0, float(advance), 0.0, _BULLET_BITS)
        elif ch == DASH:
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)   # 6-চওড়া bitmap-এর জন্য alignment=1
            # 6×2 অনুভূমিক বার আঁকে (baseline থেকে ~4px উপরে, লেখার মাঝ বরাবর) ও pen সরায়
            glBitmap(6, 2, 0.0, -4.0, float(advance), 0.0, _DASH_BITS)
        else:
            glutBitmapCharacter(font, ord(ch))      # এক অক্ষর এঁকে pen ডান দিকে সরায়
