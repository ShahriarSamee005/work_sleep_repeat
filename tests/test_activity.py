"""tests/test_activity.py — হুক ইভেন্ট → working নিয়ম (techspec §4.4) পরীক্ষা করে।

চালানো: pytest tests/test_activity.py
সময় সবসময় হাতে দেওয়া হয় (activity-তে ঘড়ি নেই), তাই টেস্টে অপেক্ষা করতে হয় না।
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import activity
import config

IDLE = 60.0        # টেস্টে ছোট মান — আসল ডিফল্ট ৬০০s
STALE = 300.0      # আসল ডিফল্ট ১৮০০s
T0 = 1_700_000_000.0


def engine():
    return activity.Activity(idle_timeout=IDLE, stale_cap=STALE)


def ev(name, session="s1"):
    return {"hook_event_name": name, "session_id": session}


def test_defaults_come_from_config():
    a = activity.Activity()
    assert a.idle_timeout == config.IDLE_TIMEOUT
    assert a.stale_cap == config.TURN_STALE_CAP


def test_starts_not_working():
    assert engine().tick(T0) is False


def test_prompt_starts_working():
    a = engine()
    a.handle(ev("UserPromptSubmit"), T0)
    assert a.tick(T0) is True


def test_turn_stays_working_while_tools_run():
    # এক প্রম্পট, ২৫ মিনিট টুল চলছে — turn_active থাকায় idle timeout লাগে না (appflow §4)
    a = engine()
    a.handle(ev("UserPromptSubmit"), T0)
    now = T0
    for _ in range(5):
        now += IDLE + 10                      # idle timeout-এর চেয়ে বড় ফাঁক
        a.handle(ev("PostToolUse"), now)
        assert a.tick(now) is True


def test_stop_keeps_working_until_idle_timeout():
    a = engine()
    a.handle(ev("UserPromptSubmit"), T0)
    a.handle(ev("Stop"), T0 + 5)
    assert a.tick(T0 + 5) is True             # Stop-এর পরেও কাজ করছে ধরি
    assert a.tick(T0 + 5 + IDLE - 1) is True  # idle timeout-এর ঠিক আগে
    assert a.tick(T0 + 5 + IDLE + 1) is False  # পরে → ঘুমাতে যায়


def test_notification_is_keep_alive():
    a = engine()
    a.handle(ev("SessionStart"), T0)
    a.handle(ev("Notification"), T0 + IDLE - 1)
    assert a.tick(T0 + IDLE + 1) is True      # Notification শেষ ইভেন্টের সময় এগিয়ে দিয়েছে


def test_session_end_stops_working():
    a = engine()
    a.handle(ev("UserPromptSubmit"), T0)
    a.handle(ev("SessionEnd"), T0 + 1)
    assert a.sessions == {}
    assert a.tick(T0 + 1) is False


def test_two_sessions_closing_one_keeps_working():
    # plan Step B gate: দুটি Claude Code সেশন, একটি বন্ধ করলেও বিছানায় যাওয়া চলবে না
    a = engine()
    a.handle(ev("UserPromptSubmit", "a"), T0)
    a.handle(ev("UserPromptSubmit", "b"), T0)
    a.handle(ev("SessionEnd", "a"), T0 + 1)
    assert a.tick(T0 + 1) is True
    a.handle(ev("SessionEnd", "b"), T0 + 2)
    assert a.tick(T0 + 2) is False


def test_stale_cap_drops_crashed_session():
    # টার্নের মাঝে Claude Code মারা গেল: Stop/SessionEnd আসেনি, turn_active আটকে আছে (appflow §6)
    a = engine()
    a.handle(ev("UserPromptSubmit"), T0)
    assert a.tick(T0 + STALE - 1) is True
    assert a.tick(T0 + STALE + 1) is False
    assert a.sessions == {}                   # বাসি সেশন তালিকা থেকেও বাদ


def test_unknown_event_ignored():
    a = engine()
    assert a.handle(ev("PreToolUse"), T0) is False
    assert a.handle({"hook_event_name": "UserPromptSubmit"}, T0) is True   # session_id ছাড়া চলে
    assert a.handle("not a dict", T0) is False
    assert a.tick(T0) is True                 # শুধু চেনা ইভেন্টটিই গোনা হয়েছে


def test_missing_session_id_shares_one_bucket():
    a = engine()
    a.handle({"hook_event_name": "UserPromptSubmit"}, T0)
    a.handle({"hook_event_name": "Stop"}, T0 + 1)
    assert list(a.sessions) == [activity.UNKNOWN_SESSION]
    assert a.tick(T0 + 1 + IDLE + 1) is False


def test_session_created_by_any_event():
    # SessionStart না এলেও (হুক পরে বসানো হলে) প্রথম ইভেন্টেই সেশন তৈরি হয়
    a = engine()
    a.handle(ev("PostToolUse"), T0)
    assert a.tick(T0) is True
