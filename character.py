"""character.py — ক্যারেক্টারের state machine ও drawing (ঘুম → ওঠা → হাঁটা → বসা → কাজ ও উল্টো)।"""

import math

from OpenGL.GL import glPopMatrix, glPushMatrix, glScalef, glTranslatef

import sprites
from algorithms import cubic_bezier, ease_in_out
from pixel import draw_pixel, draw_rect, draw_sprite

import config

# ---- ৮টি state (appflow §3) ----
IN_BED = "IN_BED"
GETTING_UP = "GETTING_UP"
WALKING_TO_DESK = "WALKING_TO_DESK"
SITTING_DOWN = "SITTING_DOWN"
WORKING = "WORKING"
STANDING_UP = "STANDING_UP"
WALKING_TO_BED = "WALKING_TO_BED"
LYING_DOWN = "LYING_DOWN"

_STAND_H = len(sprites.STAND)     # দাঁড়ানো স্প্রাইটের উচ্চতা (পায়ের pivot বের করতে)


def _lerp(a, b, t):
    # কী করছে: দুই বিন্দু a ও b-এর মাঝে t (0–1) অনুপাতে সরলরৈখিক অবস্থান দেয়
    # কেন লাগছে: ওঠা/শোয়া/বসা অবস্থায় সরল পথে স্প্রাইট সরাতে
    # real world-এ এটা কোথায় দেখা যায়: অ্যানিমেশনে দুই keyframe-এর মাঝে interpolation (tween)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def draw_sitting(time_now):
    # কী করছে: ডেস্কে বসা ভঙ্গি আঁকছে (হাত → শরীর → মাথা) এবং time_now দেখে টাইপিং-এ এক হাত ১px উপরে তোলে
    # কেন লাগছে: WORKING অবস্থায় ক্যারেক্টার বসে টাইপ করছে দেখাতে; হাত পাল্টে নড়াচড়ার ভাব আসে
    # real world-এ এটা কোথায় দেখা যায়: গেমে সময় অনুযায়ী frame বেছে নিয়ে অ্যানিমেশন (keyframe by time)
    phase = int(time_now / config.TYPE_INTERVAL) % 2   # প্রতি TYPE_INTERVAL-এ 0/1 পাল্টায়
    left_up = 1 if phase == 0 else 0                    # phase 0 → বাঁ হাত উপরে
    right_up = 1 if phase == 1 else 0                   # phase 1 → ডান হাত উপরে (y ছোট = উপরে)

    draw_rect(*config.SIT_ARM_L_OUTLINE, config.OUTLINE)
    draw_rect(*config.SIT_ARM_R_OUTLINE, config.OUTLINE)
    draw_rect(*config.SIT_ARM_L_INNER, config.SKIN)
    draw_rect(*config.SIT_ARM_R_INNER, config.SKIN_S)

    hlx, hly, hlw, hlh = config.SIT_HAND_L
    draw_rect(hlx, hly - left_up, hlw, hlh, config.OUTLINE)
    draw_pixel(config.SIT_HAND_L_SKIN[0], config.SIT_HAND_L_SKIN[1] - left_up, config.SKIN)
    hrx, hry, hrw, hrh = config.SIT_HAND_R
    draw_rect(hrx, hry - right_up, hrw, hrh, config.OUTLINE)
    draw_pixel(config.SIT_HAND_R_SKIN[0], config.SIT_HAND_R_SKIN[1] - right_up, config.SKIN)

    draw_sprite(*config.SIT_BODY_POS, sprites.BODY_BACK, sprites.BODY_BACK_COLORS)
    draw_sprite(*config.SIT_HEAD_POS, sprites.HEAD_BACK, sprites.HEAD_BACK_COLORS)


