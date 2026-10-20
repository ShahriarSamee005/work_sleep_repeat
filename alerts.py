from dataclasses import dataclass

import config

FREE = "free"            # সঙ্গী কাজ শেষ করেছে — Claude এখন ফাঁকা
CONFLICT = "conflict"     # দুজনেই একসাথে চালাচ্ছি
KINDS = (FREE, CONFLICT)
# dibs ও "your turn" টোস্ট Phase 14-এ যোগ হবে; limit টোস্ট বাদ (usage ফিচার কাটা)


@dataclass(frozen=True)
class Toast:
    # কী করছে: একটি টোস্টের বিষয়বস্তু — কোন ধরনের, শিরোনাম ও এক লাইন বডি (design §5)
    # কেন লাগছে: alerts শুধু "কী বলা উচিত" ঠিক করে; কে দেখাবে (tray) তা আলাদা স্তর
    # real world-এ এটা কোথায় দেখা যায়: notification payload — বানানো ও দেখানো আলাদা রাখা
    kind: str
    title: str
    body: str


class Memory:
    def __init__(self):
        # কী করছে: কোন টোস্ট কখন পাঠানো হয়েছে তা মনে রাখে, যাতে একই ঘটনায় বারবার না বাজে
        # কেন লাগছে: দ্বন্দ্ব চলতেই থাকে — প্রতি সেকেন্ডে টোস্ট দিলে বিরক্তিকর (techspec §9: dedupe)
        # real world-এ এটা কোথায় দেখা যায়: alerting সিস্টেমে "fire once per incident"
        self.conflict_since = None    # দুজনে একসাথে কাজ শুরুর সময় (না থাকলে None)
        self.conflict_sent = False    # এই overlap-এ টোস্ট দেওয়া হয়ে গেছে?


def check(prev, cur, memory):
    # কী করছে: আগের ও এখনকার snapshot মিলিয়ে কোন টোস্ট বাজানো উচিত তার তালিকা দেয়
    # কেন লাগছে: এটিই alerts-এর পুরো নিয়ম — শুদ্ধ ফাংশন, তাই স্ক্রিপ্ট করা snapshot দিয়ে টেস্ট করা যায়
    # real world-এ এটা কোথায় দেখা যায়: state diff → events (reducer-এর মতো), I/O ছাড়া
    # prev None হলে (প্রথম ফ্রেম) কিছুই বাজে না — অ্যাপ চালু হওয়াই কোনো "ঘটনা" নয়
    out = []
    if prev is None:
        _track_conflict(cur, memory)
        return out

    # "It's free": সঙ্গীর working সত্য → মিথ্যা (techspec §9)। আমি নিজে কাজ করতে থাকলে চুপ থাকি —
    # তখন খবরটা কাজে লাগে না, আর "দুজনেই" অবস্থার টোস্ট আলাদা করে আছে।
    if prev.peer.working and not cur.peer.working and not cur.me.working:
        out.append(Toast(FREE, "Claude is free", "%s just finished." % cur.peer.name))

    # দ্বন্দ্ব: দুজনেই কাজ করছি এবং তা ৩০ সেকেন্ডের বেশি টিকেছে — overlap-এ একবারই (appflow §9)
    if _track_conflict(cur, memory):
        out.append(Toast(CONFLICT, "You're both on it",
                         "%s is also using Claude right now." % cur.peer.name))
    return out


def _track_conflict(cur, memory):
    # কী করছে: দ্বন্দ্বের সময় গোনে; CONFLICT_AFTER পেরোলে ও এখনো না পাঠানো হলে True দেয়
    # কেন লাগছে: ক্ষণিকের overlap-এ (একজন থামছে, একজন শুরু করছে) টোস্ট দেওয়া অর্থহীন
    # real world-এ এটা কোথায় দেখা যায়: মনিটরিং-এ "for: 30s" শর্ত — স্থায়ী হলে তবেই অ্যালার্ট
    both = cur.me.working and cur.peer.working
    if not both:
        memory.conflict_since = None
        memory.conflict_sent = False
        return False
    now = cur.now.timestamp()
    if memory.conflict_since is None:
        memory.conflict_since = now
    if memory.conflict_sent or now - memory.conflict_since < config.CONFLICT_AFTER:
        return False
    memory.conflict_sent = True
    return True
