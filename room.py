"""room.py — একটি রুমের স্ট্যাটিক অংশ আঁকে (দেয়াল, মেঝে, ডেকর, বিছানা, ডেস্ক, চেয়ার, রাগ)।

সব কোঅর্ডিনেট রুম-লোকাল (design.md §5) এবং config.py থেকে পড়া। কলার (main) translate/reflect করে।
"""

import math

from OpenGL.GL import glEndList, glGenLists, glNewList, GL_COMPILE

import sprites
from algorithms import boundary_fill, bresenham_line
from pixel import draw_box, draw_pixel, draw_rect, draw_sprite

import config

# (rug_name, messy) → display list id; build_room_lists() ভরে দেয়
ROOM_LISTS = {}


def _floor_cell_color(x, y, row):
    # কী করছে: মেঝের এক ঘরের রঙ ঠিক করছে design §5-এর অগ্রাধিকার নিয়মে (লাইন > জোড়া > হাইলাইট > base)
    # কেন লাগছে: তক্তার লাইন, শেষ-জোড়া ও হাইলাইট আলাদা রঙে মেঝেকে সমতল না দেখিয়ে বাস্তব দেখায়
    # real world-এ এটা কোথায় দেখা যায়: প্রোসিজারাল টেক্সচার — সূত্র দিয়ে প্যাটার্নের রঙ বের করা
    if (y - config.FLOOR_TOP) % config.PLANK_H == config.PLANK_H - 1:
        return config.FLOOR_D                     # তক্তার মাঝের লাইন
    if (x + row * config.PLANK_SEAM_SHIFT) % config.PLANK_SEAM_MOD == 0:
        return config.FLOOR_D                      # তক্তার শেষ জোড়া
    if ((y - config.FLOOR_TOP) % config.PLANK_H == 0
            and (x + row * config.PLANK_HL_SHIFT) % config.PLANK_HL_MOD
            < config.PLANK_HL_WIDTH):
        return config.FLOOR_L                      # তক্তার হাইলাইট
    return config.FLOOR


def draw_wall_and_floor():
    # কী করছে: পেছনের দেয়াল, বেসবোর্ড ও কাঠের মেঝে (তক্তার লাইন/জোড়া/হাইলাইটসহ) আঁকছে
    # কেন লাগছে: রুমের ব্যাকগ্রাউন্ড; মেঝেতে তক্তার প্যাটার্ন সমতল না দেখিয়ে গভীরতা দেয়
    # real world-এ এটা কোথায় দেখা যায়: 2D গেমে টাইলড ফ্লোর/দেয়াল প্রোসিজারাল প্যাটার্নে আঁকা
    draw_rect(*config.WALL_RECT, config.WALL)
    draw_rect(*config.WALL_SHADOW, config.WALL_D)
    draw_rect(*config.WALL_HL, config.WALL_L)
    draw_rect(*config.BASEBOARD, config.TRIM)
    draw_rect(*config.BASEBOARD_EDGE, config.TRIM_L)

    # মেঝে: প্রতি সারিতে একই রঙের পরপর ঘরগুলোকে একটি rect (run) হিসেবে আঁকি — পিক্সেল-প্রতি quad
    # নয়। ফলাফল হুবহু একই, কিন্তু quad সংখ্যা অনেক কমে (display list দ্রুত রিপ্লে হয়)।
    for y in range(config.FLOOR_TOP, config.FLOOR_BOTTOM + 1):
        row = (y - config.FLOOR_TOP) // config.PLANK_H
        run_start = 0
        run_color = _floor_cell_color(0, y, row)
        for x in range(1, config.ROOM_W):
            color = _floor_cell_color(x, y, row)
            if color != run_color:
                draw_rect(run_start, y, x - run_start, 1, run_color)  # এক রঙের run শেষ
                run_start = x
                run_color = color
        draw_rect(run_start, y, config.ROOM_W - run_start, 1, run_color)  # সারির শেষ run


