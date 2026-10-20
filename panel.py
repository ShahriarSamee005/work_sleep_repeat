import font
import sprites
from pixel import draw_box, draw_rect, draw_sprite, draw_text, text_width

import config

PANEL_FONT = font.BITMAP_8X13      # প্যানেলের সব লেখা এই ফন্টে (design §9)


def format_time(seconds):
    # কী করছে: সেকেন্ডকে "Xh YYm" রূপে দেয় (মিনিট ২ অঙ্কে); ০ বা কম হলে "—"
    # কেন লাগছে: টাইম কার্ডে আজকের কাজের সময় পড়ার মতো করে দেখাতে (design §9)
    # real world-এ এটা কোথায় দেখা যায়: টাইম-ট্র্যাকার/স্টপওয়াচে সময়ের মানবিক ফরম্যাট
    s = int(seconds)
    if s <= 0:
        return "—"                       # শূন্য হলে ড্যাশ
    h = s // 3600                         # পূর্ণ ঘণ্টা
    m = (s % 3600) // 60                  # বাকি মিনিট
    return "%dh %02dm" % (h, m)           # যেমন "1h 05m"


def screen_to_grid(mx, my):
    # কী করছে: মাউসের window পিক্সেল (mx,my) কে গ্রিড কোঅর্ডিনেটে (gx,gy) বদলায় (÷ PIXEL)
    # কেন লাগছে: মাউস ইভেন্ট window পিক্সেলে আসে; আমাদের হিসাব গ্রিড এককে
    # real world-এ এটা কোথায় দেখা যায়: স্ক্রিন স্পেস → world/UI স্পেস রূপান্তর (hit-testing)
    # এখানে my উপরে-থেকে (top-down) ধরা, আমাদের ortho-ও y=0 উপরে — তাই সরাসরি ভাগ।
    # pyglet-এর মাউস y নিচ-থেকে আসে, তাই main.py কল করার আগে উল্টে দেয়
    return (mx / config.PIXEL, my / config.PIXEL)


def _draw_centered(cx, y, text, color):
    # কী করছে: cx-কে কেন্দ্র ধরে text-এর প্রস্থ মেপে গ্রিড এককে বাঁয়ে সরিয়ে আঁকে
    # কেন লাগছে: প্যানেলের লেখাগুলো ৪৮-পিক্সেল কলামে মাঝ বরাবর বসাতে
    # real world-এ এটা কোথায় দেখা যায়: UI টেক্সট center-align
    # নোট: '—'/'•'-ও এক স্বাভাবিক অক্ষরের সমান জায়গা নেয় (draw_text তাদের pen সমানই সরায়),
    #      তাই text_width fixed-pitch হিসাবেই মাপে — center ঠিক থাকে
    width_px = text_width(text, PANEL_FONT)
    start_x = cx - (width_px / config.PIXEL) / 2.0
    draw_text(start_x, y, text, color, PANEL_FONT)


def _draw_icon(any_working):
    # কী করছে: কেউ কাজ করলে SUN, নাহলে MOON স্প্রাইট আঁকে
    # কেন লাগছে: এক নজরে বোঝাতে Pro AI ব্যস্ত (সূর্য) নাকি ফাঁকা (চাঁদ) — design §9
    # real world-এ এটা কোথায় দেখা যায়: status আইকন (busy/free) toolbar-এ
    if any_working:
        draw_sprite(*config.PANEL_ICON_POS, sprites.SUN, sprites.SUN_COLORS)
    else:
        draw_sprite(*config.PANEL_ICON_POS, sprites.MOON, sprites.MOON_COLORS)


