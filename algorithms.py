"""algorithms.py — হাতে লেখা CG অ্যালগরিদম: Bresenham, cubic Bezier, boundary fill, scanline circle, Cohen-Sutherland।

কোনো লাইব্রেরি এই অ্যালগরিদমগুলো করে দেয় না — সব হাতে লেখা (কোর্সের শর্ত ও viva-র মূল অংশ)।
"""

import math

# Cohen-Sutherland region code-এর নামযুক্ত বিট (design/techspec §4.3)।
# আমাদের গ্রিডে y নিচের দিকে বাড়ে, তাই "TOP" মানে ছোট y (উপরে), "BOTTOM" মানে বড় y (নিচে)।
INSIDE = 0   # 0000 — রেক্টের ভেতরে
LEFT = 1     # 0001 — বাঁ সীমার বাইরে (x < xmin)
RIGHT = 2    # 0010 — ডান সীমার বাইরে (x > xmax)
BOTTOM = 4   # 0100 — নিচের সীমার বাইরে (y > ymax)
TOP = 8      # 1000 — উপরের সীমার বাইরে (y < ymin)


def bresenham_line(x0, y0, x1, y1):
    # কী করছে: (x0,y0) থেকে (x1,y1) পর্যন্ত সরল রেখার পিক্সেল ঘরগুলোর তালিকা বের করছে (integer গণিতে)
    # কেন লাগছে: গ্রিডে রেখা আঁকতে কোন কোন ঘর রঙ করতে হবে জানা দরকার; float ছাড়া দ্রুত ও নিখুঁত
    # real world-এ এটা কোথায় দেখা যায়: GPU/প্রিন্টার/Google Maps রাস্টারাইজেশনে রেখা→পিক্সেল
    points = []
    dx = abs(x1 - x0)              # অনুভূমিক দূরত্ব (ধনাত্মক)
    dy = abs(y1 - y0)             # উল্লম্ব দূরত্ব (ধনাত্মক)
    sx = 1 if x0 < x1 else -1     # x কোন দিকে এগোবে (+1 ডানে, -1 বাঁয়ে)
    sy = 1 if y0 < y1 else -1     # y কোন দিকে এগোবে (+1 নিচে, -1 উপরে)
    err = dx - dy                 # সিদ্ধান্ত-চলক: কখন x, কখন y ধাপ নেবে তা ঠিক করে
    x, y = x0, y0
    while True:
        points.append((x, y))     # বর্তমান ঘর তালিকায় যোগ
        if x == x1 and y == y1:   # শেষ বিন্দুতে পৌঁছালে থামি
            break
        e2 = 2 * err              # ভগ্নাংশ এড়াতে err-কে ২ গুণ করে তুলনা করি
        if e2 > -dy:              # x-এ এক ধাপ নেওয়ার সময় হয়েছে?
            err -= dy
            x += sx
        if e2 < dx:              # y-তে এক ধাপ নেওয়ার সময় হয়েছে?
            err += dx
            y += sy
    return points


def cubic_bezier(p0, p1, p2, p3, t):
    # কী করছে: ৪টি কন্ট্রোল পয়েন্ট আর t (0–1) থেকে cubic Bezier বক্ররেখার একটি বিন্দু (x,y) দেয়
    # কেন লাগছে: ক্যারেক্টার বিছানা থেকে ডেস্কে বাঁকা পথে হাঁটে — সেই মসৃণ পথ এই সূত্রে তৈরি
    # real world-এ এটা কোথায় দেখা যায়: ফন্ট ডিজাইন, গাড়ি মডেলিং, অ্যানিমেশন path, Illustrator-এর pen
    u = 1 - t                              # (1 - t), সূত্র ছোট রাখতে
    # B(t) = (1-t)³P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³P3  — প্রতিটি অক্ষে আলাদা করে
    x = (u * u * u * p0[0] + 3 * u * u * t * p1[0]
         + 3 * u * t * t * p2[0] + t * t * t * p3[0])
    y = (u * u * u * p0[1] + 3 * u * u * t * p1[1]
         + 3 * u * t * t * p2[1] + t * t * t * p3[1])
    return (x, y)