def draw_decor():
    # কী করছে: দেয়ালের পোস্টার ও কোণার গাছ (টব + পাতা স্প্রাইট) আঁকছে
    # কেন লাগছে: রুমকে প্রাণবন্ত/কোজি দেখাতে সামান্য সাজসজ্জা
    # real world-এ এটা কোথায় দেখা যায়: গেমের রুমে পোস্টার/গাছের মতো প্রপ দিয়ে পরিবেশ তৈরি
    # পোস্টার
    draw_box(*config.POSTER_BOX, config.POSTER_FRAME)
    draw_rect(*config.POSTER_SKY, config.POSTER_3)
    draw_rect(*config.POSTER_STRIPE, config.POSTER_2)
    draw_rect(*config.POSTER_GROUND, config.POSTER_1)
    draw_pixel(*config.POSTER_SUN, config.POSTER_1)
    # গাছ
    draw_box(*config.POT_BOX, config.POT)
    draw_rect(*config.POT_SHADOW, config.POT_D)
    draw_sprite(*config.PLANT_POS, sprites.PLANT, sprites.PLANT_COLORS)


def _draw_blanket_neat():
    # কী করছে: পরিপাটি (idle) কম্বল আঁকছে — ভাঁজ, ছায়া, শরীরের বাম্প ও কিছু ভাঁজরেখা
    # কেন লাগছে: কেউ ঘুমাচ্ছে বোঝাতে; বাম্প দেখায় কম্বলের নিচে শরীর আছে
    # real world-এ এটা কোথায় দেখা যায়: পিক্সেল আর্টে shading দিয়ে কাপড়ের ভাঁজ বোঝানো
    draw_rect(*config.BLANKET_RECT, config.BLANKET)
    draw_rect(*config.BLANKET_FOLD_EDGE, config.SHEET)
    draw_rect(*config.BLANKET_FOLD_LINE, config.BLANKET_L)
    draw_rect(*config.BLANKET_SHADOW_L, config.BLANKET_D)
    draw_rect(*config.BLANKET_SHADOW_R, config.BLANKET_D)
    draw_rect(*config.BLANKET_SHADOW_B, config.BLANKET_D)
    # শরীরের বাম্প: প্রতি সারিতে অর্ধ-উপবৃত্তের প্রস্থ বের করে দু'পাশে এক পিক্সেল ছায়া/আলো
    for y in range(config.BUMP_Y0, config.BUMP_Y1 + 1):
        val = 1 - ((y - config.BUMP_CY) / config.BUMP_RY) ** 2
        if val < 0:
            continue
        w = int(config.BUMP_W * math.sqrt(val))
        draw_pixel(config.BUMP_XL - w, y, config.BLANKET_D)
        draw_pixel(config.BUMP_XR + w, y, config.BLANKET_L)
    draw_rect(*config.BLANKET_WRINKLE_1, config.BLANKET_D)
    draw_rect(*config.BLANKET_WRINKLE_2, config.BLANKET_D)
    draw_rect(*config.BLANKET_WRINKLE_3, config.BLANKET_L)


def _messy_edge(y):
    # কী করছে: design §5-এর সূত্রে এই সারিতে (y) কম্বলের বাঁ প্রান্ত (edge) কোন x-এ, তা দেয়
    # কেন লাগছে: এলোমেলো কম্বল কর্ণ বরাবর নিচে ঠেলা; প্রতি সারিতে বাঁ প্রান্ত বদলায়
    # real world-এ এটা কোথায় দেখা যায়: প্রোসিজারাল shape — সূত্র দিয়ে প্রতি সারির সীমা বের করা
    zig = (config.MESSY_EDGE_ZIG_ADD
           if y % config.MESSY_EDGE_ZIG_MOD < config.MESSY_EDGE_ZIG_LT else 0)
    return (config.MESSY_EDGE_BASE
            + max(0, int((config.MESSY_EDGE_PIVOT - y) * config.MESSY_EDGE_SLOPE))
            + zig)