def _draw_card(box, name, active, seconds):
    # কী করছে: এক টাইম কার্ড আঁকে — active হলে PANEL_CARD_ACTIVE + ACCENT বর্ডার, নাহলে PANEL_CARD;
    #           উপরে "Name · today", নিচে format_time (active হলে GOLD)
    # কেন লাগছে: প্রতিজনের আজকের কাজের সময় দেখাতে; কে এখন কাজ করছে তা বর্ডার/রঙে বোঝাতে
    # real world-এ এটা কোথায় দেখা যায়: ড্যাশবোর্ডের প্রতি-ব্যক্তি time card
    x, y, w, h = box
    fill = config.PANEL_CARD_ACTIVE if active else config.PANEL_CARD
    border = config.ACCENT if active else config.PANEL_BORDER
    draw_box(x, y, w, h, fill, outline=border)
    _draw_centered(config.PANEL_CENTER_X, y + config.CARD_NAME_DY,
                   name + " today", config.TEXT_MUTED)
    time_color = config.GOLD if active else config.TEXT_DIM
    _draw_centered(config.PANEL_CENTER_X, y + config.CARD_TIME_DY,
                   format_time(seconds), time_color)


def draw_panel(state, me, now):
    # কী করছে: পুরো প্যানেল আঁকে — ব্যাকগ্রাউন্ড, আইকন, শিরোনাম, স্ট্যাটাস/সাব-স্ট্যাটাস, দুই কার্ড
    # কেন লাগছে: এটাই ডান পাশের UI; কে কাজ করছে আর আজ কত সময় হয়েছে তা দেখায়
    # real world-এ এটা কোথায় দেখা যায়: অ্যাপের side panel / status HUD
    # state = {"samee": {...}, "rifat": {...}} প্রতিজনে "working" (bool) ও "seconds" (float);
    #         main প্রতি ফ্রেমে state.snapshot() থেকে এটি বানায় (techspec §7)
    # me: এখন শুধু Phase 14-এর dibs বাটন ও §2.1-এর "You're working" লেখার জন্য রাখা
    # now: Phase 11 sync-এর জন্য সংরক্ষিত (এখন seconds আগেই হিসাব করে state-এ দেওয়া)
    samee_w = state["samee"]["working"]
    rifat_w = state["rifat"]["working"]
    any_w = samee_w or rifat_w
    both_w = samee_w and rifat_w

    # ব্যাকগ্রাউন্ড + ভেতরের ১-পিক্সেল বর্ডার
    draw_rect(config.PANEL_X, config.PANEL_Y, config.PANEL_W, config.PANEL_H, config.PANEL_BG)
    draw_box(config.PANEL_X, config.PANEL_Y, config.PANEL_W, config.PANEL_H,
             config.PANEL_BG, outline=config.PANEL_BORDER)

    _draw_icon(any_w)

    _draw_centered(config.PANEL_CENTER_X, config.PANEL_TITLE_Y, "CLAUDE STATUS", config.TEXT_MUTED)

    # স্ট্যাটাস লাইন: দ্বন্দ্ব > কে ব্যবহার করছে > ফাঁকা
    if both_w:
        _draw_centered(config.PANEL_CENTER_X, config.PANEL_STATUS_Y, "Both working!", config.WARNING)
    elif samee_w:
        _draw_centered(config.PANEL_CENTER_X, config.PANEL_STATUS_Y, "Samee is using it", config.GOLD)
    elif rifat_w:
        _draw_centered(config.PANEL_CENTER_X, config.PANEL_STATUS_Y, "Rifat is using it", config.GOLD)
    else:
        _draw_centered(config.PANEL_CENTER_X, config.PANEL_STATUS_Y, "Claude is free", config.TEXT)

    # সাব-স্ট্যাটাস
    sub = "Ask before you start" if any_w else "Nobody is working"
    _draw_centered(config.PANEL_CENTER_X, config.PANEL_SUB_Y, sub, config.TEXT_DIM)

    # টগলের জায়গা (y 44–60) এখন ফাঁকা — টগল বাদ, কারণ status এখন হুক থেকে আসে (design §2)।
    # Phase 14-এ এখানেই "Call dibs" বাটন বসবে; তাই config-এর TOGGLE_* মাপগুলো রেখে দেওয়া হলো।

    # দুই টাইম কার্ড
    _draw_card(config.CARD1_BOX, "Samee", samee_w, state["samee"]["seconds"])
    _draw_card(config.CARD2_BOX, "Rifat", rifat_w, state["rifat"]["seconds"])