def bezier_points(p0, p1, p2, p3, steps):
    # কী করছে: t = 0 থেকে 1 পর্যন্ত সমান steps ভাগে বক্ররেখা থেকে (steps+1)টি বিন্দু নেয়
    # কেন লাগছে: পুরো পথটা আঁকতে/দেখাতে (ডিবাগ ভিউ) অনেকগুলো বিন্দু লাগে
    # real world-এ এটা কোথায় দেখা যায়: ভেক্টর সফটওয়্যার বক্ররেখাকে ছোট সরলরেখায় ভেঙে আঁকে
    pts = []
    for i in range(steps + 1):
        t = i / steps                      # 0, 1/steps, ..., 1
        pts.append(cubic_bezier(p0, p1, p2, p3, t))
    return pts


def ease_in_out(t):
    # কী করছে: smoothstep — t (0–1) কে এমনভাবে বদলায় যেন শুরু ও শেষ ধীর, মাঝে দ্রুত
    # কেন লাগছে: সমান গতিতে হাঁটা যান্ত্রিক লাগে; easing দিলে হাঁটা স্বাভাবিক/জীবন্ত দেখায়
    # real world-এ এটা কোথায় দেখা যায়: সব UI/গেম অ্যানিমেশনে ease-in-out টাইমিং
    return t * t * (3 - 2 * t)             # smoothstep সূত্র


def boundary_fill(grid, x, y, fill, boundary):
    # কী করছে: (x,y) থেকে শুরু করে ৪-দিকে ছড়িয়ে boundary রঙে ঘেরা এলাকা fill রঙে ভরে (স্ট্যাক দিয়ে)
    # কেন লাগছে: এলোমেলো কম্বলের ভেতরটা ভরাট করতে; রিকার্শন নয়, কারণ Python-এ গভীর রিকার্শন crash করে
    # real world-এ এটা কোথায় দেখা যায়: Photoshop/MS Paint-এর "paint bucket" টুল
    height = len(grid)
    width = len(grid[0])
    stack = [(x, y)]                       # নিজেরা স্ট্যাক রাখছি (call stack নয়)
    while stack:
        cx, cy = stack.pop()              # স্ট্যাকের উপরের ঘর নিই
        if cx < 0 or cy < 0 or cx >= width or cy >= height:
            continue                       # গ্রিডের বাইরে হলে বাদ
        current = grid[cy][cx]
        if current == boundary or current == fill:
            continue                       # সীমানা বা আগেই ভরা হলে থামি (নাহলে অসীম লুপ)
        grid[cy][cx] = fill               # এই ঘর ভরি
        stack.append((cx + 1, cy))        # ৪ প্রতিবেশী পরে দেখার জন্য স্ট্যাকে দিই
        stack.append((cx - 1, cy))
        stack.append((cx, cy + 1))
        stack.append((cx, cy - 1))


def scanline_circle(cx, cy, r):
    # কী করছে: r ব্যাসার্ধের বৃত্তকে সারি-ধরে ভরাট করতে প্রতিটি সারির (y, x_start, x_end) span দেয়
    # কেন লাগছে: ল্যাম্পের গোল glow ভরাট করতে; পিক্সেল-আর্ট ধাপযুক্ত গোল আভা তৈরি হয়
    # real world-এ এটা কোথায় দেখা যায়: রাস্টার গ্রাফিক্সে বৃত্ত/উপবৃত্ত ভরাট (scanline fill)
    spans = []
    for dy in range(-r, r + 1):           # কেন্দ্র থেকে উপরে-নিচে প্রতিটি সারি
        half = int(math.sqrt(r * r - dy * dy))  # এই সারিতে অর্ধ-প্রস্থ (বৃত্তের সমীকরণ থেকে)
        y = cy + dy
        spans.append((y, cx - half, cx + half))  # সারির বাঁ থেকে ডান প্রান্ত
    return spans


