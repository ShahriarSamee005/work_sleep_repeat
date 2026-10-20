import time
from datetime import datetime, timedelta, timezone

import config

# Dhaka = UTC+6, সারা বছর এক (DST নেই) — তাই zoneinfo/tzdata ছাড়াই ফিক্সড offset যথেষ্ট
DHAKA = timezone(timedelta(seconds=config.TZ_OFFSET_SECONDS), config.TIMEZONE)


def now():
    # কী করছে: বর্তমান সময় epoch সেকেন্ডে (float) দেয়
    # কেন লাগছে: অ্যাপের সব হিসাব (idle timeout, since, today_seconds) epoch সেকেন্ডে চলে
    # real world-এ এটা কোথায় দেখা যায়: সার্ভার/ক্লায়েন্টে unix timestamp — টাইমজোন-নিরপেক্ষ একক
    return time.time()


def to_dt(ts):
    # কী করছে: epoch সেকেন্ডকে টাইমজোন-সচেতন UTC datetime-এ বদলায় (None দিলে None)
    # কেন লাগছে: state-এর ভিউ (techspec §7) datetime চায়, কিন্তু ভেতরের হিসাব সংখ্যায় হয়
    # real world-এ এটা কোথায় দেখা যায়: API boundary-তে epoch ↔ ISO টাইমস্ট্যাম্প রূপান্তর
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def dhaka_today(ts=None):
    # কী করছে: দেওয়া (বা এখনকার) সময়ে Dhaka-র তারিখ (date) দেয়
    # কেন লাগছে: "আজকের কাজের সময়" Dhaka দিনে গোনা হয়; দিন বদলালে কাউন্টার ০ হয় (appflow §12)
    # real world-এ এটা কোথায় দেখা যায়: রিপোর্টিং অ্যাপে "business day" নির্দিষ্ট টাইমজোনে ধরা
    if ts is None:
        ts = now()
    return datetime.fromtimestamp(ts, tz=DHAKA).date()


def parse_ts(value):
    # কী করছে: unix সেকেন্ড (সংখ্যা/স্ট্রিং) বা ISO 8601 স্ট্রিং — দুটোকেই epoch সেকেন্ডে বদলায়;
    #           বুঝতে না পারলে None দেয়
    # কেন লাগছে: হুক পেলোড ও Supabase দুই ফরম্যাটেই সময় দিতে পারে; কোনটা আসবে আগে জানা নেই
    # real world-এ এটা কোথায় দেখা যায়: বাইরের ইনপুট পার্স করা — কঠোর না হয়ে সহনশীল (tolerant reader)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)                       # "1700000000" / "1700000000.5"
    except ValueError:
        pass
    iso = text[:-1] + "+00:00" if text.endswith("Z") else text   # "...Z" → ISO-এর offset রূপ
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)   # offset না থাকলে UTC ধরি
    return parsed.timestamp()


def fmt_duration(seconds):
    # কী করছে: সেকেন্ডকে "Xh YYm" রূপে দেয় (মিনিট ২ অঙ্কে); ০ বা কম হলে "—"
    # কেন লাগছে: ট্রে টুলটিপ/টোস্ট/লগে সময় পড়ার মতো করে দেখাতে
    # real world-এ এটা কোথায় দেখা যায়: টাইম-ট্র্যাকারে মানবিক সময় ফরম্যাট
    # নোট: প্যানেলের format_time একই রূপ দেয় — render মডিউল layer 1 import করতে পারে না (techspec §3),
    #      তাই দুই জায়গায় আছে; রূপ বদলালে দুটোই বদলাতে হবে
    s = int(seconds)
    if s <= 0:
        return "—"
    return "%dh %02dm" % (s // 3600, (s % 3600) // 60)
