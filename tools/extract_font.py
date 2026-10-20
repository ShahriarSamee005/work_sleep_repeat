"""Dev tool (run once): GLUT bitmap font → our own glyph table (`font.py`).

Phase 10 Step A drops GLUT. freeglut's `glutBitmapCharacter` / `glutBitmapWidth`
abort the process ("called without first calling 'glutInit'"), so the two fonts
the app draws text with must become our own data. This tool renders every
printable ASCII code with the real GLUT font, reads the pixels back, and writes
`font.py` with the exact same glyphs — so text stays pixel-identical after the
window swap.

Needs freeglut (PyOpenGL ships it). Run from the project root:
    python tools/extract_font.py
"""

import os
import sys
from math import ceil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from OpenGL.GL import (
    glClear,
    glClearColor,
    glColor4f,
    glLoadIdentity,
    glMatrixMode,
    glPixelStorei,
    glRasterPos2f,
    glReadBuffer,
    glReadPixels,
    glViewport,
    GL_BACK,
    GL_COLOR_BUFFER_BIT,
    GL_MODELVIEW,
    GL_PACK_ALIGNMENT,
    GL_PROJECTION,
    GL_RGB,
    GL_UNSIGNED_BYTE,
)
from OpenGL.GLU import gluOrtho2D
from OpenGL.GLUT import (
    glutBitmapCharacter,
    glutBitmapWidth,
    glutCreateWindow,
    glutDisplayFunc,
    glutInit,
    glutInitDisplayMode,
    glutInitWindowSize,
    glutMainLoopEvent,
    GLUT_BITMAP_8_BY_13,
    GLUT_BITMAP_9_BY_15,
    GLUT_DOUBLE,
    GLUT_RGBA,
)

W = H = 64                 # ছোট অফস্ক্রিন ক্যানভাস — এক অক্ষর আঁকতে যথেষ্ট
PEN_X, PEN_Y = 16, 24      # raster pen (window পিক্সেল, y উপরে বাড়ে)
BOX = (-8, 24, -16, 24)    # pen-এর সাপেক্ষে পড়ার সীমা: dx শুরু/শেষ, dy শুরু/শেষ
CODES = range(32, 127)     # printable ASCII — অ্যাপের সব লেখা এই সীমায়

FONTS = (
    ("BITMAP_8X13", "8x13", GLUT_BITMAP_8_BY_13),
    ("BITMAP_9X15", "9x15", GLUT_BITMAP_9_BY_15),
)


def setup():
    glutInit([sys.argv[0]])
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(W, H)
    glutCreateWindow(b"font extract")
    glutDisplayFunc(lambda: None)   # freeglut display callback ०াড়া glutMainLoopEvent মানে না
    for _ in range(3):
        glutMainLoopEvent()
    glViewport(0, 0, W, H)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, W, 0, H)      # y উপরে — glBitmap-এর সারি ক্রমের মতোই
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glReadBuffer(GL_BACK)
    glPixelStorei(GL_PACK_ALIGNMENT, 1)


def lit_pixels(font, code):
    # এক অক্ষর কালোর উপর সাদা এঁকে pen-এর সাপেক্ষে জ্বলা পিক্সেলগুলোর (dx, dy) সেট দেয়
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    glColor4f(1.0, 1.0, 1.0, 1.0)
    glRasterPos2f(PEN_X, PEN_Y)
    glutBitmapCharacter(font, code)
    x0, x1, y0, y1 = BOX
    data = glReadPixels(PEN_X + x0, PEN_Y + y0, x1 - x0, y1 - y0, GL_RGB, GL_UNSIGNED_BYTE)
    if hasattr(data, "tobytes"):
        data = data.tobytes()
    data = bytes(data)
    w = x1 - x0
    out = set()
    for row in range(y1 - y0):                 # row 0 = সবচেয়ে নিচে (bottom-up)
        for col in range(w):
            if data[(row * w + col) * 3] > 128:
                out.add((x0 + col, y0 + row))
    return out


def extract(font):
    glyphs = {}
    advances = set()
    for code in CODES:
        glyphs[code] = lit_pixels(font, code)
        advances.add(glutBitmapWidth(font, code))
    if len(advances) != 1:
        raise SystemExit("font is not fixed pitch: widths %s" % sorted(advances))
    return glyphs, advances.pop()


