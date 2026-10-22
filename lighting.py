from OpenGL.GL import (
    glBegin,
    glEnd,
    glVertex2f,
    GL_QUADS,
)

from algorithms import scanline_circle
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


def draw_offline():
    # কী করছে: পুরো রুমের উপর আরেকটি NIGHT quad বসায় (DARK_OFFLINE alpha)
    # কেন লাগছে: সঙ্গীর পিসি বন্ধ/নেট নেই — তার রুম বাকি সবের চেয়ে স্পষ্ট ম্লান দেখাতে (design §3)
    # real world-এ এটা কোথায় দেখা যায়: UI-তে "stale/disabled" অংশ ম্লান করে দেওয়া (dimmed state)
    draw_rect(0, 0, config.ROOM_W, config.ROOM_H, config.NIGHT, config.DARK_OFFLINE)


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


