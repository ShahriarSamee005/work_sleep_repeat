import threading

import requests

import clock
import config

STATUS = "status"        # outbox-এর একমাত্র kind এখন (usage বাদ, techspec §6.4)


class Outbox:
    def __init__(self):
        # কী করছে: পাঠানোর অপেক্ষায় থাকা পেলোড রাখে — প্রতি kind-এ শুধু সর্বশেষটি
        # কেন লাগছে: নেট না থাকলে ১০ বার status বদলালেও সর্বশেষ অবস্থাটিই সত্য; পুরনোগুলো পাঠানো
        #           অর্থহীন ও ক্ষতিকর (পুরনো মান সার্ভারে বসে যেত)
        # real world-এ এটা কোথায় দেখা যায়: "latest-wins" / coalescing queue (UI event dedupe-ও তাই)
        self._lock = threading.Lock()
        self._items = {}

    def put(self, kind, payload):
        with self._lock:
            self._items[kind] = payload

    def peek(self):
        # কী করছে: অপেক্ষমাণ আইটেমগুলোর কপি দেয় (তালিকা থেকে সরায় না)
        # কেন লাগছে: পাঠানো সফল হলেই সরাব — নাহলে আইটেম হারিয়ে যেত (appflow §10: outbox রাখি)
        # real world-এ এটা কোথায় দেখা যায়: at-least-once পাঠানোয় peek → send → ack → delete
        with self._lock:
            return dict(self._items)

    def done(self, kind, payload):
        # কী করছে: সফলভাবে পাঠানো আইটেম সরায় — কিন্তু মাঝপথে নতুন মান এলে সেটি রেখে দেয়
        # কেন লাগছে: পাঠানোর সময় main থ্রেড নতুন status দিতে পারে; সেটি হারালে অবস্থা পুরনো থাকত
        # real world-এ এটা কোথায় দেখা যায়: compare-and-delete — যা পাঠিয়েছি ঠিক তাই মুছি
        with self._lock:
            if self._items.get(kind) is payload:
                del self._items[kind]

    def pending(self):
        with self._lock:
            return len(self._items)


def backoff_delay(failures):
    # কী করছে: পরপর কতবার ব্যর্থ হয়েছে তা দেখে পরের চেষ্টার আগে কত সেকেন্ড অপেক্ষা করব তা দেয়
    # কেন লাগছে: নেট/সার্ভার ডাউন থাকলে প্রতি ২ সেকেন্ডে পেটানো অর্থহীন; ধীরে ধীরে ফাঁক বাড়াই
    # real world-এ এটা কোথায় দেখা যায়: exponential backoff (ক্যাপ সহ) — সব নেটওয়ার্ক ক্লায়েন্টে
    if failures <= 0:
        return config.POLL_INTERVAL
    steps = config.BACKOFF_SECONDS
    return float(steps[min(failures, len(steps)) - 1])


