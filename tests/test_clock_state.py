"""tests/test_clock_state.py — Dhaka দিন/মধ্যরাত split, টাইমস্ট্যাম্প পার্সিং ও AppState হিসাব।

চালানো: pytest tests/test_clock_state.py
"""

import dataclasses
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clock
import panel
import state

DHAKA = clock.DHAKA
T0 = 1_700_000_000.0


def dhaka(y, m, d, hh=0, mm=0, ss=0):
    # Dhaka-র দেয়াল ঘড়ির সময়কে epoch সেকেন্ডে বদলায় (টেস্ট পড়তে সহজ হয়)
    return datetime(y, m, d, hh, mm, ss, tzinfo=DHAKA).timestamp()


# ---------------- clock ----------------

def test_dhaka_today_is_utc_plus_six():
    # UTC-তে 2026-10-20 18:30 মানে Dhaka-তে পরদিন 00:30
    assert clock.dhaka_today(datetime(2026, 10, 20, 18, 30,
                                      tzinfo=timezone.utc).timestamp()).isoformat() == "2026-10-21"
    assert clock.dhaka_today(datetime(2026, 10, 20, 17, 30,
                                      tzinfo=timezone.utc).timestamp()).isoformat() == "2026-10-20"


def test_parse_ts_accepts_unix_and_iso():
    assert clock.parse_ts(T0) == T0
    assert clock.parse_ts(str(T0)) == T0
    assert clock.parse_ts("2023-11-14T22:13:20+00:00") == T0
    assert clock.parse_ts("2023-11-14T22:13:20Z") == T0          # Postgres/JS-এর Z রূপ
    assert clock.parse_ts("2023-11-14T22:13:20") == T0           # offset ছাড়া → UTC ধরি


def test_parse_ts_rejects_junk():
    for bad in (None, "", "   ", "not a time", True, {}, []):
        assert clock.parse_ts(bad) is None


def test_fmt_duration_matches_the_panel():
    for seconds in (0, -5, 59, 60, 3600, 3900, 86399):
        assert clock.fmt_duration(seconds) == panel.format_time(seconds)
    assert clock.fmt_duration(3900) == "1h 05m"


# ---------------- AppState: সময় হিসাব ----------------

def test_today_seconds_counts_the_running_session():
    app = state.AppState("samee", "rifat", T0)
    app.set_working(True, T0)
    assert app.snapshot(T0 + 90).me.today_seconds == 90
    app.set_working(False, T0 + 90)
    assert app.snapshot(T0 + 500).me.today_seconds == 90        # থামার পর বাড়ে না


def test_set_working_reports_only_real_changes():
    app = state.AppState("samee", "rifat", T0)
    assert app.set_working(True, T0) is True
    assert app.set_working(True, T0 + 5) is False               # একই মান → কিছুই হয়নি
    assert app.snapshot(T0 + 60).me.since is not None


def test_sessions_add_up():
    app = state.AppState("samee", "rifat", T0)
    app.set_working(True, T0)
    app.set_working(False, T0 + 100)
    app.set_working(True, T0 + 200)
    assert app.snapshot(T0 + 250).me.today_seconds == 150


# ---------------- মধ্যরাত split ----------------

def test_midnight_resets_the_counter():
    before = dhaka(2026, 10, 20, 23, 59, 30)
    after = dhaka(2026, 10, 21, 0, 0, 30)
    app = state.AppState("samee", "rifat", before)
    app.set_working(True, before - 3600)                        # আগে থেকেই এক ঘণ্টা কাজ
    assert app.snapshot(before).me.today_seconds == 3600
    assert app.roll_day(after) is True
    assert app.snapshot(after).me.today_seconds == 0            # মধ্যরাতের আগের সময় ফেলে দেওয়া হয়
    assert app.snapshot(after + 120).me.today_seconds == 120    # নতুন দিনে নতুন করে গোনা


def test_roll_day_does_nothing_inside_the_same_day():
    app = state.AppState("samee", "rifat", dhaka(2026, 10, 20, 9, 0))
    assert app.roll_day(dhaka(2026, 10, 20, 23, 59)) is False


def test_midnight_while_not_working_just_clears():
    before = dhaka(2026, 10, 20, 22, 0)
    app = state.AppState("samee", "rifat", before)
    app.set_working(True, before)
    app.set_working(False, before + 600)
    app.roll_day(dhaka(2026, 10, 21, 0, 0, 1))
    assert app.snapshot(dhaka(2026, 10, 21, 1, 0)).me.today_seconds == 0


# ---------------- resume ----------------

def test_adopt_today_restores_the_server_total():
    app = state.AppState("samee", "rifat", T0)
    app.adopt_today(1800, T0)
    assert app.snapshot(T0).me.today_seconds == 1800


def test_adopt_today_does_not_double_count_a_running_session():
    app = state.AppState("samee", "rifat", T0)
    app.set_working(True, T0 - 300)            # ৫ মিনিট ধরে চলছে
    app.adopt_today(1800, T0)                  # সার্ভার বলল আজ ৩০ মিনিট হয়েছে
    assert app.snapshot(T0).me.today_seconds == 1800
    assert app.snapshot(T0 + 60).me.today_seconds == 1860       # এখন থেকে আবার গোনা


# ---------------- snapshot ও ভিউ ----------------

def test_snapshot_is_frozen_and_independent():
    app = state.AppState("samee", "rifat", T0)
    snap = app.snapshot(T0)
    app.set_working(True, T0)
    assert snap.me.working is False                             # পুরনো snapshot বদলায়নি
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.me.working = True                                  # ভিউ বদলানো যায় না


def test_me_is_always_online_and_peer_starts_offline():
    snap = state.AppState("rifat", "samee", T0).snapshot(T0)
    assert snap.me.user_id == "rifat" and snap.me.name == "Rifat" and snap.me.online is True
    assert snap.peer.user_id == "samee" and snap.peer.online is False
    assert snap.connected is False
    assert snap.now.tzinfo is not None


# ---------------- প্যানেলের স্ট্যাটাস লাইন (design §2.1) ----------------

def build(me_working=False, peer_working=False, peer_online=True, connected=True):
    app = state.AppState("samee", "rifat", T0)
    app.set_working(me_working, T0)
    app.set_peer(working=peer_working, online=peer_online)
    app.set_connected(connected)
    return app.snapshot(T0)


def test_status_line_rules():
    import config
    assert panel.status_line(build())[0] == "Claude is free"
    assert panel.status_line(build(me_working=True))[0] == "You are working"
    assert panel.status_line(build(peer_working=True))[0] == "Rifat is working"
    text, color = panel.status_line(build(me_working=True, peer_working=True))
    assert text == "Both of you are on it!" and color == config.WARNING
    text, color = panel.status_line(build(peer_online=False))
    assert text == "Rifat is offline" and color == config.OFFLINE_GREY


def test_working_beats_offline_in_the_status_line():
    # সঙ্গী অফলাইন, কিন্তু আমি কাজ করছি → আমার অবস্থাই বেশি কাজের তথ্য
    assert panel.status_line(build(me_working=True, peer_online=False))[0] == "You are working"
