"""character.py — ক্যারেক্টার আঁকা (Phase 5: বসে কাজ করার ভঙ্গি ও টাইপিং)। state machine Phase 6-এ।"""

import sprites
from pixel import draw_pixel, draw_rect, draw_sprite

import config


def draw_sitting(time_now):
    # কী করছে: ডেস্কে বসা ভঙ্গি আঁকছে (হাত → শরীর → মাথা) এবং time_now দেখে টাইপিং-এ এক হাত ১px উপরে তোলে
    # কেন লাগছে: WORKING অবস্থায় ক্যারেক্টার বসে টাইপ করছে দেখাতে; হাত পাল্টে নড়াচড়ার ভাব আসে
    # real world-এ এটা কোথায় দেখা যায়: গেমে সময় অনুযায়ী frame বেছে নিয়ে অ্যানিমেশন (keyframe by time)
    # চেয়ার আগেই রুম display list-এ আঁকা; এখানে design §6-এর ক্রম: (chair →) arms → body → head
    phase = int(time_now / config.TYPE_INTERVAL) % 2   # প্রতি TYPE_INTERVAL-এ 0/1 পাল্টায়
    left_up = 1 if phase == 0 else 0                    # phase 0 → বাঁ হাত উপরে
    right_up = 1 if phase == 1 else 0                   # phase 1 → ডান হাত উপরে (y ছোট = উপরে)

    # হাতের দুই পাশের রেখা (outline) ও ভেতরের রঙ
    draw_rect(*config.SIT_ARM_L_OUTLINE, config.OUTLINE)
    draw_rect(*config.SIT_ARM_R_OUTLINE, config.OUTLINE)
    draw_rect(*config.SIT_ARM_L_INNER, config.SKIN)
    draw_rect(*config.SIT_ARM_R_INNER, config.SKIN_S)

    # হাতের পাঞ্জা — টাইপিং-এ up হলে y ১ কমে (উপরে ওঠে)
    hlx, hly, hlw, hlh = config.SIT_HAND_L
    draw_rect(hlx, hly - left_up, hlw, hlh, config.OUTLINE)
    draw_pixel(config.SIT_HAND_L_SKIN[0], config.SIT_HAND_L_SKIN[1] - left_up, config.SKIN)
    hrx, hry, hrw, hrh = config.SIT_HAND_R
    draw_rect(hrx, hry - right_up, hrw, hrh, config.OUTLINE)
    draw_pixel(config.SIT_HAND_R_SKIN[0], config.SIT_HAND_R_SKIN[1] - right_up, config.SKIN)

    # শরীর, তারপর মাথা (মাথা সবার উপরে)
    draw_sprite(*config.SIT_BODY_POS, sprites.BODY_BACK, sprites.BODY_BACK_COLORS)
    draw_sprite(*config.SIT_HEAD_POS, sprites.HEAD_BACK, sprites.HEAD_BACK_COLORS)
