"""tests/test_character.py — OpenGL ছাড়াই Character state machine পরীক্ষা করে (plain asserts)।

চালানো: python tests/test_character.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import character as C
import config

DT = 1.0 / 60.0            # সিমুলেশনের ছোট ধাপ
_fails = []


def check(name, ok):
    # কী করছে: একটি শর্ত সত্য হলে PASS ছাপে, নাহলে FAIL গণনা করে
    # কেন লাগছে: প্রতিটি পরীক্ষার ফল পরিষ্কারভাবে দেখাতে
    # real world-এ এটা কোথায় দেখা যায়: test runner-এর assert/report
    print(("PASS" if ok else "FAIL"), "-", name)
    if not ok:
        _fails.append(name)


def advance_until(ch, predicate, limit=20.0):
    # কী করছে: predicate সত্য না হওয়া পর্যন্ত (বা limit সময় পর্যন্ত) ছোট ধাপে update চালায়
    # কেন লাগছে: নির্দিষ্ট state/progress-এ পৌঁছাতে সিমুলেশন এগিয়ে নিতে
    # real world-এ এটা কোথায় দেখা যায়: টেস্টে নির্দিষ্ট অবস্থায় পৌঁছানো
    steps = int(limit / DT)
    for _ in range(steps):
        if predicate():
            return True
        ch.update(DT)
    return predicate()


def test_full_cycle_order():
    # কী করছে: IN_BED → WORKING → IN_BED পূর্ণ চক্রে সব state ঠিক ক্রমে আসে কিনা দেখে
    ch = C.Character("t")
    ch.set_working(True)
    seq = [ch.state]
    for _ in range(int(6.0 / DT)):
        ch.update(DT)
        if ch.state != seq[-1]:
            seq.append(ch.state)
    to_work = [C.IN_BED, C.GETTING_UP, C.WALKING_TO_DESK, C.SITTING_DOWN, C.WORKING]
    check("to-work visits every state in order", seq == to_work)

    ch.set_working(False)
    seq2 = [ch.state]
    for _ in range(int(8.0 / DT)):
        ch.update(DT)
        if ch.state != seq2[-1]:
            seq2.append(ch.state)
    to_bed = [C.WORKING, C.STANDING_UP, C.WALKING_TO_BED, C.LYING_DOWN, C.IN_BED]
    check("to-bed visits every state in order", seq2 == to_bed)
    check("blanket neat only at the end (IN_BED)", ch.bed_is_messy() is False)


def test_devices_order_and_only_seated():
    # কী করছে: device চালু/বন্ধের ক্রম (মনিটর আগে, ল্যাম্প পরে; বন্ধে উল্টো) ও শুধু বসা অবস্থায় চালু — যাচাই
    ch = C.Character("t")
    ch.set_working(True)
    mon_on_t = lamp_on_t = None
    devices_only_seated = True
    tsim = 0.0
    for _ in range(int(6.0 / DT)):
        ch.update(DT)
        tsim += DT
        if (ch.monitor_on or ch.lamp_on) and ch.state != C.WORKING:
            devices_only_seated = False
        if ch.monitor_on and mon_on_t is None:
            mon_on_t = tsim
        if ch.lamp_on and lamp_on_t is None:
            lamp_on_t = tsim
    check("monitor turns on before lamp", mon_on_t is not None and lamp_on_t is not None and mon_on_t < lamp_on_t)

    # বন্ধের ক্রম: ল্যাম্প আগে বন্ধ, মনিটর পরে
    ch.set_working(False)
    lamp_off_t = mon_off_t = None
    tsim = 0.0
    for _ in range(int(8.0 / DT)):
        ch.update(DT)
        tsim += DT
        if (ch.monitor_on or ch.lamp_on) and ch.state != C.WORKING:
            devices_only_seated = False
        if (not ch.lamp_on) and lamp_off_t is None:
            lamp_off_t = tsim
        if (not ch.monitor_on) and mon_off_t is None:
            mon_off_t = tsim
    check("lamp turns off before monitor", lamp_off_t < mon_off_t)
    check("devices are on only while seated (WORKING)", devices_only_seated)


def _reverse_no_jump(p_target):
    # কী করছে: WALKING_TO_DESK-এ progress≈p_target-এ পৌঁছে target উল্টে দিয়ে দেখে position লাফায় কিনা
    # কেন লাগছে: ease_in_out symmetric বলে reverse করলে অবস্থান একই থাকার কথা (jump < 1px)
    ch = C.Character("t")
    ch.set_working(True)
    advance_until(ch, lambda: ch.state == C.WALKING_TO_DESK)
    advance_until(ch, lambda: ch.state != C.WALKING_TO_DESK or ch.progress >= p_target)
    if ch.state != C.WALKING_TO_DESK:
        return None
    before = ch.position()
    ch.set_working(False)           # মাঝপথে উল্টে দিই
    ch.update(1e-6)                  # switch এই update-এ ঘটে (progress = 1 - progress)
    after = ch.position()
    dist = math.hypot(after[0] - before[0], after[1] - before[1])
    return ch.state, dist


def test_reverse_no_jump():
    # কী করছে: হাঁটার ৩০%, ৫০%, ৯০%-এ reverse করলে position jump < 1px কিনা যাচাই
    for p in (0.30, 0.50, 0.90):
        res = _reverse_no_jump(p)
        ok = res is not None and res[0] == C.WALKING_TO_BED and res[1] < 1.0
        check("reverse at %d%% no jump (dist<1px)" % int(p * 100), ok)


def test_toggle_during_getting_up():
    # কী করছে: GETTING_UP চলাকালীন টগল করলে তা GETTING_UP শেষ হওয়ার পরে প্রয়োগ হয় কিনা দেখে
    ch = C.Character("t")
    ch.set_working(True)
    ch.update(DT)                    # IN_BED → GETTING_UP
    check("entered GETTING_UP", ch.state == C.GETTING_UP)
    ch.set_working(False)            # মাঝপথে উল্টো টগল
    stayed = True
    for _ in range(int(config.GET_UP_TIME / DT) - 1):
        ch.update(DT)
        if ch.state != C.GETTING_UP:
            stayed = False
            break
    check("stays in GETTING_UP (non-interruptible)", stayed)
    advance_until(ch, lambda: ch.state != C.GETTING_UP, limit=1.0)
    check("after GETTING_UP goes to LYING_DOWN (target applied)", ch.state == C.LYING_DOWN)


def test_huge_dt_clamped():
    # কী করছে: বিশাল dt দিলে এক টিকে সর্বোচ্চ DT_CLAMP এগোয় কিনা (teleport হয় না) দেখে
    ch = C.Character("t")
    ch.set_working(True)
    advance_until(ch, lambda: ch.state == C.WALKING_TO_DESK)
    p0 = ch.progress
    ch.update(1000.0)               # বিশাল dt
    advanced = ch.progress - p0
    expected_max = config.DT_CLAMP / config.WALK_TIME + 1e-6
    check("huge dt clamped (still WALKING_TO_DESK)", ch.state == C.WALKING_TO_DESK)
    check("huge dt advances <= DT_CLAMP worth", advanced <= expected_max)


if __name__ == "__main__":
    test_full_cycle_order()
    test_devices_order_and_only_seated()
    test_reverse_no_jump()
    test_toggle_during_getting_up()
    test_huge_dt_clamped()
    print()
    print("ALL PASS" if not _fails else ("FAILED: " + ", ".join(_fails)))
    sys.exit(0 if not _fails else 1)