class Client:
    def __init__(self, url, key, timeout=None, session=None):
        # কী করছে: Supabase-এর দুটি RPC ডাকার পাতলা মোড়ক (requests.Session পুনর্ব্যবহার করে)
        # কেন লাগছে: টেবিলে সরাসরি হাত দিই না — সব কল wsr_update_status / wsr_get_state দিয়ে (§6.3)
        # real world-এ এটা কোথায় দেখা যায়: ছোট API ক্লায়েন্ট ক্লাস — টেস্টে নকল করা সহজ
        self.base = url.rstrip("/") + "/rest/v1/rpc/"
        self.timeout = config.SYNC_TIMEOUT if timeout is None else timeout
        self.session = session or requests.Session()
        self.session.headers.update({
            "apikey": key,
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        })

    def _call(self, fn, payload):
        response = self.session.post(self.base + fn, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json() if response.content else None

    def update_status(self, user, fields):
        return self._call("wsr_update_status", {"p_user": user, "p_fields": fields})

    def get_state(self):
        return self._call("wsr_get_state", {})


class Sync:
    def __init__(self, app_state, client, me, peer, now_fn=None):
        # কী করছে: সিংক ইঞ্জিন — আউটবক্স পাঠায়, heartbeat দেয়, wsr_get_state পড়ে AppState-এ বসায়
        # কেন লাগছে: দুই পিসি একে অপরকে দেখে এভাবেই; নেট না থাকলেও অ্যাপ যেন না আটকায় (§6.4)
        # real world-এ এটা কোথায় দেখা যায়: ব্যাকগ্রাউন্ড sync এজেন্ট — push + poll + backoff
        # নোট: এখানে OpenGL/উইন্ডোর কিছু নেই; শুধু AppState-এ লেখে (লক তার ভেতরেই)
        self.state = app_state
        self.client = client
        self.me = me
        self.peer = peer
        self.now_fn = now_fn or clock.now
        self.outbox = Outbox()
        self.failures = 0
        self.connected = False
        self.resumed = False          # নিজের row একবার পড়ে today_seconds ফিরিয়ে নেওয়া হয়েছে?
        self.last_send = 0.0          # সর্বশেষ কিছু পাঠানোর সময় (heartbeat হিসাবের জন্য)
        self.last_loop = None         # সর্বশেষ চক্রের সময় (time jump ধরতে)
        self.time_jumps = 0
        self._stop = threading.Event()
        self._thread = None

    # ---- main থ্রেড থেকে ডাকা ----

    def queue_status(self, fields):
        # কী করছে: নিজের status আউটবক্সে রাখে (latest-wins), পরের চক্রে যাবে
        # কেন লাগছে: main থ্রেড কখনো নেটওয়ার্কে অপেক্ষা করবে না — রেন্ডার আটকে যেত
        # real world-এ এটা কোথায় দেখা যায়: UI থ্রেড → queue → worker থ্রেড
        self.outbox.put(STATUS, dict(fields))

    def start(self):
        self._thread = threading.Thread(target=self._run, name="sync", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    # ---- থ্রেডের ভেতর ----

    def _run(self):
        while not self._stop.is_set():
            ok = self.step(self.now_fn())
            delay = config.POLL_INTERVAL if ok else backoff_delay(self.failures)
            self._stop.wait(delay)

    def step(self, now):
        # কী করছে: এক চক্র — time jump দেখা → আউটবক্স পাঠানো → heartbeat → state পড়া → AppState-এ বসানো।
        #           সফল হলে True, কোনো কল ব্যর্থ হলে False (তখন কলার backoff করে)
        # কেন লাগছে: পুরো সিংক একটি ফাংশনে রাখলে টেস্টে নকল client দিয়ে পুরো আচরণ পরীক্ষা করা যায়
        # real world-এ এটা কোথায় দেখা যায়: থ্রেড লুপ আর এক ধাপের লজিক আলাদা রাখা (testable step)
        jumped = self._check_time_jump(now)
        try:
            self._flush(now, force_push=jumped)
            payload = self.client.get_state()
        except Exception:                      # requests-এর সব ব্যর্থতা এক জায়গায় (§12)
            self.failures += 1
            if self.failures >= config.FAILURES_BEFORE_OFFLINE:
                self.connected = False         # একবার ব্যর্থতায় নয় — দুইবারে (appflow §10)
                self.state.set_connected(False)
            return False
        self.apply_state(payload, now)
        self.failures = 0
        self.connected = True
        self.state.set_connected(True)
        return True

    def _check_time_jump(self, now):
        # কী করছে: গত চক্রের পর অস্বাভাবিক বড় ফাঁক হলে (পিসি ঘুমিয়েছিল) True দেয়
        # কেন লাগছে: ঘুম থেকে উঠে অপেক্ষা না করে সাথে সাথে নিজের অবস্থা আবার পুশ করা দরকার (appflow §11)
        # real world-এ এটা কোথায় দেখা যায়: sleep/resume টের পেয়ে reconnect করা ক্লায়েন্ট
        previous, self.last_loop = self.last_loop, now
        if previous is None:
            return False
        if now - previous > config.TIME_JUMP_SECONDS:
            self.time_jumps += 1
            self.failures = 0                  # নতুন করে শুরু, backoff-এ বসে থাকা নয়
            return True
        return False

    def _flush(self, now, force_push=False):
        # কী করছে: আউটবক্সের আইটেম পাঠায়; কিছু না থাকলে ও heartbeat-এর সময় হলে খালি update পাঠায়
        # কেন লাগছে: খালি wsr_update_status সার্ভারে last_heartbeat বসায় — ওটাই "আমি অনলাইন" সংকেত
        # real world-এ এটা কোথায় দেখা যায়: keep-alive/heartbeat সহ outbox flush
        items = self.outbox.peek()
        if force_push and STATUS not in items:
            snap = self.state.snapshot(now)
            items = {STATUS: status_fields(snap, now, self.state.dibs_since())}   # ঘুম থেকে উঠে পুরো অবস্থা
            self.outbox.put(STATUS, items[STATUS])
        sent = False
        for kind, payload in items.items():
            self.client.update_status(self.me, payload)
            self.outbox.done(kind, payload)
            sent = True
        if not sent and now - self.last_send >= config.HEARTBEAT_INTERVAL:
            self.client.update_status(self.me, {})       # শুধু heartbeat
            sent = True
        if sent:
            self.last_send = now

    def apply_state(self, payload, now):
        # কী করছে: wsr_get_state-এর JSON থেকে সঙ্গীর অবস্থা ও (একবার) নিজের today_seconds নিয়ে
        #           AppState-এ বসায়; সার্ভারের now দিয়ে সঙ্গী অনলাইন কিনা ঠিক করে
        # কেন লাগছে: দুই পিসির ঘড়ি আলাদা হতে পারে — তাই heartbeat-এর বয়স সার্ভার সময়ে মাপি (§6.4)
        # real world-এ এটা কোথায় দেখা যায়: সার্ভার-সময় ভিত্তিক presence (ক্লায়েন্ট ঘড়িতে ভরসা নেই)
        if not isinstance(payload, dict):
            return
        server_now = clock.parse_ts(payload.get("server_now")) or now
        rows = payload.get("status") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            user = row.get("user_id")
            if user == self.peer:
                beat = clock.parse_ts(row.get("last_heartbeat"))
                online = beat is not None and (server_now - beat) <= config.PEER_OFFLINE_AFTER
                self.state.set_peer(
                    name=row.get("display_name") or self.peer,
                    working=bool(row.get("working")),
                    since=clock.to_dt(clock.parse_ts(row.get("since"))),
                    today_seconds=int(row.get("today_seconds") or 0),
                    wants_next=bool(row.get("wants_next")),
                    online=online,
                )
            elif user == self.me and not self.resumed:
                self.resumed = True
                # আজকের দিনেরই হিসাব হলে ফিরিয়ে নিই (অ্যাপ রিস্টার্টে সময় হারায় না, §6.4)
                if row.get("today_date") == clock.dhaka_today(now).isoformat():
                    self.state.adopt_today(int(row.get("today_seconds") or 0), now)


def status_fields(snap, now, dibs_since=None):
    # কী করছে: snapshot থেকে wsr_update_status-এ পাঠানোর ফিল্ডগুলো বানায়
    # কেন লাগছে: এক জায়গায় রাখলে পুশের আকার সবসময় এক থাকে (main ও sync দুজনেই এটি ব্যবহার করে)
    # real world-এ এটা কোথায় দেখা যায়: API payload builder — সার্ভারের স্কিমার সাথে এক জায়গায় বাঁধা
    # dibs_since: AppState.dibs_since() — wants_next_at সার্ভারে পাঠাতে (ভিউতে এটি নেই)
    return {
        "working": snap.me.working,
        "since": snap.me.since.isoformat() if snap.me.since else None,
        "today_seconds": int(snap.me.today_seconds),
        "today_date": clock.dhaka_today(now).isoformat(),
        "wants_next": snap.me.wants_next,
        "wants_next_at": clock.to_dt(dibs_since).isoformat() if dibs_since else None,
        "app_version": config.APP_VERSION,
    }
