"""tests/test_dibs.py — "পরেরবার আমি" (dibs) নিয়ম: সেট, auto-clear, মেয়াদ, বাটন ও পুশ।

চালানো: pytest tests/test_dibs.py
(টোস্টের নিয়ম tests/test_alerts.py-তে।)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clock
import config
import panel
import state
import sync
import tray

T0 = 1_700_000_000.0


def app(me="samee", peer="rifat"):
    return state.AppState(me, peer, T0)


def snap(me_dibs=False, peer_working=False, peer_dibs=False, me_working=False):
    st = app()
    if me_dibs:
        st.set_dibs(True, T0)
    if me_working:
        st.set_working(True, T0)
    st.set_peer(working=peer_working, wants_next=peer_dibs, online=True)
    return st.snapshot(T0)


# ---------------- state: সেট ও বাতিল ----------------

def test_set_dibs_reports_only_real_changes():
    st = app()
    assert st.set_dibs(True, T0) is True
    assert st.set_dibs(True, T0 + 5) is False
    assert st.snapshot(T0).me.wants_next is True
    assert st.set_dibs(False, T0 + 10) is True
    assert st.snapshot(T0).me.wants_next is False


def test_cancel_clears_the_timestamp():
    st = app()
    st.set_dibs(True, T0)
    assert st.dibs_since() == T0
    st.set_dibs(False, T0 + 1)
    assert st.dibs_since() is None


def test_starting_work_clears_my_dibs():
    # techspec §9: যে ডেকেছে সে কাজ শুরু করলেই dibs আপনা-আপনি যায়
    st = app()
    st.set_dibs(True, T0)
    st.set_working(True, T0 + 60)
    assert st.snapshot(T0 + 60).me.wants_next is False
    assert st.dibs_since() is None


def test_stopping_work_does_not_bring_dibs_back():
    st = app()
    st.set_dibs(True, T0)
    st.set_working(True, T0 + 60)
    st.set_working(False, T0 + 120)
    assert st.snapshot(T0 + 120).me.wants_next is False


# ---------------- মেয়াদ ----------------

def test_dibs_expires_after_two_hours():
    st = app()
    st.set_dibs(True, T0)
    assert st.expire_dibs(T0 + config.DIBS_EXPIRE - 1) is False
    assert st.snapshot(T0).me.wants_next is True
    assert st.expire_dibs(T0 + config.DIBS_EXPIRE + 1) is True
    assert st.snapshot(T0).me.wants_next is False


def test_expire_is_a_no_op_without_dibs():
    st = app()
    assert st.expire_dibs(T0 + 10 * config.DIBS_EXPIRE) is False


def test_expire_only_fires_once():
    st = app()
    st.set_dibs(True, T0)
    late = T0 + config.DIBS_EXPIRE + 1
    assert st.expire_dibs(late) is True
    assert st.expire_dibs(late + 1) is False


# ---------------- প্যানেলের বাটন (design §2.3) ----------------

def test_button_only_shows_while_the_peer_works():
    assert panel.dibs_visible(snap(peer_working=True)) is True
    assert panel.dibs_visible(snap()) is False
    assert panel.dibs_visible(snap(me_working=True)) is False


def test_hit_test_covers_the_box_only():
    x, y, w, h = config.DIBS_BOX
    assert panel.dibs_hit(x + 1, y + 1) is True
    assert panel.dibs_hit(x + w - 0.5, y + h - 0.5) is True
    assert panel.dibs_hit(x - 1, y + 1) is False
    assert panel.dibs_hit(x + 1, y + h + 1) is False
    assert panel.dibs_hit(config.PANEL_CENTER_X, config.CARD1_BOX[1]) is False   # কার্ডে নয়


def test_the_button_sits_in_the_old_toggle_space():
    x, y, w, h = config.DIBS_BOX
    assert x + w // 2 == config.PANEL_CENTER_X          # প্যানেলের মাঝ বরাবর
    assert config.PANEL_SUB_Y < y                       # সাব-স্ট্যাটাসের নিচে
    assert y + h < config.CARD1_BOX[1]                  # কার্ডের উপরে


# ---------------- ট্রে আইটেম প্যানেলের আয়না ----------------

def test_tray_item_mirrors_the_button():
    holder = {"snap": snap(peer_working=True)}
    icon = tray.Tray(tray.make_commands(), snapshot_fn=lambda: holder["snap"])
    assert icon._dibs_enabled() is True
    assert icon._dibs_label() == "Call dibs"

    holder["snap"] = snap(peer_working=True, me_dibs=True)
    assert icon._dibs_label() == "Cancel dibs"

    holder["snap"] = snap()                              # কেউ কাজ করছে না
    assert icon._dibs_enabled() is False


def test_cancelling_stays_possible_after_the_peer_stops():
    # সঙ্গী থেমে গেলে বাটন লুকায়, কিন্তু ট্রে থেকে নিজের dibs বাতিল করা যেতে হবে
    icon = tray.Tray(tray.make_commands(), snapshot_fn=lambda: snap(me_dibs=True))
    assert icon._dibs_enabled() is True
    assert icon._dibs_label() == "Cancel dibs"


def test_tray_survives_a_missing_snapshot():
    icon = tray.Tray(tray.make_commands())
    assert icon._dibs_enabled() is False
    assert icon._dibs_label() == "Call dibs"


# ---------------- সার্ভারে পুশ ----------------

def test_status_fields_carry_dibs():
    st = app()
    st.set_dibs(True, T0)
    fields = sync.status_fields(st.snapshot(T0), T0, st.dibs_since())
    assert fields["wants_next"] is True
    assert fields["wants_next_at"] == clock.to_dt(T0).isoformat()


def test_status_fields_send_null_when_no_dibs():
    st = app()
    fields = sync.status_fields(st.snapshot(T0), T0, st.dibs_since())
    assert fields["wants_next"] is False
    assert fields["wants_next_at"] is None               # RPC-তে null বসবে


def test_peer_dibs_arrives_from_the_server():
    st = app()
    engine = sync.Sync(st, None, me="samee", peer="rifat")
    engine.apply_state({
        "server_now": "2023-11-14T22:13:20+00:00",
        "status": [
            {"user_id": "rifat", "display_name": "Rifat", "working": True,
             "wants_next": True, "last_heartbeat": "2023-11-14T22:13:20+00:00",
             "today_seconds": 0, "since": None},
        ],
    }, T0)
    assert st.snapshot(T0).peer.wants_next is True


# ---------------- Phase 14b: dibs percentage ----------------

def test_set_dibs_with_pct():
    st = app()
    st.set_dibs(True, T0, pct=75)
    s = st.snapshot(T0)
    assert s.me.wants_next is True
    assert s.me.wants_next_pct == 75


def test_pct_clears_on_cancel():
    st = app()
    st.set_dibs(True, T0, pct=60)
    st.set_dibs(False, T0 + 1)
    assert st.snapshot(T0).me.wants_next_pct is None


def test_pct_clears_when_starting_work():
    st = app()
    st.set_dibs(True, T0, pct=80)
    st.set_working(True, T0 + 60)
    s = st.snapshot(T0 + 60)
    assert s.me.wants_next is False
    assert s.me.wants_next_pct is None


def test_pct_clears_on_expire():
    st = app()
    st.set_dibs(True, T0, pct=30)
    st.expire_dibs(T0 + config.DIBS_EXPIRE + 1)
    assert st.snapshot(T0).me.wants_next_pct is None


def test_status_fields_carry_pct():
    st = app()
    st.set_dibs(True, T0, pct=55)
    fields = sync.status_fields(st.snapshot(T0), T0, st.dibs_since())
    assert fields["wants_next_pct"] == 55


def test_status_fields_null_pct_when_no_dibs():
    st = app()
    fields = sync.status_fields(st.snapshot(T0), T0, st.dibs_since())
    assert fields["wants_next_pct"] is None


def test_apply_state_with_pct():
    st = app()
    engine = sync.Sync(st, None, me="samee", peer="rifat")
    engine.apply_state({
        "server_now": "2023-11-14T22:13:20+00:00",
        "status": [
            {"user_id": "rifat", "display_name": "Rifat", "working": True,
             "wants_next": True, "wants_next_pct": 40,
             "last_heartbeat": "2023-11-14T22:13:20+00:00",
             "today_seconds": 0, "since": None},
        ],
    }, T0)
    s = st.snapshot(T0)
    assert s.peer.wants_next is True
    assert s.peer.wants_next_pct == 40


def test_apply_state_without_pct():
    st = app()
    engine = sync.Sync(st, None, me="samee", peer="rifat")
    engine.apply_state({
        "server_now": "2023-11-14T22:13:20+00:00",
        "status": [
            {"user_id": "rifat", "display_name": "Rifat", "working": True,
             "wants_next": True,
             "last_heartbeat": "2023-11-14T22:13:20+00:00",
             "today_seconds": 0, "since": None},
        ],
    }, T0)
    assert st.snapshot(T0).peer.wants_next_pct is None


def test_slider_hit_and_pct_from_x():
    mid_x = (config.SLIDER_X0 + config.SLIDER_X1) / 2
    assert panel.slider_hit(mid_x, config.SLIDER_Y + 1) is True
    assert panel.slider_hit(config.SLIDER_X0 - 1, config.SLIDER_Y + 1) is False
    assert panel.slider_pct_from_x(config.SLIDER_X0) == 0
    assert panel.slider_pct_from_x(config.SLIDER_X1) == 100


def test_slider_pct_snaps_to_step():
    span = config.SLIDER_X1 - config.SLIDER_X0
    x_for_53 = config.SLIDER_X0 + 0.53 * span
    pct = panel.slider_pct_from_x(x_for_53)
    assert pct == 50
    assert pct % config.DIBS_PCT_STEP == 0
    x_for_66 = config.SLIDER_X0 + 0.66 * span
    assert panel.slider_pct_from_x(x_for_66) == 70