def compute_outcode(x, y, rect):
    # কী করছে: একটি বিন্দু রেক্টের কোন দিকে বাইরে, তা ৪ বিটের কোড (TOP/BOTTOM/LEFT/RIGHT) দিয়ে বলে
    # কেন লাগছে: Cohen-Sutherland ক্লিপিং-এ দ্রুত বলে দেয় বিন্দু ভেতরে না বাইরে, বাইরে হলে কোন দিকে
    # real world-এ এটা কোথায় দেখা যায়: GPU pipeline-এ স্ক্রিনের বাইরের অংশ বাদ দেওয়া (clipping)
    xmin, ymin, xmax, ymax = rect
    code = INSIDE
    if x < xmin:
        code |= LEFT
    elif x > xmax:
        code |= RIGHT
    if y < ymin:                          # y ছোট = উপরে (গ্রিডে y নিচে বাড়ে)
        code |= TOP
    elif y > ymax:
        code |= BOTTOM
    return code


def cohen_sutherland(x0, y0, x1, y1, rect):
    # কী করছে: (x0,y0)-(x1,y1) রেখাকে rect-এর ভেতরের অংশে কেটে দেয়; পুরো বাইরে হলে None
    # কেন লাগছে: ল্যাম্পের আলোর রশ্মিকে রুমের সীমায় কেটে দিই, যাতে আলো অন্যজনের রুমে না যায়
    # real world-এ এটা কোথায় দেখা যায়: GPU rendering pipeline-এ viewport-এর বাইরের রেখা কাটা
    xmin, ymin, xmax, ymax = rect
    out0 = compute_outcode(x0, y0, rect)
    out1 = compute_outcode(x1, y1, rect)
    while True:
        if out0 == INSIDE and out1 == INSIDE:
            return (x0, y0, x1, y1)        # দুই প্রান্তই ভেতরে → পুরো রেখা রাখি (accept)
        if out0 & out1:
            return None                    # দুই প্রান্ত একই বাইরের অঞ্চলে → পুরো রেখা বাইরে (reject)
        out = out0 if out0 != INSIDE else out1  # যে প্রান্ত বাইরে, সেটি বেছে নিই
        # রেক্টের যে সীমা প্রান্তটি পেরিয়েছে, সেই সীমায় রেখার ছেদবিন্দু বের করি
        if out & TOP:
            x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
            y = ymin
        elif out & BOTTOM:
            x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
            y = ymax
        elif out & RIGHT:
            y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
            x = xmax
        else:  # LEFT
            y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
            x = xmin
        # বাইরের প্রান্তটিকে ছেদবিন্দুতে সরিয়ে তার outcode আবার হিসাব করি, তারপর লুপ চলবে
        if out == out0:
            x0, y0 = x, y
            out0 = compute_outcode(x0, y0, rect)
        else:
            x1, y1 = x, y
            out1 = compute_outcode(x1, y1, rect)


# =========================================================================
# স্ব-পরীক্ষা (self-test): `python algorithms.py` চালালে প্রতিটি অ্যালগরিদমের PASS/FAIL ছাপে
# =========================================================================

def _check(name, condition):
    # কী করছে: একটি শর্ত সত্য হলে PASS, নাহলে FAIL ছাপে ও গণনা রাখে
    # কেন লাগছে: প্রতিটি অ্যালগরিদমের ফল প্রত্যাশিত কিনা তা পরিষ্কার করে দেখাতে
    # real world-এ এটা কোথায় দেখা যায়: unit test framework (pytest ইত্যাদি)-এর assert
    print(("PASS" if condition else "FAIL"), "-", name)
    return condition


