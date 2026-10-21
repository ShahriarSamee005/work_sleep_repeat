"""tests/test_alerts.py — কোন ঘটনায় কোন টোস্ট বাজে ও কতবার (techspec §9, design §5)।

চালানো: pytest tests/test_alerts.py
স্ক্রিপ্ট করা snapshot পরপর দিয়ে নিয়ম যাচাই করি — ঘড়ি বা নেটওয়ার্ক লাগে না।
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import alerts
import config
import state

T0 = 1_700_000_000.0


def snap(now, me_working=False, peer_working=False, peer_online=True, connected=True,
         me_dibs=False, peer_dibs=False):
    # কী করছে: চাওয়া অবস্থায় একটি StateSnapshot বানায় (me = samee, peer = rifat)
    # কেন লাগছে: alerts শুধু দুটি snapshot তুলনা করে — তাই টেস্টে হাতে বানানোই যথেষ্ট
    app = state.AppState("samee", "rifat", now)
    if me_dibs:
        app.set_dibs(True, now)
    app.set_working(me_working, now)      # কাজ শুরু করলে dibs আপনিই যায় — ক্রমটা তাই গুরুত্বপূর্ণ
    if me_dibs and not me_working:
        app.set_dibs(True, now)
    app.set_peer(working=peer_working, online=peer_online, wants_next=peer_dibs)
    app.set_connected(connected)
    return app.snapshot(now)


def kinds(toasts):
    return [t.kind for t in toasts]


# ---------------- "It's free" ----------------

def test_peer_finishing_fires_the_free_toast():
    memory = alerts.Memory()
    before = snap(T0, peer_working=True)
    after = snap(T0 + 1, peer_working=False)
    toasts = alerts.check(before, after, memory)
    assert kinds(toasts) == [alerts.FREE]
    assert toasts[0].title == "Claude is free"
    assert toasts[0].body == "Rifat just finished."       # design §5-এর হুবহু কপি


def test_free_fires_once_per_transition():
    memory = alerts.Memory()
    before = snap(T0, peer_working=True)
    after = snap(T0 + 1, peer_working=False)
    assert kinds(alerts.check(before, after, memory)) == [alerts.FREE]
    later = snap(T0 + 2, peer_working=False)
    assert alerts.check(after, later, memory) == []        # সঙ্গী এখনো ফাঁকা — আবার বাজবে না


def test_free_fires_again_on_a_second_round():
    memory = alerts.Memory()
    a = snap(T0, peer_working=True)
    b = snap(T0 + 1, peer_working=False)
    assert kinds(alerts.check(a, b, memory)) == [alerts.FREE]
    c = snap(T0 + 2, peer_working=True)          # সঙ্গী আবার শুরু করল
    assert alerts.check(b, c, memory) == []
    d = snap(T0 + 3, peer_working=False)         # ও আবার থামল
    assert kinds(alerts.check(c, d, memory)) == [alerts.FREE]


def test_no_free_toast_while_i_am_working():
    # আমি নিজেই চালাচ্ছি — "Claude ফাঁকা" খবরটা তখন কাজের নয়
    memory = alerts.Memory()
    before = snap(T0, me_working=True, peer_working=True)
    after = snap(T0 + 1, me_working=True, peer_working=False)
    assert alerts.check(before, after, memory) == []


def test_peer_starting_is_not_an_alert():
    memory = alerts.Memory()
    before = snap(T0)
    after = snap(T0 + 1, peer_working=True)
    assert alerts.check(before, after, memory) == []


# ---------------- দ্বন্দ্ব ----------------

def test_conflict_needs_thirty_seconds():
    memory = alerts.Memory()
    prev = snap(T0, me_working=True)
    start = snap(T0, me_working=True, peer_working=True)
    assert alerts.check(prev, start, memory) == []                    # সবে শুরু
    mid = snap(T0 + config.CONFLICT_AFTER - 1, me_working=True, peer_working=True)
    assert alerts.check(start, mid, memory) == []                     # ৩০s হয়নি
    late = snap(T0 + config.CONFLICT_AFTER + 1, me_working=True, peer_working=True)
    toasts = alerts.check(mid, late, memory)
    assert kinds(toasts) == [alerts.CONFLICT]
    assert toasts[0].title == "You're both on it"
    assert toasts[0].body == "Rifat is also using Claude right now."


def test_conflict_fires_once_per_overlap():
    memory = alerts.Memory()
    prev = snap(T0, me_working=True)
    cur = snap(T0, me_working=True, peer_working=True)
    alerts.check(prev, cur, memory)
    late = snap(T0 + config.CONFLICT_AFTER + 1, me_working=True, peer_working=True)
    assert kinds(alerts.check(cur, late, memory)) == [alerts.CONFLICT]
    later = snap(T0 + config.CONFLICT_AFTER + 60, me_working=True, peer_working=True)
    assert alerts.check(late, later, memory) == []        # একই overlap — আর নয়


def test_a_new_overlap_can_fire_again():
    memory = alerts.Memory()
    a = snap(T0, me_working=True, peer_working=True)
    alerts.check(snap(T0, me_working=True), a, memory)
    b = snap(T0 + config.CONFLICT_AFTER + 1, me_working=True, peer_working=True)
    assert kinds(alerts.check(a, b, memory)) == [alerts.CONFLICT]
    c = snap(T0 + 100, me_working=True, peer_working=False)           # overlap শেষ
    alerts.check(b, c, memory)
    d = snap(T0 + 101, me_working=True, peer_working=True)            # নতুন overlap শুরু
    alerts.check(c, d, memory)
    e = snap(T0 + 101 + config.CONFLICT_AFTER + 1, me_working=True, peer_working=True)
    assert kinds(alerts.check(d, e, memory)) == [alerts.CONFLICT]


def test_short_overlap_never_fires():
    # একজন থামছে, একজন শুরু করছে — ক্ষণিকের overlap-এ বিরক্ত করা হয় না
    memory = alerts.Memory()
    a = snap(T0, me_working=True)
    b = snap(T0 + 1, me_working=True, peer_working=True)
    alerts.check(a, b, memory)
    c = snap(T0 + 5, me_working=False, peer_working=True)
    assert alerts.check(b, c, memory) == []
    assert memory.conflict_since is None


# ---------------- প্রান্ত ----------------

def test_first_snapshot_is_never_an_event():
    memory = alerts.Memory()
    assert alerts.check(None, snap(T0, me_working=True, peer_working=True), memory) == []


def test_conflict_timer_starts_even_on_the_first_snapshot():
    # অ্যাপ চালু হওয়ার সময়ই দুজনে কাজ করছিল → ৩০s পেরোলে টোস্ট আসা উচিত
    memory = alerts.Memory()
    alerts.check(None, snap(T0, me_working=True, peer_working=True), memory)
    assert memory.conflict_since == T0
    late = snap(T0 + config.CONFLICT_AFTER + 1, me_working=True, peer_working=True)
    assert kinds(alerts.check(snap(T0, me_working=True, peer_working=True),
                              late, memory)) == [alerts.CONFLICT]


def test_the_kind_list_is_exactly_these_three():
    # usage ফিচার কাটা — "limits" যেন কখনো ফিরে না আসে
    assert alerts.KINDS == (alerts.FREE, alerts.DIBS, alerts.CONFLICT)
    assert "limits" not in alerts.KINDS


# ---------------- dibs (Phase 14) ----------------

def test_peer_calling_dibs_fires_once():
    memory = alerts.Memory()
    before = snap(T0, me_working=True)
    after = snap(T0 + 1, me_working=True, peer_dibs=True)
    toasts = alerts.check(before, after, memory)
    assert kinds(toasts) == [alerts.DIBS]
    assert toasts[0].title == "Rifat wants it next"
    assert toasts[0].body == "They'll wait until you're done."
    still = snap(T0 + 2, me_working=True, peer_dibs=True)
    assert alerts.check(after, still, memory) == []       # dibs ঝুলে আছে — আবার বাজবে না


def test_peer_dropping_dibs_is_silent():
    memory = alerts.Memory()
    before = snap(T0, me_working=True, peer_dibs=True)
    after = snap(T0 + 1, me_working=True, peer_dibs=False)
    assert alerts.check(before, after, memory) == []


def test_your_turn_replaces_the_plain_free_toast():
    memory = alerts.Memory()
    before = snap(T0, peer_working=True, me_dibs=True)
    after = snap(T0 + 1, peer_working=False, me_dibs=True)
    toasts = alerts.check(before, after, memory)
    assert kinds(toasts) == [alerts.FREE]                  # একই kind, তাই একই on/off সেটিং
    assert toasts[0].title == "Your turn"
    assert toasts[0].body == "Rifat finished. You called dibs."


def test_without_dibs_it_is_the_plain_free_toast():
    memory = alerts.Memory()
    before = snap(T0, peer_working=True)
    after = snap(T0 + 1, peer_working=False)
    assert alerts.check(before, after, memory)[0].title == "Claude is free"
