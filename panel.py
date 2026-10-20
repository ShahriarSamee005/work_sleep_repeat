import font
import sprites
from pixel import DASH, draw_box, draw_rect, draw_sprite, draw_text, text_width

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


def _draw_card(box, view):
    # কী করছে: এক টাইম কার্ড আঁকে — কাজ করলে PANEL_CARD_ACTIVE + ACCENT বর্ডার, নাহলে PANEL_CARD;
    #           বাঁয়ে online ডট, উপরে "Name today", নিচে format_time (কাজ করলে GOLD)
    # কেন লাগছে: প্রতিজনের আজকের কাজের সময় দেখাতে; কে কাজ করছে ও কে আদৌ অনলাইন তা বোঝাতে
    # real world-এ এটা কোথায় দেখা যায়: ড্যাশবোর্ডের প্রতি-ব্যক্তি time card + presence ডট
    x, y, w, h = box
    fill = config.PANEL_CARD_ACTIVE if view.working else config.PANEL_CARD
    border = config.ACCENT if view.working else config.PANEL_BORDER
    draw_box(x, y, w, h, fill, outline=border)

    dx, dy, dw, dh = config.CARD_DOT                 # online ডট (design §2.4)
    draw_rect(x + dx, y + dy, dw, dh,
              config.ONLINE_GREEN if view.online else config.OFFLINE_GREY)

    _draw_centered(config.PANEL_CENTER_X, y + config.CARD_NAME_DY,
                   view.name + " today", config.TEXT_MUTED)
    time_color = config.GOLD if view.working else config.TEXT_DIM
    _draw_centered(config.PANEL_CENTER_X, y + config.CARD_TIME_DY,
                   format_time(view.today_seconds), time_color)


def status_line(snap):
    # কী করছে: design §2.1-এর নিয়ম মেনে স্ট্যাটাস লেখা ও তার রঙ ঠিক করে, (text, color) দেয়
    # কেন লাগছে: অগ্রাধিকার আছে — দ্বন্দ্ব > আমি > সঙ্গী > সঙ্গী অফলাইন > ফাঁকা; এক জায়গায় রাখলে
    #           টেস্ট করা যায় ও প্যানেলের আঁকার কোড ছোট থাকে
    # real world-এ এটা কোথায় দেখা যায়: UI স্ট্রিং নির্বাচনের শুদ্ধ (pure) ফাংশন
    me, peer = snap.me, snap.peer
    if me.working and peer.working:
        return "Both of you are on it!", config.WARNING
    if me.working:
        # "You're" নয় — এই bitmap ফন্টে apostrophe একটি তির্যক দাগের মতো দেখায় (You´re)
        return "You are working", config.GOLD
    if peer.working:
        return "%s is working" % peer.name, config.GOLD
    if not peer.online:
        return "%s is offline" % peer.name, config.OFFLINE_GREY
    return "Claude is free", config.TEXT


def draw_panel(snap):
    # কী করছে: পুরো প্যানেল আঁকে — ব্যাকগ্রাউন্ড, আইকন, শিরোনাম, স্ট্যাটাস/সাব-স্ট্যাটাস,
    #           দুই টাইম কার্ড (online ডট সহ) ও নিচে সংযোগের লাইন
    # কেন লাগছে: এটাই ডান পাশের UI; কে কাজ করছে, কত সময়, কে অনলাইন, আর আমরা সার্ভারে পৌঁছাচ্ছি কিনা
    # real world-এ এটা কোথায় দেখা যায়: অ্যাপের side panel / status HUD
    # snap: state.StateSnapshot — প্যানেল শুধু এটিই পড়ে, কোনো লক বা মডিউল ছোঁয় না (techspec §7)
    views = {snap.me.user_id: snap.me, snap.peer.user_id: snap.peer}
    any_w = snap.me.working or snap.peer.working

    # ব্যাকগ্রাউন্ড + ভেতরের ১-পিক্সেল বর্ডার
    draw_rect(config.PANEL_X, config.PANEL_Y, config.PANEL_W, config.PANEL_H, config.PANEL_BG)
    draw_box(config.PANEL_X, config.PANEL_Y, config.PANEL_W, config.PANEL_H,
             config.PANEL_BG, outline=config.PANEL_BORDER)

    _draw_icon(any_w)

    _draw_centered(config.PANEL_CENTER_X, config.PANEL_TITLE_Y, "CLAUDE STATUS", config.TEXT_MUTED)

    text, color = status_line(snap)
    _draw_centered(config.PANEL_CENTER_X, config.PANEL_STATUS_Y, text, color)

    # সাব-স্ট্যাটাস
    sub = "Ask before you start" if any_w else "Nobody is working"
    _draw_centered(config.PANEL_CENTER_X, config.PANEL_SUB_Y, sub, config.TEXT_DIM)

    # টগলের জায়গা (y 44–60) এখন ফাঁকা — টগল বাদ, কারণ status এখন হুক থেকে আসে (design §2)।
    # Phase 14-এ এখানেই "Call dibs" বাটন বসবে; তাই config-এর TOGGLE_* মাপগুলো রেখে দেওয়া হলো।

    # দুই টাইম কার্ড — বাঁয়ে সবসময় Samee, ডানে Rifat (কে অ্যাপ চালাচ্ছে তা নির্বিশেষে)
    _draw_card(config.CARD1_BOX, views["samee"])
    _draw_card(config.CARD2_BOX, views["rifat"])

    # নিচের সংযোগ লাইন (design §2) — সার্ভারে পৌঁছাচ্ছি কিনা, আমার নিজের অবস্থা নয়
    if snap.connected:
        _draw_centered(config.PANEL_CENTER_X, config.PANEL_CONN_Y, "online", config.ONLINE_GREEN)
    else:
        _draw_centered(config.PANEL_CENTER_X, config.PANEL_CONN_Y,
                       "offline " + DASH + " retrying", config.OFFLINE_GREY)