def messy_formula_mask():
    # কী করছে: design §5-এর সূত্র সরাসরি ব্যবহার করে কম্বল কোন কোন ঘরে থাকবে তার সেট দেয়
    # কেন লাগছে: line+fill দিয়ে বানানো মাস্কের সাথে মিলিয়ে দেখতে (কতটা পার্থক্য) রেফারেন্স লাগে
    # real world-এ এটা কোথায় দেখা যায়: অ্যালগরিদমের ফল "ground truth"-এর সাথে মেলানো (testing)
    cells = set()
    for y in range(config.MESSY_Y0, config.MESSY_Y1 + 1):
        start = max(config.MESSY_FILL_MIN_X, _messy_edge(y))
        for x in range(start, config.MESSY_X_RIGHT + 1):
            cells.add((x, y))
    return cells


def messy_linefill_mask():
    # কী করছে: কম্বলের সীমানা কয়েকটি bresenham_line-এ এঁকে boundary_fill দিয়ে ভেতর ভরে মাস্ক বানায়
    # কেন লাগছে: এটাই "color fill" CG technique-এর প্রয়োগ — রেখা দিয়ে আকৃতি, তারপর ফিল দিয়ে ভেতর
    # real world-এ এটা কোথায় দেখা যায়: vector আঁকা টুলে outline এঁকে bucket দিয়ে ভরাট
    gx0 = config.MESSY_FILL_MIN_X - 1          # গ্রিডে ১-ঘর margin, যাতে fill ঘেরা থাকে
    gx1 = config.MESSY_X_RIGHT + 1
    gy0 = config.MESSY_Y0 - 1
    gy1 = config.MESSY_Y1 + 1
    w = gx1 - gx0 + 1
    h = gy1 - gy0 + 1
    EMPTY, BORDER, FILL = 0, 1, 2
    grid = [[EMPTY] * w for _ in range(h)]

    def mark(x, y):
        grid[y - gy0][x - gx0] = BORDER        # রুম-লোকাল (x,y) → গ্রিড ইনডেক্স

    top_y = config.MESSY_Y0
    bot_y = config.MESSY_Y1
    right_x = config.MESSY_X_RIGHT
    left_x = config.MESSY_EDGE_BASE            # 7 = কর্ণের নিচের প্রান্তের x
    pivot = config.MESSY_EDGE_PIVOT            # যেখানে কর্ণ শেষ
    diag_top = _messy_edge(top_y)              # y=30-এ edge (কর্ণের উপরের x)

    # কম্বলের সীমানা = ৫টি bresenham সেগমেন্টে বন্ধ polygon:
    outline = [
        (left_x, pivot, diag_top, top_y),      # ১) কর্ণ উপরের ধার
        (diag_top, top_y, right_x, top_y),     # ২) উপরের ছোট অনুভূমিক ধার
        (right_x, top_y, right_x, bot_y),      # ৩) ডান খাড়া ধার
        (right_x, bot_y, left_x, bot_y),       # ৪) নিচের অনুভূমিক ধার
        (left_x, bot_y, left_x, pivot),        # ৫) বাঁ খাড়া ধার (বিছানার পাশ)
    ]
    for x0, y0, x1, y1 in outline:
        for px, py in bresenham_line(x0, y0, x1, y1):
            mark(px, py)

    # ভেতরের একটি seed থেকে ভরাট (seed নিশ্চিতভাবে polygon-এর ভেতরে)
    seed_x, seed_y = right_x - 2, bot_y - 3
    boundary_fill(grid, seed_x - gx0, seed_y - gy0, FILL, BORDER)

    mask = set()
    for gy in range(h):
        for gx in range(w):
            if grid[gy][gx] != EMPTY:          # BORDER বা FILL = কম্বলের অংশ
                mask.add((gx + gx0, gy + gy0))
    return mask


def _messy_cell_color(x, y, edge):
    # কী করছে: এলোমেলো কম্বলের এক ঘরের shading রঙ ঠিক করছে (design §5-এর নিয়মে)
    # কেন লাগছে: কম্বলের বাঁ ধারে হাইলাইট, ডান/নিচে ছায়া, মাঝে ভাঁজ — এতে ত্রিমাত্রিক দেখায়
    # real world-এ এটা কোথায় দেখা যায়: পিক্সেল আর্টে shading দিয়ে কাপড়ের ভাঁজ বোঝানো
    color = config.BLANKET
    if x == edge:                              # বাঁ ধারে হাইলাইট (মাঝে মাঝে গাঢ়)
        color = config.BLANKET_D if y % config.MESSY_EDGE_D_MOD == 0 else config.BLANKET_L
    if x == config.MESSY_X_RIGHT or y >= config.MESSY_SHADOW_Y:  # ডান/নিচের ছায়া
        color = config.BLANKET_D
    if ((x + y) % config.MESSY_WRINKLE_MOD == 0
            and x > edge + config.MESSY_WRINKLE_OFFSET):         # ভাঁজ
        color = config.BLANKET_D
    return color