def _run_self_test():
    # কী করছে: সব অ্যালগরিদমের ছোট ছোট কেস চালিয়ে PASS/FAIL রিপোর্ট করে
    # কেন লাগছে: হাতে লেখা অ্যালগরিদম ঠিক আছে কিনা এক নজরে যাচাই (viva-তে দেখানোর জন্য)
    # real world-এ এটা কোথায় দেখা যায়: লাইব্রেরির test suite চালিয়ে সব সবুজ কিনা দেখা
    ok = True

    # ---- bresenham_line ----
    line = bresenham_line(0, 0, 7, 3)
    expected = [(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2), (6, 3), (7, 3)]
    ok &= _check("bresenham (0,0)->(7,3) exact", line == expected)

    rev = bresenham_line(3, 7, 0, 0)       # steep + reversed
    ok &= _check("bresenham (3,7)->(0,0) endpoints", rev[0] == (3, 7) and rev[-1] == (0, 0))
    ok &= _check("bresenham (3,7)->(0,0) steep len", len(rev) == 8)

    vert = bresenham_line(2, 0, 2, 5)
    ok &= _check("bresenham vertical", vert == [(2, 0), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5)])
    horiz = bresenham_line(0, 3, 5, 3)
    ok &= _check("bresenham horizontal", horiz == [(0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3)])

    # ---- cubic_bezier / ease_in_out ----
    p0, p1, p2, p3 = (0, 0), (0, 10), (10, 10), (10, 0)
    ok &= _check("bezier t=0 == P0", cubic_bezier(p0, p1, p2, p3, 0) == (0, 0))
    ok &= _check("bezier t=1 == P3", cubic_bezier(p0, p1, p2, p3, 1) == (10, 0))
    mid = cubic_bezier(p0, p1, p2, p3, 0.5)
    ok &= _check("bezier t=0.5 == (5.0, 7.5)", mid == (5.0, 7.5))
    ok &= _check("ease_in_out 0/0.5/1",
                 ease_in_out(0) == 0 and ease_in_out(0.5) == 0.5 and ease_in_out(1) == 1)

    # ---- boundary_fill: 7x7 grid, square outline (boundary=1), fill inside with 2 ----
    grid = [[0] * 7 for _ in range(7)]
    for i in range(1, 6):                  # (1,1)..(5,5) বর্গের সীমানা আঁকি
        grid[1][i] = 1
        grid[5][i] = 1
        grid[i][1] = 1
        grid[i][5] = 1
    boundary_fill(grid, 3, 3, 2, 1)        # ভেতর থেকে ভরাট
    inside_ok = all(grid[y][x] == 2 for y in range(2, 5) for x in range(2, 5))
    outside_ok = grid[0][0] == 0 and grid[6][6] == 0 and grid[0][3] == 0
    border_ok = grid[1][1] == 1 and grid[5][5] == 1
    ok &= _check("boundary_fill inside filled", inside_ok)
    ok &= _check("boundary_fill outside untouched", outside_ok)
    ok &= _check("boundary_fill border intact", border_ok)

    # ---- scanline_circle r=3 ----
    spans = scanline_circle(0, 0, 3)
    ok &= _check("circle r=3 has 7 rows", len(spans) == 7)
    halves = [xe for (_, _, xe) in spans]  # cx=0 বলে x_end = half-width
    ok &= _check("circle r=3 half-widths [0,2,2,3,2,2,0]", halves == [0, 2, 2, 3, 2, 2, 0])
    ok &= _check("circle symmetric top/bottom", spans[0][2] == spans[-1][2] and spans[1][2] == spans[-2][2])

    # ---- cohen_sutherland: rect (0,0,10,10) ----
    rect = (0, 0, 10, 10)
    ok &= _check("clip fully inside unchanged", cohen_sutherland(2, 2, 8, 8, rect) == (2, 2, 8, 8))
    ok &= _check("clip fully outside None", cohen_sutherland(11, 11, 20, 20, rect) is None)
    ok &= _check("clip crossing one edge", cohen_sutherland(5, 5, 15, 5, rect) == (5, 5, 10, 5))
    ok &= _check("clip crossing two edges", cohen_sutherland(-5, 5, 15, 5, rect) == (0, 5, 10, 5))
    ok &= _check("clip entirely left None", cohen_sutherland(-5, 2, -1, 8, rect) is None)

    print()
    print("ALL PASS" if ok else "SOME FAILED")
    return ok


if __name__ == "__main__":
    _run_self_test()
