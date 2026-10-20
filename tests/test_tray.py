"""tests/test_tray.py — ট্রে আইকনের অবস্থা, আইকন তৈরি ও অ্যালার্ট সেটিং সেভ (design §4)।

চালানো: pytest tests/test_tray.py
pystray-র উইন্ডো/থ্রেড ছোঁয়া হয় না — শুধু শুদ্ধ অংশগুলো (icon_state, ছবি, সেটিংস)।
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import sprites
import state
import tray
import userconfig

T0 = 1_700_000_000.0


def snap(me_working=False, peer_working=False, peer_online=True, connected=True):
    app = state.AppState("samee", "rifat", T0)
    app.set_working(me_working, T0)
    app.set_peer(working=peer_working, online=peer_online)
    app.set_connected(connected)
    return app.snapshot(T0)


# ---------------- আইকনের অবস্থা (design §4-এর টেবিল) ----------------

def test_icon_states():
    assert tray.icon_state(snap()) == tray.FREE
    assert tray.icon_state(snap(peer_working=True)) == tray.PEER
    assert tray.icon_state(snap(me_working=True)) == tray.ME
    assert tray.icon_state(snap(me_working=True, peer_working=True)) == tray.CONFLICT


def test_disconnected_wins_over_everything():
    # সার্ভারে পৌঁছাচ্ছি না মানে যা দেখাচ্ছি তা পুরনো হতে পারে — সেটাই আগে জানানো দরকার
    assert tray.icon_state(snap(connected=False)) == tray.OFFLINE
    assert tray.icon_state(snap(me_working=True, connected=False)) == tray.OFFLINE


# ---------------- স্প্রাইট ও ছবি ----------------

def test_tray_grids_are_square():
    for grid in (sprites.TRAY_MOON, sprites.TRAY_LAMP):
        assert len(grid) == 16
        assert {len(row) for row in grid} == {16}


def test_every_state_has_an_icon():
    icons = tray.build_icons()
    assert sorted(icons) == sorted([tray.CONFLICT, tray.FREE, tray.ME,
                                    tray.OFFLINE, tray.PEER])
    for image in icons.values():
        assert image.size == (config.TRAY_ICON_PX, config.TRAY_ICON_PX)
        assert image.mode == "RGBA"


def test_the_badged_icons_differ_from_the_plain_one():
    icons = tray.build_icons()
    assert icons[tray.ME].tobytes() != icons[tray.PEER].tobytes()      # "you" ডট
    assert icons[tray.CONFLICT].tobytes() != icons[tray.PEER].tobytes()  # লাল ডট
    assert icons[tray.OFFLINE].tobytes() != icons[tray.FREE].tobytes()   # ধূসর চাঁদ


def test_icons_have_transparent_corners():
    # ট্রে-র পেছনের রঙ যাই হোক, আইকনের কোণ স্বচ্ছ থাকা উচিত
    image = tray.build_icons()[tray.FREE]
    assert image.getpixel((0, 0))[3] == 0


# ---------------- অ্যালার্ট সেটিংস ----------------

def test_alerts_default_to_on():
    settings = tray.AlertSettings()
    assert settings.is_enabled("free") is True
    assert settings.is_enabled("conflict") is True


def test_toggle_flips_and_reports():
    settings = tray.AlertSettings()
    assert settings.toggle("free") is False
    assert settings.is_enabled("free") is False
    assert settings.toggle("free") is True


def test_toggle_writes_through_to_the_store():
    written = []
    settings = tray.AlertSettings(store=written.append)
    settings.toggle("conflict")
    assert written and written[-1]["conflict"] is False
    assert written[-1]["free"] is True              # অন্যটি অক্ষত


def test_load_only_accepts_known_kinds():
    settings = tray.AlertSettings()
    settings.load({"free": False, "limits": True})
    assert settings.is_enabled("free") is False
    assert "limits" not in settings.as_dict()       # usage ফিচার কাটা — ফিরে আসবে না


def test_settings_survive_a_restart(tmp_path):
    # gate: বন্ধ করা অ্যালার্ট রিস্টার্টের পরেও বন্ধ থাকে
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"me": "samee", "supabase_url": "u",
                                  "supabase_key": "k"}) + "\n", encoding="utf-8")
    settings = tray.AlertSettings(store=lambda values: userconfig.save_alerts(values, target))
    settings.toggle("free")

    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["alerts"] == {"free": False, "conflict": True}
    assert saved["me"] == "samee" and saved["supabase_key"] == "k"   # বাকি চাবি অক্ষত

    restarted = tray.AlertSettings()
    restarted.load(dict(userconfig.load(path=target, env=tmp_path / "none").alerts))
    assert restarted.is_enabled("free") is False
    assert restarted.is_enabled("conflict") is True


def test_save_alerts_creates_the_file_when_missing(tmp_path):
    target = tmp_path / "sub" / "config.json"
    userconfig.save_alerts({"free": False, "conflict": True}, target)
    assert json.loads(target.read_text(encoding="utf-8"))["alerts"]["free"] is False
    assert not list(target.parent.glob("*.tmp"))     # temp ফাইল পড়ে থাকে না