def _draw_blanket_messy():
    # কী করছে: খালি বিছানার এলোমেলো রূপ আঁকছে — চাদরের ভাঁজ, বালিশের দাগ, line+fill কম্বল ও ঝুলন্ত কোণা
    # কেন লাগছে: কেউ বিছানায় নেই (কাজ করছে) বোঝাতে; কম্বলের আকৃতি line+fill CG technique-এ তৈরি
    # real world-এ এটা কোথায় দেখা যায়: গেমে একই অবজেক্টের ভিন্ন state (গোছানো/এলোমেলো) আঁকা
    draw_rect(*config.MESSY_SHEET_1, config.SHEET_D)   # চাদরের ভাঁজ
    draw_rect(*config.MESSY_SHEET_2, config.SHEET_D)
    draw_rect(*config.MESSY_SHEET_3, config.SHEET_D)
    for dx, dy in config.MESSY_DENT:                   # বালিশের দাগ
        draw_pixel(dx, dy, config.SHEET_D)

    mask = messy_linefill_mask()                       # line+fill দিয়ে কম্বলের আকৃতি
    rows = {}
    for x, y in mask:
        rows.setdefault(y, []).append(x)

    # প্রতি সারিতে একই রঙের পরপর ঘরকে এক rect (run) করে আঁকি (floor-এর মতো দ্রুত)
    for y in range(config.MESSY_Y0, config.MESSY_Y1 + 1):
        xs = rows.get(y)
        if not xs:
            continue
        edge = _messy_edge(y)
        run_start = None
        run_color = None
        x_lo, x_hi = min(xs), max(xs)
        for x in range(x_lo, x_hi + 1):
            if (x, y) not in mask:                     # ফাঁক (সাধারণত থাকে না) → run শেষ
                if run_start is not None:
                    draw_rect(run_start, y, x - run_start, 1, run_color)
                    run_start = None
                continue
            color = _messy_cell_color(x, y, edge)
            if run_start is None:
                run_start, run_color = x, color
            elif color != run_color:
                draw_rect(run_start, y, x - run_start, 1, run_color)
                run_start, run_color = x, color
        if run_start is not None:
            draw_rect(run_start, y, x_hi + 1 - run_start, 1, run_color)

    draw_rect(*config.MESSY_HANG, config.BLANKET_D)    # ঝুলে থাকা কোণা


def draw_bed(messy=False):
    # কী করছে: বিছানা আঁকছে — হেডবোর্ড, ফ্রেম, ম্যাট্রেস, বালিশ ও (পরিপাটি/এলোমেলো) কম্বল
    # কেন লাগছে: রুমের প্রধান অবজেক্ট; কম্বলের অবস্থা বলে কেউ ঘুমাচ্ছে না জেগে আছে
    # real world-এ এটা কোথায় দেখা যায়: একই অবজেক্ট বিভিন্ন state-এ আঁকা (game asset variants)
    draw_box(*config.BED_HEADBOARD, config.WOOD)
    draw_rect(*config.BED_HEADBOARD_HL, config.WOOD_L)
    draw_rect(*config.BED_POST_L, config.OUTLINE)
    draw_rect(*config.BED_POST_R, config.OUTLINE)
    draw_box(*config.BED_FRAME, config.WOOD_D)
    draw_rect(*config.BED_MATTRESS, config.SHEET)
    draw_box(*config.BED_PILLOW, config.PILLOW, config.SHEET_D)
    draw_rect(*config.BED_PILLOW_SHADOW, config.SHEET_D)
    if messy:
        _draw_blanket_messy()
    else:
        _draw_blanket_neat()


