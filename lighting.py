"""lighting.py — রুমের উপর আলো/ছায়ার স্তর: অন্ধকার overlay, উষ্ণ glow, আলোর রশ্মি, স্ক্রিন আভা ও ডিবাগ ভিউ।

সব ফাংশন রুম-লোকাল কোঅর্ডিনেটে আঁকে; কলার (main) translate/reflect প্রয়োগ করে (design §8, §11)।
আঁকার ক্রম: অন্ধকার overlay → উষ্ণ glow → আলোর রশ্মি → স্ক্রিন আভা → (তারপর main emissive অংশ আঁকে)।
"""

import math

from OpenGL.GL import (
    glBegin,
    glEnd,
    glVertex2f,
    GL_LINE_LOOP,
    GL_LINE_STRIP,
    GL_LINES,
    GL_QUADS,
)

from algorithms import bezier_points, bresenham_line, cohen_sutherland, scanline_circle
from pixel import draw_rect, set_color

import config


def _emit_span(y, x0, x1):
    # কী করছে: খোলা glBegin(GL_QUADS)-এর ভেতরে এক সারির (y) x0..x1 ঘরগুলো এক quad হিসেবে জমা দেয়
    # কেন লাগছে: প্রতি সারির জন্য আলাদা glBegin/glEnd না ডেকে সব একসাথে পাঠালে অনেক দ্রুত হয়
    # real world-এ এটা কোথায় দেখা যায়: batch rendering — বহু কোয়াড এক draw call-এ পাঠানো
    glVertex2f(x0, y)              # উপরে-বাঁ (x0..x1 inclusive → ডান প্রান্ত x1+1)
    glVertex2f(x1 + 1, y)          # উপরে-ডান
    glVertex2f(x1 + 1, y + 1)      # নিচে-ডান
    glVertex2f(x0, y + 1)          # নিচে-বাঁ


def draw_darkness(working):
    # কী করছে: পুরো রুমের উপর একটি NIGHT রঙের স্বচ্ছ quad বসায়; কাজ করলে হালকা (0.30), নাহলে গাঢ় (0.40)
    # কেন লাগছে: রাতের কোজি ভাব দেয়; কাজ করলে ল্যাম্প জ্বলে বলে রুম একটু কম অন্ধকার হয়
    # real world-এ এটা কোথায় দেখা যায়: গেমে দিন/রাত overlay বা "ambient darkness" স্তর
    alpha = config.DARK_WORK if working else config.DARK_IDLE
    draw_rect(0, 0, config.ROOM_W, config.ROOM_H, config.NIGHT, alpha)


def draw_glow():
    # কী করছে: ল্যাম্পের কেন্দ্র ঘিরে ৫টি ভিন্ন ব্যাসার্ধের বৃত্ত (scanline_circle) একই উষ্ণ রঙে স্তরে স্তরে আঁকে
    # কেন লাগছে: স্বচ্ছ বৃত্তগুলো জমে (alpha stacking) কেন্দ্রকে উজ্জ্বল করে — পিক্সেল-আর্ট ধাপযুক্ত আভা
    # real world-এ এটা কোথায় দেখা যায়: বাতির চারপাশে আলোর radial falloff (উজ্জ্বল কেন্দ্র, ম্লান কিনারা)
    xmin, ymin, xmax, ymax = config.ROOM_CLIP_RECT
    cx, cy = config.GLOW_CENTER
    set_color(config.GLOW_WARM, config.GLOW_ALPHA)   # একবার রঙ সেট; সব বৃত্ত একই রঙ+alpha
    glBegin(GL_QUADS)
    for r in config.GLOW_RADII:                      # বড় থেকে ছোট বৃত্ত
        for (y, xs, xe) in scanline_circle(cx, cy, r):
            if y < ymin or y > ymax:                 # রুমের বাইরের সারি বাদ (point clipping)
                continue
            xs = max(xs, xmin)                       # রুমের বাঁ সীমায় আটকাই
            xe = min(xe, xmax)                       # রুমের ডান সীমায় আটকাই (ডিভাইডার পেরোয় না)
            if xs > xe:
                continue                             # ক্লিপ করে সারিতে কিছু না থাকলে বাদ
            _emit_span(y, xs, xe)
    glEnd()


