import threading
from dataclasses import dataclass, replace
from datetime import datetime

import clock
import config

# UsageView — DROPPED 2026-10-20 (usage ফিচার বাদ, tracker Decisions)। techspec §7-এ তালিকায় আছে,
# কিন্তু এখানে বানানো হয়নি; usage ফিরলে §7-এর কমেন্ট করা শেপ থেকে যোগ করতে হবে।


@dataclass(frozen=True)
class PersonView:
    # কী করছে: একজনের অবস্থা — পরিবর্তন-অযোগ্য (frozen) ছবি, রেন্ডার কোড এটিই পড়ে
    # কেন লাগছে: frozen হলে রেন্ডারের মাঝপথে মান বদলাতে পারে না, তাই এক ফ্রেম সবসময় সঙ্গতিপূর্ণ
    # real world-এ এটা কোথায় দেখা যায়: UI-তে immutable view model (React props-এর মতো)
    user_id: str
    name: str
    working: bool
    since: datetime | None       # চলতি কাজের সেশন কখন শুরু (None = কাজ করছে না)
    today_seconds: int           # আজকের মোট সময় (চলতি সেশনসহ)
    wants_next: bool             # dibs ডেকেছে কিনা (Phase 14)
    online: bool                 # heartbeat তাজা কিনা (নিজের জন্য সবসময় True)


@dataclass(frozen=True)
class StateSnapshot:
    # কী করছে: এক ফ্রেমের পুরো অবস্থা — আমি, সঙ্গী, সংযোগ ও সময়
    # কেন লাগছে: রেন্ডার লুপ প্রতি ফ্রেমে একবার এটি নেয়; লক ধরে রাখতে হয় না (techspec §7)
    # real world-এ এটা কোথায় দেখা যায়: গেম/UI-তে "frame snapshot" — আঁকার সময় state ফ্রিজ করা
    me: PersonView
    peer: PersonView
    connected: bool              # Supabase-এ পৌঁছানো যাচ্ছে কিনা (Phase 11; এখন সবসময় False)
    now: datetime


_NAMES = {"samee": "Samee", "rifat": "Rifat"}