def draw_desk():
    # কী করছে: ডেস্ক টপ/পা, মনিটর ফ্রেম+স্ট্যান্ড, কীবোর্ড, ল্যাম্প বেস/পোল, মগ ও বই আঁকছে
    # কেন লাগছে: কাজের জায়গা; স্ক্রিন ও ল্যাম্প শেড আলাদা ফাংশনে (state বদলায় বলে)
    # real world-এ এটা কোথায় দেখা যায়: static prop-কে dynamic অংশ (স্ক্রিন/আলো) থেকে আলাদা রাখা
    draw_box(*config.DESK_TOP, config.DESK)
    draw_rect(*config.DESK_HL, config.DESK_L)
    draw_rect(*config.DESK_FRONT, config.OUTLINE)
    draw_rect(*config.DESK_FRONT_IN, config.DESK_D)
    draw_rect(*config.DESK_LEG_L, config.OUTLINE)
    draw_rect(*config.DESK_LEG_R, config.OUTLINE)
    # মনিটর ফ্রেম + স্ট্যান্ড
    draw_box(*config.MONITOR_BOX, config.MONITOR)
    draw_rect(*config.MONITOR_STAND, config.METAL)
    draw_rect(*config.MONITOR_BASE, config.METAL)
    # কীবোর্ড ও কী
    draw_box(*config.KEYBOARD_BOX, config.KEY)
    for kx in range(config.KEY_X_START, config.KEY_X_END + 1, config.KEY_X_STEP):
        draw_pixel(kx, config.KEY_ROW1_Y, config.KEY_D)
        draw_pixel(kx + 1, config.KEY_ROW2_Y, config.KEY_D)
    # ল্যাম্পের বেস ও পোল (শেড আলাদা ফাংশনে)
    draw_rect(*config.LAMP_BASE, config.METAL)
    draw_rect(*config.LAMP_POLE, config.METAL)
    # মগ
    draw_box(*config.MUG_BOX, config.MUG)
    draw_pixel(*config.MUG_HANDLE_1, config.OUTLINE)
    draw_pixel(*config.MUG_HANDLE_2, config.OUTLINE)
    draw_pixel(*config.MUG_COFFEE, config.WOOD)
    # বই
    draw_box(*config.BOOKS_BOX, config.BOOK)
    draw_rect(*config.BOOK_TOP, config.BOOK2)


def draw_chair():
    # কী করছে: চেয়ারের সিট, হাইলাইট, পিঠ, পোস্ট ও বেস আঁকছে
    # কেন লাগছে: ডেস্কের সামনে বসার জায়গা; পরে ক্যারেক্টার এখানে বসবে
    # real world-এ এটা কোথায় দেখা যায়: game scene-এ furniture prop আঁকা
    draw_box(*config.CHAIR_SEAT, config.CHAIR)
    draw_rect(*config.CHAIR_SEAT_HL, config.CHAIR_L)
    draw_box(*config.CHAIR_BACK, config.CHAIR_D)
    draw_rect(*config.CHAIR_POST, config.METAL)
    draw_rect(*config.CHAIR_BASE, config.OUTLINE)


def draw_rug(colors):
    # কী করছে: রাগ আঁকছে — base ভরাট, হালকা/গাঢ় কিনারা ও সেলাই ফোঁটা; রঙ প্যারামিটার থেকে
    # কেন লাগছে: প্রতি রুমের রাগ ভিন্ন রঙ (Samee grey-blue, Rifat green), তাই colors পাস করা হয়
    # real world-এ এটা কোথায় দেখা যায়: একই স্প্রাইট ভিন্ন palette-এ (recolor) আঁকা
    base, dark, light = colors
    draw_box(*config.RUG_BOX, base)
    draw_rect(*config.RUG_EDGE_TOP, light)
    draw_rect(*config.RUG_EDGE_LEFT, light)
    draw_rect(*config.RUG_EDGE_BOTTOM, dark)
    draw_rect(*config.RUG_EDGE_RIGHT, dark)
    # সেলাই ফোঁটা (design §5-এ রঙ বলা নেই; mockup-এর সাথে মিলিয়ে গাঢ় edge রঙ ব্যবহার করা হলো)
    for sx in range(config.RUG_STITCH_X0, config.RUG_STITCH_X1 + 1, config.RUG_STITCH_STEP):
        draw_pixel(sx, config.RUG_STITCH_Y, dark)