def draw_screen_glow():
    # কী করছে: মনিটরের কাছে একটি ছোট নীল বৃত্ত (scanline_circle) কম alpha-য় আঁকে, রুমে ক্লিপ করে
    # কেন লাগছে: চালু স্ক্রিন থেকে ঠান্ডা নীল আভা ছড়ানোর ভাব দেয় (উষ্ণ ল্যাম্প আলোর বিপরীতে)
    # real world-এ এটা কোথায় দেখা যায়: অন্ধকার ঘরে মনিটরের নীলচে আভা মুখে/দেয়ালে পড়া
    xmin, ymin, xmax, ymax = config.ROOM_CLIP_RECT
    cx, cy = config.SCREEN_GLOW_CENTER
    set_color(config.GLOW_SCREEN, config.SCREEN_GLOW_ALPHA)
    glBegin(GL_QUADS)
    for (y, xs, xe) in scanline_circle(cx, cy, config.SCREEN_GLOW_RADIUS):
        if y < ymin or y > ymax:
            continue
        xs = max(xs, xmin)
        xe = min(xe, xmax)
        if xs > xe:
            continue
        _emit_span(y, xs, xe)
    glEnd()


def _ray_endpoints():
    # কী করছে: RAY_ORIGIN থেকে সোজা নিচ বরাবর ±RAY_SPREAD_DEG পাখা মেলে RAY_COUNT রশ্মির (x0,y0,x1,y1) দেয়
    # কেন লাগছে: ল্যাম্প থেকে নামা রশ্মিগুলোর দিক/দৈর্ঘ্য একবারে হিসাব করে রাখতে (ক্লিপ ও আঁকা দুটোতেই লাগে)
    # real world-এ এটা কোথায় দেখা যায়: স্পটলাইটের cone — এক উৎস থেকে নানা কোণে রশ্মি
    ox, oy = config.RAY_ORIGIN
    rays = []
    for i in range(config.RAY_COUNT):
        frac = i / (config.RAY_COUNT - 1)                 # 0..1 সমান ভাগে
        ang = math.radians((frac * 2 - 1) * config.RAY_SPREAD_DEG)  # -spread .. +spread
        ex = ox + config.RAY_LENGTH * math.sin(ang)       # x-ঘটক: বাঁ/ডানে হেলা
        ey = oy + config.RAY_LENGTH * math.cos(ang)       # y-ঘটক: নিচে (cos, কারণ সোজা নিচ = 0°)
        rays.append((ox, oy, ex, ey))
    return rays


def _draw_ray_cells(x0, y0, x1, y1):
    # কী করছে: (x0,y0)-(x1,y1) রেখার bresenham ঘরগুলো খোলা glBegin(GL_QUADS)-এ quad হিসেবে জমা দেয়
    # কেন লাগছে: রশ্মি হাতে-লেখা bresenham দিয়েই রাস্টারাইজ হয় (CG technique দেখানো viva-র জন্য)
    # real world-এ এটা কোথায় দেখা যায়: রেখা → পিক্সেল রূপান্তর (line rasterization)
    for cx, cy in bresenham_line(int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))):
        _emit_span(cy, cx, cx)     # এক ঘর = ১×১ quad


def draw_rays(debug=False):
    # কী করছে: ল্যাম্পের রশ্মিগুলো cohen_sutherland দিয়ে রুমে কেটে bresenham-এ আঁকে;
    #           debug হলে কাটার আগেরটা লাল ও কাটার পরেরটা সবুজে, নাহলে উষ্ণ রঙে কম alpha-য়
    # কেন লাগছে: না কাটলে আলো দেয়াল পেরিয়ে অন্যজনের রুমে যেত; debug-এ ক্লিপিং চোখে দেখানো যায়
    # real world-এ এটা কোথায় দেখা যায়: GPU pipeline-এ viewport-এর বাইরের রেখা ক্লিপ করা
    rays = _ray_endpoints()
    rect = config.ROOM_CLIP_RECT

    if debug:
        # আগে পুরো (unclipped) রশ্মি লাল রঙে — রুম ছাড়িয়ে ডিভাইডার পেরিয়ে যায়
        set_color(config.DEBUG_RAY_UNCLIPPED)
        glBegin(GL_QUADS)
        for x0, y0, x1, y1 in rays:
            _draw_ray_cells(x0, y0, x1, y1)
        glEnd()
        # তারপর কাটা (clipped) অংশ সবুজে উপরে — রুমের প্রান্তে থামে (লালের ভেতরের অংশ ঢেকে দেয়)
        set_color(config.DEBUG_RAY_CLIPPED)
        glBegin(GL_QUADS)
        for x0, y0, x1, y1 in rays:
            clip = cohen_sutherland(x0, y0, x1, y1, rect)
            if clip is None:                 # পুরো রশ্মি রুমের বাইরে হলে বাদ
                continue
            _draw_ray_cells(*clip)
        glEnd()
    else:
        # স্বাভাবিক দৃশ্য: শুধু কাটা অংশ উষ্ণ রঙে হালকা alpha-য়
        set_color(config.GLOW_WARM, config.RAY_ALPHA)
        glBegin(GL_QUADS)
        for x0, y0, x1, y1 in rays:
            clip = cohen_sutherland(x0, y0, x1, y1, rect)
            if clip is None:
                continue
            _draw_ray_cells(*clip)
        glEnd()