def pack(glyphs):
    # সব glyph-এর common bounding box বের করে প্রতিটিকে glBitmap-এর সারি-বাইটে প্যাক করে
    all_px = [p for px in glyphs.values() for p in px]
    minx = min(p[0] for p in all_px)
    maxx = max(p[0] for p in all_px)
    miny = min(p[1] for p in all_px)
    maxy = max(p[1] for p in all_px)
    w, h = maxx - minx + 1, maxy - miny + 1
    stride = ceil(w / 8.0)
    packed = {}
    for code, px in glyphs.items():
        rows = bytearray(stride * h)
        for (dx, dy) in px:
            col, row = dx - minx, dy - miny
            rows[row * stride + col // 8] |= 0x80 >> (col % 8)   # MSB আগে
        packed[code] = bytes(rows)
    return packed, w, h, -minx, -miny, stride


def main():
    setup()
    out = ['"""GLUT bitmap font glyphs, extracted once by tools/extract_font.py.',
           "",
           "Phase 10 Step A: the app no longer links GLUT, so the two fonts it drew text",
           "with (8x13 and 9x15) live here as data. Every glyph is byte-for-byte what",
           "freeglut drew, so text renders exactly as it did in phases 0-8.",
           "",
           "DO NOT EDIT BY HAND - re-run the tool instead.",
           '"""',
           "",
           ]
    names = []
    for const, label, font in FONTS:
        glyphs, advance = extract(font)
        packed, w, h, xorig, yorig, stride = pack(glyphs)
        print("%s: %d glyphs, box %dx%d, origin (%d, %d), advance %d"
              % (label, len(packed), w, h, xorig, yorig, advance), file=sys.stderr)
        names.append(const)
        out.append("%s = Font(" % const)
        out.append('    name="%s", advance=%d, width=%d, height=%d,'
                   % (label, advance, w, h))
        out.append("    xorig=%.1f, yorig=%.1f," % (xorig, yorig))
        out.append("    glyphs={")
        for code in CODES:
            key = repr(chr(code))                       # উদ্ধৃতি-সেফ: quote/backslash ঠিক রাখে
            out.append("        %-6s: \"%s\"," % (key, packed[code].hex()))
        out.append("    },")
        out.append(")")
        out.append("")
    body = "\n".join(out)
    head = _FONT_CLASS
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "font.py")
    # ক্লাস ডেফিনিশন ডকস্ট্রিং-এর পরে, ডেটার আগে বসাতে হয়
    lines = body.split("\n")
    cut = lines.index("") + 1 if "" in lines else 0
    doc_end = lines.index('"""', 1) + 1
    final = "\n".join(lines[:doc_end]) + "\n" + head + "\n" + "\n".join(lines[doc_end:]) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(final)
    print("wrote %s (%s)" % (path, ", ".join(names)), file=sys.stderr)


_FONT_CLASS = '''
class Font:
    def __init__(self, name, advance, width, height, xorig, yorig, glyphs):
        # কী করছে: এক বিটম্যাপ ফন্ট ধরে রাখে — প্রতি অক্ষরের glBitmap সারি-বাইট ও মাপ
        # কেন লাগছে: GLUT ফন্ট হ্যান্ডলের বদলে এটিই এখন draw_text-এ যায় (GLUT ছাড়া চলতে)
        # real world-এ এটা কোথায় দেখা যায়: গেম/এম্বেডেড UI-তে কম্পাইল-করা bitmap font অ্যাটলাস
        self.name = name
        self.advance = advance                 # fixed-pitch: প্রতি অক্ষরে pen কত px ডানে যায়
        self.width = width                     # glyph box-এর প্রস্থ (px)
        self.height = height                   # glyph box-এর উচ্চতা (px)
        self.xorig = xorig                     # pen থেকে box-এর বাঁ কিনারা (glBitmap xorig)
        self.yorig = yorig                     # pen থেকে box-এর নিচ (glBitmap yorig)
        self.glyphs = {ch: bytes.fromhex(hx) for ch, hx in glyphs.items()}
        self.blank = bytes(len(next(iter(self.glyphs.values()))))   # অজানা অক্ষর = ফাঁকা

    def bits(self, ch):
        # কী করছে: অক্ষরের glBitmap সারি-বাইট দেয়; ফন্টে না থাকলে ফাঁকা box
        # কেন লাগছে: অজানা অক্ষরেও pen এগোনো দরকার, কিন্তু আঁকা হবে না (tofu নয়, ফাঁকা)
        # real world-এ এটা কোথায় দেখা যায়: ফন্টে না-থাকা glyph-এর fallback
        return self.glyphs.get(ch, self.blank)

'''

if __name__ == "__main__":
    main()