def draw_screen(on=False):
    # কী করছে: মনিটরের স্ক্রিন আঁকছে — বন্ধ হলে ধূসর + দুই প্রতিফলন পিক্সেল, চালু হলে নীল + কোড লাইন
    # কেন লাগছে: স্ক্রিন state প্রতি ফ্রেমে বদলায়, তাই static room থেকে আলাদা
    # real world-এ এটা কোথায় দেখা যায়: UI-তে on/off state অনুযায়ী একই উপাদানের ভিন্ন চেহারা
    if on:
        draw_rect(*config.SCREEN_RECT, config.SCREEN_ON)
        for cx, cy, length, color in config.CODE_LINES:
            draw_rect(cx, cy, length, 1, color)
    else:
        draw_rect(*config.SCREEN_RECT, config.SCREEN_OFF)
        draw_pixel(*config.SCREEN_REFLECT_1, config.SCREEN_REFLECT)
        draw_pixel(*config.SCREEN_REFLECT_2, config.SCREEN_REFLECT)


def draw_lamp_shade(on=False, warn=False):
    # কী করছে: ল্যাম্প শেড আঁকছে; ভেতরের রঙ warn হলে লাল, on হলে উজ্জ্বল, নাহলে বন্ধ; on-এ বাল্ব রেখা
    # কেন লাগছে: আলো জ্বলা/নেভা ও দ্বন্দ্ব (দুজনেই কাজ) দেখাতে শেডের রঙ বদলায়
    # real world-এ এটা কোথায় দেখা যায়: status অনুযায়ী রঙ বদলানো indicator light
    draw_rect(*config.LAMP_SHADE_TOP, config.OUTLINE)
    draw_rect(*config.LAMP_SHADE_BODY, config.OUTLINE)
    if warn:
        inside = config.WARNING
    elif on:
        inside = config.LAMP_ON
    else:
        inside = config.LAMP_OFF
    draw_rect(*config.LAMP_SHADE_IN, inside)
    draw_rect(*config.LAMP_SHADE_RIM, config.OUTLINE)
    if on:
        draw_rect(*config.LAMP_BULB_LINE, config.LAMP_BULB)


def build_room_lists():
    # কী করছে: রুমের স্ট্যাটিক অংশ (দেয়াল/মেঝে/ডেকর/রাগ/বিছানা/ডেস্ক/চেয়ার) ৪টি display list-এ
    #           একবার কম্পাইল করছে — neat/messy কম্বল × দুই রাগ রঙ (Samee, Rifat)
    # কেন লাগছে: Python-এ প্রতি ফ্রেমে হাজার হাজার quad আঁকা ধীর; list-এ রেখে glCallList দ্রুত রিপ্লে হয়
    # real world-এ এটা কোথায় দেখা যায়: GPU-তে একবার geometry আপলোড করে বারবার আঁকা (VBO/display list)
    # নোট: স্ক্রিন, ল্যাম্প শেড ও ঘুমন্ত মাথা list-এ নেই — এগুলো পরে বদলায় বলে প্রতি ফ্রেমে নতুন আঁকা হয়
    rug_colors = {
        "samee": (config.SAMEE_RUG, config.SAMEE_RUG_D, config.SAMEE_RUG_L),
        "rifat": (config.RIFAT_RUG, config.RIFAT_RUG_D, config.RIFAT_RUG_L),
    }
    variants = [("samee", False), ("samee", True), ("rifat", False), ("rifat", True)]
    base = glGenLists(len(variants))   # পরপর ৪টি list id বরাদ্দ করে
    for i, (rug, messy) in enumerate(variants):
        list_id = base + i
        glNewList(list_id, GL_COMPILE)   # এখান থেকে কমান্ডগুলো list-এ জমা হবে (আঁকা হবে না)
        draw_wall_and_floor()
        draw_decor()
        draw_rug(rug_colors[rug])
        draw_bed(messy)
        draw_desk()
        draw_chair()
        glEndList()
        ROOM_LISTS[(rug, messy)] = list_id