class Character:
    """একজন ব্যক্তির state machine ও drawing (techspec §4.6)।"""

    def __init__(self, name):
        # কী করছে: একটি ক্যারেক্টার তৈরি করছে, শুরুতে বিছানায় ঘুমন্ত অবস্থায়
        # কেন লাগছে: Samee ও Rifat দুজনের জন্য আলাদা অবজেক্ট; সব per-user state এখানে থাকে
        # real world-এ এটা কোথায় দেখা যায়: গেমে প্রতিটি চরিত্র নিজের state নিয়ে আলাদা অবজেক্ট
        self.name = name
        self.state = IN_BED
        self.progress = 0.0        # 0..1, বর্তমান state-এর ভেতরে অগ্রগতি
        self.target_working = False
        self.monitor_on = False
        self.lamp_on = False
        self._work_time = 0.0      # WORKING-এ ঢোকার পর কত সময় (device চালু ক্রমে)
        self._leave_time = 0.0     # WORKING ছাড়ার সময় গোনা (device বন্ধ ক্রমে)
        self.moving_up = True      # facing: উপরে হাঁটছে? (dy < 0 → পিঠ দেখা যায়)

    def set_working(self, working):
        # কী করছে: শুধু লক্ষ্য (target) সেট করে — কাজ করবে কি না; update() বাকিটা সামলায়
        # কেন লাগছে: sync/কী শুধু "কী হওয়া উচিত" বলে; কীভাবে (অ্যানিমেশন) সেটা state machine ঠিক করে
        # real world-এ এটা কোথায় দেখা যায়: UI-তে target state সেট করলে animation নিজে গিয়ে মেলায়
        self.target_working = working

    def bed_is_messy(self):
        # কী করছে: বিছানা এলোমেলো কিনা বলে — IN_BED ছাড়া সব অবস্থাতেই এলোমেলো
        # কেন লাগছে: কেউ বিছানা ছেড়ে উঠলেই কম্বল এলোমেলো; শুধু বিছানায় ফিরলে গোছানো
        # real world-এ এটা কোথায় দেখা যায়: state থেকে দৃশ্যমান বৈশিষ্ট্য বের করা
        return self.state != IN_BED

    def _enter(self, new_state):
        # কী করছে: নতুন state-এ ঢোকে, progress রিসেট করে এবং device/timer ঠিক করে
        # কেন লাগছে: প্রতিবার state বদলালে অগ্রগতি ও (WORKING হলে) timer শূন্য থেকে শুরু হওয়া দরকার
        # real world-এ এটা কোথায় দেখা যায়: state machine-এ "on enter" হ্যান্ডলার
        self.state = new_state
        self.progress = 0.0
        if new_state == WORKING:
            self._work_time = 0.0
            self._leave_time = 0.0
        if new_state != WORKING:      # বসা অবস্থা ছাড়া কখনো device চালু থাকে না
            self.monitor_on = False
            self.lamp_on = False

    def update(self, dt):
        # কী করছে: dt সময় এগিয়ে state machine চালায় — ওঠা/হাঁটা/বসা/কাজ/ফেরা সব ধাপ
        # কেন লাগছে: টগল করলে ক্যারেক্টার নিজে থেকে ঠিক অ্যানিমেশনে লক্ষ্য অবস্থায় পৌঁছায়
        # real world-এ এটা কোথায় দেখা যায়: গেম লুপের প্রতি টিকে চরিত্রের state আপডেট
        dt = min(dt, config.DT_CLAMP)        # বড় dt clamp — teleport আটকায়
        prev = self.position()               # facing হিসাবের জন্য আগের অবস্থান

        s = self.state
        if s == IN_BED:
            if self.target_working:
                self._enter(GETTING_UP)
        elif s == GETTING_UP:                # ছোট, non-interruptible
            self.progress += dt / config.GET_UP_TIME
            if self.progress >= 1.0:
                self._enter(WALKING_TO_DESK if self.target_working else LYING_DOWN)
        elif s == WALKING_TO_DESK:           # interruptible
            if not self.target_working:
                self.state = WALKING_TO_BED
                self.progress = 1.0 - self.progress   # কোনো jump ছাড়াই ঘুরে যায়
            else:
                self.progress += dt / config.WALK_TIME
                if self.progress >= 1.0:
                    self._enter(SITTING_DOWN)
        elif s == SITTING_DOWN:              # ছোট, non-interruptible
            self.progress += dt / config.SIT_TIME
            if self.progress >= 1.0:
                self._enter(WORKING)
        elif s == WORKING:
            if self.target_working:
                self._work_time += dt        # বসার পর ক্রমে device চালু
                self.monitor_on = self._work_time >= config.DEVICE_DELAY
                self.lamp_on = self._work_time >= 2 * config.DEVICE_DELAY
                self._leave_time = 0.0
            else:                            # ছাড়ছে: লাইট → মনিটর → তারপর ওঠা
                self.lamp_on = False
                self._leave_time += dt
                if self._leave_time >= config.DEVICE_DELAY:
                    self.monitor_on = False
                if self._leave_time >= 2 * config.DEVICE_DELAY:
                    self._enter(STANDING_UP)
        elif s == STANDING_UP:              # ছোট, non-interruptible
            self.progress += dt / config.SIT_TIME
            if self.progress >= 1.0:
                self._enter(SITTING_DOWN if self.target_working else WALKING_TO_BED)
        elif s == WALKING_TO_BED:           # interruptible
            if self.target_working:
                self.state = WALKING_TO_DESK
                self.progress = 1.0 - self.progress   # ঘুরে যায়, jump নেই
            else:
                self.progress += dt / config.WALK_TIME
                if self.progress >= 1.0:
                    self._enter(LYING_DOWN)
        elif s == LYING_DOWN:               # ছোট, non-interruptible
            self.progress += dt / config.GET_UP_TIME
            if self.progress >= 1.0:
                self._enter(GETTING_UP if self.target_working else IN_BED)

        cur = self.position()
        dy = cur[1] - prev[1]
        if abs(dy) > 1e-9:                   # নড়লে facing হালনাগাদ (উপরে=পিঠ, নিচে=সামনে)
            self.moving_up = dy < 0

    def position(self):
        # কী করছে: বর্তমান state ও progress থেকে দাঁড়ানো/হাঁটা স্প্রাইটের top-left অবস্থান দেয়
        # কেন লাগছে: হাঁটা Bezier পথে, ওঠা/শোয়া/বসা সরল পথে — সব এক জায়গায় হিসাব
        # real world-এ এটা কোথায় দেখা যায়: অ্যানিমেশন সিস্টেমে সময়/অগ্রগতি → রূপান্তর মান
        s = self.state
        p = self.progress
        if s == GETTING_UP:
            return _lerp(config.HEAD_SLEEP_POS, config.WALK_P0, p)
        if s == LYING_DOWN:
            return _lerp(config.WALK_P0, config.HEAD_SLEEP_POS, p)
        if s == WALKING_TO_DESK:
            t = ease_in_out(p)
            return cubic_bezier(config.WALK_P0, config.WALK_P1, config.WALK_P2, config.WALK_P3, t)
        if s == WALKING_TO_BED:
            t = 1.0 - ease_in_out(p)          # উল্টো দিকে একই বক্ররেখা
            return cubic_bezier(config.WALK_P0, config.WALK_P1, config.WALK_P2, config.WALK_P3, t)
        if s == SITTING_DOWN:
            return _lerp(config.WALK_P3, config.SIT_STAND_POS, p)
        if s == STANDING_UP:
            return _lerp(config.SIT_STAND_POS, config.WALK_P3, p)
        if s == WORKING:
            return config.SIT_STAND_POS
        return config.HEAD_SLEEP_POS          # IN_BED

    def _walk_sprite(self, time_now):
        # কী করছে: হাঁটার সময় STEP_INTERVAL-এ WALK_A/WALK_B পাল্টায় ও facing অনুযায়ী front/back বাছে
        # কেন লাগছে: পা নড়ার ভাব ও সঠিক দিক (পিঠ/সামনে) দেখাতে
        # real world-এ এটা কোথায় দেখা যায়: sprite-sheet অ্যানিমেশনে সময় ধরে frame বদল
        frame = int(time_now / config.STEP_INTERVAL) % 2
        if self.moving_up:
            return (sprites.WALK_A_BACK if frame == 0 else sprites.WALK_B_BACK)
        return (sprites.WALK_A if frame == 0 else sprites.WALK_B)

    def _stand_sprite(self):
        # কী করছে: দাঁড়ানো স্প্রাইট front না back, facing অনুযায়ী দেয়
        # কেন লাগছে: ওঠা/বসা/শোয়ার সময় সঠিক দিকে মুখ/পিঠ দেখাতে
        # real world-এ এটা কোথায় দেখা যায়: চরিত্রের direction অনুযায়ী sprite নির্বাচন
        return sprites.STAND_BACK if self.moving_up else sprites.STAND

    def draw(self, time_now):
        # কী করছে: বর্তমান state অনুযায়ী সঠিক স্প্রাইট আঁকে — ঘুম, বসা+টাইপিং, হাঁটা(bob), বা বসা/ওঠা(squash)
        # কেন লাগছে: এক জায়গা থেকে state → দৃশ্য; main শুধু এটা ডাকে
        # real world-এ এটা কোথায় দেখা যায়: চরিত্রের current animation state রেন্ডার করা
        s = self.state
        if s == IN_BED:
            draw_sprite(*config.HEAD_SLEEP_POS, sprites.HEAD_SLEEP, sprites.HEAD_SLEEP_COLORS)
            return
        if s == WORKING:
            draw_sitting(time_now)
            return

        x, y = self.position()
        x, y = int(round(x)), int(round(y))

        if s in (WALKING_TO_DESK, WALKING_TO_BED):
            frame = int(time_now / config.STEP_INTERVAL) % 2
            bob = -1 if frame == 0 else 0          # প্রতি পদক্ষেপে ১px bob
            sprite = self._walk_sprite(time_now)
            draw_sprite(x, y + bob, sprite, sprites.CHAR_COLORS)
        elif s in (SITTING_DOWN, STANDING_UP):
            # বসা/ওঠার সময় পায়ের কাছে pivot করে সামান্য squash (glScalef about feet)
            if s == SITTING_DOWN:
                squash = 1.0 - (1.0 - config.SIT_SQUASH) * self.progress
            else:
                squash = config.SIT_SQUASH + (1.0 - config.SIT_SQUASH) * self.progress
            feet_y = y + _STAND_H                   # স্প্রাইটের নিচ (পা)
            glPushMatrix()
            glTranslatef(0, feet_y, 0)             # pivot পায়ে নিই
            glScalef(1, squash, 1)                 # শুধু উল্লম্বে চাপা
            glTranslatef(0, -feet_y, 0)            # আবার ফেরত
            draw_sprite(x, y, self._stand_sprite(), sprites.CHAR_COLORS)
            glPopMatrix()
        else:                                      # GETTING_UP, LYING_DOWN
            draw_sprite(x, y, self._stand_sprite(), sprites.CHAR_COLORS)
