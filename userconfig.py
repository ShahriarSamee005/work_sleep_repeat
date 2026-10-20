import json
import os
from dataclasses import dataclass
from pathlib import Path

# Phase 11-এ শুধু পড়া হয়; লেখা (first-run dialog) Phase 15-এ আসবে।
APP_DIR_NAME = "WorkSleepRepeat"
CONFIG_NAME = "config.json"
ENV_NAME = ".env"


@dataclass(frozen=True)
class UserConfig:
    # কী করছে: অ্যাপ চালানোর জন্য দরকারি সেটিং — কে চালাচ্ছে ও Supabase-এর ঠিকানা/কী
    # কেন লাগছে: এই মানগুলো কোডে রাখা যাবে না (কী গোপন, আর দুই পিসিতে আলাদা)
    # real world-এ এটা কোথায় দেখা যায়: অ্যাপের config অবজেক্ট — ফাইল/env দুই জায়গা থেকে মেলানো
    me: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    source: str = "none"          # মান কোথা থেকে এলো (লগ/ডায়ালগে দেখাতে)

    @property
    def has_supabase(self):
        return bool(self.supabase_url and self.supabase_key)


def config_path():
    # কী করছে: %APPDATA%\WorkSleepRepeat\config.json-এর পথ দেয় (techspec §10)
    # কেন লাগছে: Phase 15-এর setup UI এখানেই লিখবে; এখন থাকলে পড়ি
    # real world-এ এটা কোথায় দেখা যায়: Windows-এ per-user অ্যাপ ডেটার স্ট্যান্ডার্ড জায়গা
    base = os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_DIR_NAME / CONFIG_NAME


def env_path():
    # কী করছে: প্রজেক্ট ফোল্ডারের .env ফাইলের পথ দেয়
    # কেন লাগছে: ডেভ রানে config.json না বানিয়েও চালানো যায় (.env.example দেখে বানানো)
    # real world-এ এটা কোথায় দেখা যায়: ডেভ মেশিনে .env, প্রোডাকশনে আসল config
    return Path(__file__).resolve().parent / ENV_NAME


def _read_json(path):
    # কী করছে: config.json পড়ে dict দেয়; না থাকলে/ভুল হলে খালি dict
    # কেন লাগছে: কনফিগ ভাঙা থাকলেও অ্যাপ অন্তত লোকাল মোডে চলতে পারবে
    # real world-এ এটা কোথায় দেখা যায়: কনফিগ পড়ায় সহনশীলতা — না থাকলে ডিফল্ট
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_env(path):
    # কী করছে: .env ফাইলের KEY=VALUE লাইনগুলো পড়ে dict দেয় (# মন্তব্য ও কোট বাদ দিয়ে)
    # কেন লাগছে: python-dotenv না থাকলেও যেন কাজ করে (প্যাকেজিং-এ এক কম নির্ভরতা)
    # real world-এ এটা কোথায় দেখা যায়: ছোট dotenv পার্সার — ১২-ফ্যাক্টর অ্যাপের env ফাইল
    out = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load(me=None, path=None, env=None):
    # কী করছে: config.json → .env → OS env, এই ক্রমে দেখে UserConfig বানায়; me দিলে সেটিই জেতে
    # কেন লাগছে: techspec §10 — "config file wins over .env, --me wins over both"
    # real world-এ এটা কোথায় দেখা যায়: স্তরে স্তরে কনফিগ (file → env → CLI), শেষেরটি সবচেয়ে জোরালো
    path = Path(path) if path is not None else config_path()
    env = Path(env) if env is not None else env_path()

    data = _read_json(path)
    who = (data.get("me") or "").strip()
    url = (data.get("supabase_url") or "").strip()
    key = (data.get("supabase_key") or "").strip()
    source = "config.json"

    if not (url and key):                      # config.json-এ জোড়া না থাকলে .env দেখি
        values = _read_env(env)
        found = ((values.get("SUPABASE_URL") or "").strip(),
                 (values.get("SUPABASE_KEY") or "").strip())
        source = ".env"
        if not all(found):                     # .env-এও না থাকলে প্রসেসের env (শেল/CI)
            found = ((os.environ.get("SUPABASE_URL") or "").strip(),
                     (os.environ.get("SUPABASE_KEY") or "").strip())
            source = "environment"
        if all(found):
            url, key = found

    if not (url and key):
        source = "none"                        # কোথাওই পাওয়া যায়নি → অ্যাপ লোকাল মোডে চলবে
    return UserConfig(me=(me or who), supabase_url=url, supabase_key=key, source=source)
