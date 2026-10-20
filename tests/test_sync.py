"""tests/test_sync.py — আউটবক্স, backoff, time jump ও wsr_get_state প্রয়োগ (techspec §6.4)।

চালানো: pytest tests/test_sync.py
কোনো নেটওয়ার্ক নেই: client-এর জায়গায় নকল অবজেক্ট, সময় হাতে দেওয়া।
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clock
import config
import state
import sync

T0 = 1_700_000_000.0            # 2023-11-14 22:13:20 UTC → Dhaka-তে 15 Nov
SERVER_NOW = "2023-11-14T22:13:20+00:00"


class FakeClient:
    # কী করছে: Supabase ক্লায়েন্টের জায়গায় বসে — কী পাঠানো হলো তা মনে রাখে, চাইলে ব্যর্থ হয়
    # কেন লাগছে: টেস্টে আসল নেটওয়ার্ক ছোঁয়া যাবে না (ধীর, অনির্ভরযোগ্য, বাইরের অবস্থার উপর নির্ভর)
    # real world-এ এটা কোথায় দেখা যায়: test double / fake — বাইরের সীমানা নকল করা
    def __init__(self, payload=None, fail=False):
        self.updates = []
        self.state_calls = 0
        self.payload = payload
        self.fail = fail

    def update_status(self, user, fields):
        if self.fail:
            raise OSError("no network")
        self.updates.append((user, fields))

    def get_state(self):
        if self.fail:
            raise OSError("no network")
        self.state_calls += 1
        return self.payload


def row(user, **over):
    base = {
        "user_id": user, "display_name": user.title(), "working": False,
        "since": None, "today_seconds": 0, "today_date": None,
        "wants_next": False, "wants_next_at": None,
        "last_heartbeat": SERVER_NOW, "app_version": "2.0-phase11",
    }
    base.update(over)
    return base


def payload(*rows, server_now=SERVER_NOW):
    return {"server_now": server_now, "status": list(rows)}


def make(me="samee", peer="rifat", client=None):
    app_state = state.AppState(me, peer, T0)
    engine = sync.Sync(app_state, client or FakeClient(payload()), me=me, peer=peer)
    return app_state, engine


# ---------------- outbox ----------------

def test_outbox_keeps_only_the_latest_per_kind():
    box = sync.Outbox()
    box.put(sync.STATUS, {"working": True})
    box.put(sync.STATUS, {"working": False})
    assert box.pending() == 1
    assert box.peek()[sync.STATUS] == {"working": False}


def test_outbox_done_keeps_a_newer_item():
    box = sync.Outbox()
    first = {"working": True}
    box.put(sync.STATUS, first)
    newer = {"working": False}
    box.put(sync.STATUS, newer)       # পাঠানোর মাঝপথে নতুন অবস্থা এলো
    box.done(sync.STATUS, first)      # পুরনোটি পাঠানো শেষ
    assert box.peek()[sync.STATUS] is newer      # নতুনটি হারায়নি


def test_outbox_done_removes_what_was_sent():
    box = sync.Outbox()
    item = {"working": True}
    box.put(sync.STATUS, item)
    box.done(sync.STATUS, item)
    assert box.pending() == 0


# ---------------- backoff ----------------

def test_backoff_sequence_matches_spec():
    # techspec §6.4: 2 → 4 → 8 → 16 → 30, তারপর ৩০-এই আটকে থাকে
    assert [sync.backoff_delay(n) for n in range(1, 8)] == [2, 4, 8, 16, 30, 30, 30]


def test_no_failures_means_normal_poll_interval():
    assert sync.backoff_delay(0) == config.POLL_INTERVAL


# ---------------- step: পাঠানো ও heartbeat ----------------

def test_step_sends_queued_status_then_clears_it():
    client = FakeClient(payload(row("samee"), row("rifat")))
    app_state, engine = make(client=client)
    engine.queue_status({"working": True})
    assert engine.step(T0) is True
    assert client.updates == [("samee", {"working": True})]
    assert engine.outbox.pending() == 0
    assert engine.step(T0 + config.POLL_INTERVAL) is True
    assert len(client.updates) == 1              # দ্বিতীয় চক্রে পাঠানোর কিছু নেই


def test_heartbeat_goes_out_when_nothing_else_does():
    client = FakeClient(payload(row("samee"), row("rifat")))
    _state, engine = make(client=client)
    engine.step(T0)
    assert client.updates == [("samee", {})]      # প্রথম চক্রেই "আমি অনলাইন" জানাই (খালি update)
    engine.step(T0 + 1)
    assert len(client.updates) == 1               # এরপর HEARTBEAT_INTERVAL না পেরোলে আর নয়
    engine.step(T0 + config.HEARTBEAT_INTERVAL)
    assert len(client.updates) == 2


def test_a_real_push_counts_as_the_heartbeat():
    client = FakeClient(payload(row("samee"), row("rifat")))
    _state, engine = make(client=client)
    engine.queue_status({"working": True})
    engine.step(T0)
    engine.step(T0 + config.HEARTBEAT_INTERVAL - 1)
    assert len(client.updates) == 1              # status পাঠানোই heartbeat হিসেবে গোনা হয়েছে


# ---------------- failures / offline ----------------

def test_two_failures_mark_us_offline():
    client = FakeClient(payload(), fail=True)
    app_state, engine = make(client=client)
    assert engine.step(T0) is False
    assert app_state.snapshot(T0).connected is False   # শুরুতেই False, কিন্তু এখনো "ঘোষিত" নয়
    assert engine.failures == 1
    assert engine.step(T0 + 2) is False
    assert engine.failures == 2
    assert engine.connected is False


def test_success_clears_failures_and_marks_connected():
    client = FakeClient(payload(row("samee"), row("rifat")), fail=True)
    app_state, engine = make(client=client)
    engine.step(T0)
    engine.step(T0 + 2)
    client.fail = False
    assert engine.step(T0 + 6) is True
    assert engine.failures == 0
    assert app_state.snapshot(T0 + 6).connected is True


# ---------------- time jump ----------------

def test_time_jump_forces_a_full_push():
    client = FakeClient(payload(row("samee"), row("rifat")))
    app_state, engine = make(client=client)
    app_state.set_working(True, T0)
    engine.step(T0)
    client.updates.clear()
    engine.step(T0 + config.TIME_JUMP_SECONDS + 5)       # পিসি ঘুমিয়ে উঠল
    assert engine.time_jumps == 1
    assert len(client.updates) == 1
    user, fields = client.updates[0]
    assert user == "samee" and fields["working"] is True  # পুরো অবস্থা আবার পাঠানো হলো


def test_small_gaps_are_not_time_jumps():
    client = FakeClient(payload(row("samee"), row("rifat")))
    _state, engine = make(client=client)
    engine.step(T0)
    engine.step(T0 + config.TIME_JUMP_SECONDS - 1)
    assert engine.time_jumps == 0


def test_time_jump_clears_backoff():
    client = FakeClient(payload(), fail=True)
    _state, engine = make(client=client)
    engine.step(T0)
    engine.step(T0 + 2)
    assert engine.failures == 2
    client.fail = False
    engine.step(T0 + config.TIME_JUMP_SECONDS + 5)
    assert engine.failures == 0                          # সাথে সাথে আবার চেষ্টা, বসে থাকা নয়


# ---------------- apply_state ----------------

def test_apply_state_fills_the_peer():
    app_state, engine = make()
    engine.apply_state(payload(
        row("samee"),
        row("rifat", working=True, since="2023-11-14T21:00:00+00:00",
            today_seconds=3600, display_name="Rifat"),
    ), T0)
    peer = app_state.snapshot(T0).peer
    assert peer.name == "Rifat" and peer.working is True
    assert peer.today_seconds == 3600 and peer.online is True
    assert peer.since is not None and peer.since.hour == 21


def test_peer_is_offline_when_the_heartbeat_is_old():
    app_state, engine = make()
    stale = "2023-11-14T22:11:00+00:00"          # server_now থেকে ১৪০ সেকেন্ড আগে
    engine.apply_state(payload(row("samee"), row("rifat", last_heartbeat=stale)), T0)
    assert app_state.snapshot(T0).peer.online is False


def test_peer_offline_uses_server_time_not_ours():
    # আমাদের ঘড়ি এক ঘণ্টা পিছিয়ে — তবু heartbeat তাজা বলেই গণ্য হবে (server_now দিয়ে মাপা)
    app_state, engine = make()
    engine.apply_state(payload(row("samee"), row("rifat")), T0 - 3600)
    assert app_state.snapshot(T0).peer.online is True


def test_missing_heartbeat_means_offline():
    app_state, engine = make()
    engine.apply_state(payload(row("samee"), row("rifat", last_heartbeat=None)), T0)
    assert app_state.snapshot(T0).peer.online is False


def test_my_today_seconds_resume_only_once_and_only_today():
    app_state, engine = make()
    today = clock.dhaka_today(T0).isoformat()
    engine.apply_state(payload(row("samee", today_seconds=1800, today_date=today),
                               row("rifat")), T0)
    assert app_state.snapshot(T0).me.today_seconds == 1800
    # পরের পোলে সার্ভারের মান আর নিজের লোকাল হিসাবের উপরে বসবে না
    engine.apply_state(payload(row("samee", today_seconds=99999, today_date=today),
                               row("rifat")), T0)
    assert app_state.snapshot(T0).me.today_seconds == 1800


def test_yesterdays_total_is_not_resumed():
    app_state, engine = make()
    engine.apply_state(payload(row("samee", today_seconds=7200, today_date="2001-01-01"),
                               row("rifat")), T0)
    assert app_state.snapshot(T0).me.today_seconds == 0


def test_apply_state_survives_junk():
    app_state, engine = make()
    engine.apply_state(None, T0)
    engine.apply_state({"status": None}, T0)
    engine.apply_state({"server_now": "nonsense", "status": ["not a dict"]}, T0)
    assert app_state.snapshot(T0).peer.online is False    # কিছুই বদলায়নি, ক্র্যাশও হয়নি


# ---------------- status_fields ----------------

def test_status_fields_shape():
    app_state, _engine = make()
    app_state.set_working(True, T0)
    fields = sync.status_fields(app_state.snapshot(T0), T0)
    assert fields["working"] is True
    assert fields["since"].startswith("2023-11-14T")
    assert fields["today_date"] == clock.dhaka_today(T0).isoformat()
    assert fields["app_version"] == config.APP_VERSION


def test_status_fields_send_null_since_when_not_working():
    app_state, _engine = make()
    fields = sync.status_fields(app_state.snapshot(T0), T0)
    assert fields["since"] is None            # RPC-তে since = null বসবে