class AppState:
    def __init__(self, me_id, peer_id, now=None):
        # কী করছে: অ্যাপের একমাত্র লেখার-যোগ্য state বানায় — একটি lock-এর পেছনে সব মান
        # কেন লাগছে: listener থ্রেড, main থ্রেড ও (পরে) sync থ্রেড একই state পড়ে/লেখে
        # real world-এ এটা কোথায় দেখা যায়: সার্ভারে shared mutable state একটি mutex-এর আড়ালে
        self._lock = threading.Lock()
        self._me_id = me_id
        self._peer_id = peer_id
        self._working = False
        self._since = None            # epoch সেকেন্ড বা None (ভিউতে datetime হয়ে যায়)
        self._today_seconds = 0.0     # শেষ হওয়া সেশনগুলোর যোগফল (চলতি সেশন এতে নেই)
        self._wants_next = False
        self._wants_next_at = None    # dibs কখন ডেকেছি (epoch) — মেয়াদ গোনার জন্য
        self._day = clock.dhaka_today(now)   # today_seconds কোন Dhaka দিনের, তা মনে রাখি
        self._connected = False
        # সঙ্গীর অবস্থা Phase 11-এর sync থ্রেড ভরবে; এখন প্লেসহোল্ডার (ঘুমন্ত, অফলাইন)
        self._peer = PersonView(
            user_id=peer_id, name=_NAMES.get(peer_id, peer_id), working=False,
            since=None, today_seconds=0, wants_next=False, online=False,
        )

    # ---- লেখা (main থ্রেড) ----

    def set_working(self, working, now):
        # কী করছে: নিজের working বদলায়; চালু হলে since=now, বন্ধ হলে চলতি সেশনের সময় জমা করে।
        #           বদল হলে True দেয় (তখনই push/alert দরকার)
        # কেন লাগছে: ডিটেকশন প্রতি সেকেন্ডে একই মান দিতে পারে; শুধু প্রকৃত বদলেই since/সময় নড়ে
        # real world-এ এটা কোথায় দেখা যায়: edge-triggered state machine — level নয়, পরিবর্তনে কাজ
        with self._lock:
            if working == self._working:
                return False
            if working:
                self._since = now
                self._wants_next = False      # কাজ শুরু করলে নিজের dibs আপনিই বাতিল (techspec §9)
                self._wants_next_at = None
            elif self._since is not None:
                self._today_seconds += max(0.0, now - self._since)
                self._since = None
            self._working = working
            return True

    def set_dibs(self, wants, now):
        # কী করছে: নিজের "পরেরবার আমি" (dibs) চালু/বাতিল করে; বদল হলে True দেয়
        # কেন লাগছে: সঙ্গী কাজ করার সময় তাকে না থামিয়ে জানানো যে আমি পরে চাই (appflow §8)
        # real world-এ এটা কোথায় দেখা যায়: কিউতে নাম লেখানো / "notify me when free"
        with self._lock:
            if wants == self._wants_next:
                return False
            self._wants_next = wants
            self._wants_next_at = now if wants else None
            return True

    def expire_dibs(self, now):
        # কী করছে: DIBS_EXPIRE পেরিয়ে গেলে নিজের dibs বাতিল করে (বাতিল হলে True)
        # কেন লাগছে: ভুলে ডেকে রাখা dibs সারাদিন ঝুলে থাকলে সঙ্গী অযথা চাপে থাকত (techspec §9)
        # real world-এ এটা কোথায় দেখা যায়: TTL দিয়ে আপনা-আপনি ছেড়ে যাওয়া রিজার্ভেশন
        with self._lock:
            if not self._wants_next or self._wants_next_at is None:
                return False
            if now - self._wants_next_at < config.DIBS_EXPIRE:
                return False
            self._wants_next = False
            self._wants_next_at = None
            return True

    def roll_day(self, now):
        # কী করছে: Dhaka দিন বদলালে আজকের কাউন্টার ০ করে; চলমান সেশন হলে এখন থেকে নতুন গোনা শুরু
        # কেন লাগছে: মধ্যরাতে "আজ" নতুন হয়; ইতিহাস রাখি না, তাই আগের সময় ফেলে দিই (appflow §12)
        # real world-এ এটা কোথায় দেখা যায়: দৈনিক কাউন্টার/কোটা মধ্যরাতে রিসেট
        today = clock.dhaka_today(now)
        with self._lock:
            if today == self._day:
                return False
            self._day = today
            self._today_seconds = 0.0
            if self._since is not None:
                self._since = now
            return True

    def adopt_today(self, seconds, now):
        # কী করছে: সার্ভারে রাখা আজকের সময় ফিরিয়ে নেয় (অ্যাপ চালু হওয়ার পরে একবার)
        # কেন লাগছে: অ্যাপ বন্ধ-চালু করলে আজকের কাউন্টার ০ থেকে শুরু হলে চলবে না (techspec §6.4);
        #           চলতি সেশন থাকলে তার হিসাব এখন থেকে আবার শুরু হয়, যাতে দুবার না গোনা হয়
        # real world-এ এটা কোথায় দেখা যায়: ক্লায়েন্ট রিস্টার্টে সার্ভার থেকে কাউন্টার resume করা
        with self._lock:
            self._today_seconds = float(max(0, seconds))
            if self._since is not None:
                self._since = now

    def set_connected(self, connected):
        # কী করছে: Supabase-এ পৌঁছানো যাচ্ছে কিনা তা রাখে (Phase 11-এর sync থ্রেড ডাকবে)
        # কেন লাগছে: প্যানেলের নিচে "offline" লাইন এই মান দেখে দেখানো হবে
        # real world-এ এটা কোথায় দেখা যায়: অ্যাপে connectivity indicator-এর state
        with self._lock:
            self._connected = connected

    def set_peer(self, **fields):
        # কী করছে: সঙ্গীর ভিউ-এর দেওয়া ক্ষেত্রগুলো বদলায় (বাকিটা অপরিবর্তিত)
        # কেন লাগছে: Phase 11-এ পোলিং থেকে আসা মান এখানে বসবে; এখন শুধু টেস্ট/প্লেসহোল্ডার
        # real world-এ এটা কোথায় দেখা যায়: immutable view-এর "copy with changes" (dataclasses.replace)
        with self._lock:
            self._peer = replace(self._peer, **fields)

    # ---- পড়া (যে কোনো থ্রেড) ----

    def snapshot(self, now=None):
        # কী করছে: এই মুহূর্তের একটি frozen StateSnapshot বানিয়ে দেয় (চলতি সেশনের সময় যোগ করে)
        # কেন লাগছে: রেন্ডার ও alerts লক ছাড়া কাজ করে; প্রতি ফ্রেমে একবার ডাকা হয় (techspec §7)
        # real world-এ এটা কোথায় দেখা যায়: lock ধরে দ্রুত কপি, তারপর লক ছেড়ে কাজ (copy-out pattern)
        if now is None:
            now = clock.now()
        with self._lock:
            total = self._today_seconds
            if self._since is not None:
                total += max(0.0, now - self._since)
            me = PersonView(
                user_id=self._me_id,
                name=_NAMES.get(self._me_id, self._me_id),
                working=self._working,
                since=clock.to_dt(self._since),
                today_seconds=int(total),
                wants_next=self._wants_next,
                online=True,                      # নিজের heartbeat সবসময় তাজা
            )
            return StateSnapshot(me=me, peer=self._peer,
                                 connected=self._connected, now=clock.to_dt(now))

    def dibs_since(self):
        # কী করছে: নিজের dibs কখন ডাকা হয়েছিল তা (epoch) দেয় — না থাকলে None
        # কেন লাগছে: সার্ভারে wants_next_at পাঠাতে লাগে; ভিউতে রাখার দরকার নেই (UI দেখায় না)
        # real world-এ এটা কোথায় দেখা যায়: ভেতরের টাইমস্ট্যাম্প, যা শুধু sync-এর কাজে লাগে
        with self._lock:
            return self._wants_next_at