# =========================================================================
# ডিবাগ ভিউ (design §11): গ্রিড, Bezier বক্ররেখা + কন্ট্রোল পয়েন্ট, clip rectangle
# (রশ্মির লাল/সবুজ অংশ draw_rays(debug=True) আলাদাভাবে আঁকে)
# =========================================================================

def _draw_grid():
    # কী করছে: রুম জুড়ে প্রতি GRID_STEP পিক্সেলে ম্লান উল্লম্ব ও অনুভূমিক লাইন আঁকে
    # কেন লাগছে: viva-তে কোঅর্ডিনেট/মাপ বোঝাতে গ্রিড সাহায্য করে
    # real world-এ এটা কোথায় দেখা যায়: ডিজাইন টুলে (Figma/Photoshop) ruler গ্রিড overlay
    set_color(config.DEBUG_GRID, config.DEBUG_GRID_ALPHA)
    glBegin(GL_LINES)
    x = 0
    while x <= config.ROOM_W:
        glVertex2f(x, 0)
        glVertex2f(x, config.ROOM_H)
        x += config.GRID_STEP
    y = 0
    while y <= config.ROOM_H:
        glVertex2f(0, y)
        glVertex2f(config.ROOM_W, y)
        y += config.GRID_STEP
    glEnd()


def _draw_clip_rect():
    # কী করছে: রুমের clip rectangle-এর সীমানা (ROOM_CLIP_RECT) একটি রেখা-লুপে আঁকে
    # কেন লাগছে: রশ্মি ঠিক এই আয়তক্ষেত্রে কাটা হয়; সবুজ রশ্মি এর প্রান্তে থামে তা দেখাতে
    # real world-এ এটা কোথায় দেখা যায়: rendering-এ clipping/viewport সীমানা visualize করা
    xmin, ymin, xmax, ymax = config.ROOM_CLIP_RECT
    set_color(config.DEBUG_CLIP)
    glBegin(GL_LINE_LOOP)
    glVertex2f(xmin, ymin)
    glVertex2f(xmax, ymin)
    glVertex2f(xmax, ymax)
    glVertex2f(xmin, ymax)
    glEnd()


def _draw_bezier():
    # কী করছে: হাঁটার Bezier বক্ররেখা (WALK_P0..P3) নমুনা করে রেখায় আঁকে ও ৪টি কন্ট্রোল পয়েন্টে ছোট বর্গ বসায়
    # কেন লাগছে: চরিত্র কোন পথে হাঁটে ও কন্ট্রোল পয়েন্ট কোথায় তা চোখে দেখাতে (viva-তে খুব কাজে দেয়)
    # real world-এ এটা কোথায় দেখা যায়: ভেক্টর এডিটরে pen tool-এর curve ও তার handle পয়েন্ট দেখানো
    pts = bezier_points(config.WALK_P0, config.WALK_P1, config.WALK_P2, config.WALK_P3,
                        config.DEBUG_BEZIER_STEPS)
    set_color(config.DEBUG_BEZIER)
    glBegin(GL_LINE_STRIP)
    for x, y in pts:
        glVertex2f(x, y)
    glEnd()
    # ৪টি কন্ট্রোল পয়েন্ট — প্রতিটির চারপাশে ৩×৩ বর্গ
    for px, py in (config.WALK_P0, config.WALK_P1, config.WALK_P2, config.WALK_P3):
        draw_rect(px - 1, py - 1, 3, 3, config.DEBUG_CTRL)


def draw_debug(grid_only=False):
    # কী করছে: ডিবাগ overlay আঁকে — সবসময় গ্রিড; grid_only না হলে clip rect ও Bezier বক্ররেখা+পয়েন্টও
    # কেন লাগছে: key G শুধু গ্রিড চায়, key D পুরো overlay; দুটোই এক জায়গা থেকে সামলাতে
    # real world-এ এটা কোথায় দেখা যায়: এডিটরে "grid only" বনাম "full guides" টগল
    _draw_grid()
    if grid_only:
        return
    _draw_clip_rect()
    _draw_bezier()
