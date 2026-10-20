import queue
import threading

import pystray
from PIL import Image

import alerts
import claude_settings
import config
import sprites

# main থ্রেডকে পাঠানো কমান্ড (উইন্ডো সংক্রান্ত সব কাজ ওখানেই হয়)
SHOW = "show"
HIDE = "hide"
QUIT = "quit"

# আইকনের অবস্থা (design §4)
FREE = "free"
PEER = "peer"
ME = "me"
CONFLICT = "conflict"
OFFLINE = "offline"


def _image(grid, colors, size=None, overlay=None):
    # কী করছে: টেক্সট-গ্রিড স্প্রাইটকে RGBA ছবিতে বদলায় (প্রতি ঘর = এক ব্লক), চাইলে কোণে একটি ডট বসায়
    # কেন লাগছে: ট্রে আইকন রান-টাইমে বানাই — কোনো .ico/.png ফাইল শিপ করতে হয় না (design §4)
    # real world-এ এটা কোথায় দেখা যায়: কোড থেকে আইকন/অ্যাভাটার জেনারেট করা
    size = size or config.TRAY_ICON_PX
    cells = len(grid)
    scale = max(1, size // cells)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()
    for row, line in enumerate(grid):
        for col, ch in enumerate(line):
            color = colors.get(ch)
            if color is None:
                continue                      # '.' = স্বচ্ছ
            r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            for y in range(row * scale, min(size, (row + 1) * scale)):
                for x in range(col * scale, min(size, (col + 1) * scale)):
                    pixels[x, y] = (r, g, b, 255)
    if overlay:
        _dot(img, overlay[0], overlay[1], size, scale)
    return img


def _dot(img, color, corner, size, scale):
    # কী করছে: আইকনের এক কোণে ৩ ঘর মাপের একটি ভরাট ডট আঁকে ("আমি" বা দ্বন্দ্ব চিহ্ন)
    # কেন লাগছে: একই ল্যাম্প আইকনে কে কাজ করছে / দ্বন্দ্ব হচ্ছে তা আলাদা করতে (design §4)
    # real world-এ এটা কোথায় দেখা যায়: আইকনের উপর ব্যাজ/badge overlay
    pixels = img.load()
    r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    span = max(3, scale * 3)
    x0 = size - span if "right" in corner else 0
    y0 = 0 if "top" in corner else size - span
    for y in range(y0, y0 + span):
        for x in range(x0, x0 + span):
            pixels[x, y] = (r, g, b, 255)


def build_icons():
    # কী করছে: পাঁচটি অবস্থার আইকন একবারে বানিয়ে dict-এ রাখে
    # কেন লাগছে: প্রতি সেকেন্ডে ছবি বানানো অপচয়; অবস্থা বদলালে শুধু তুলে নিই
    # real world-এ এটা কোথায় দেখা যায়: অ্যাসেট প্রি-ক্যাশ করে রাখা
    lamp = (sprites.TRAY_LAMP, sprites.TRAY_LAMP_COLORS)
    moon = (sprites.TRAY_MOON, sprites.TRAY_MOON_COLORS)
    return {
        FREE: _image(*moon),
        PEER: _image(*lamp),
        ME: _image(*lamp, overlay=(config.ACCENT, "bottom-right")),
        CONFLICT: _image(*lamp, overlay=(config.WARNING, "top-right")),
        OFFLINE: _image(sprites.TRAY_MOON, sprites.TRAY_MOON_OFF_COLORS),
    }


def icon_state(snap):
    # কী করছে: snapshot দেখে কোন আইকন দেখানো উচিত তা বলে (design §4-এর টেবিল)
    # কেন লাগছে: শুদ্ধ ফাংশন — টেস্টযোগ্য, আর tray/main দুই জায়গা থেকেই ডাকা যায়
    # real world-এ এটা কোথায় দেখা যায়: state → presentation ম্যাপিং
    if not snap.connected:
        return OFFLINE                        # সার্ভারে পৌঁছাচ্ছি না — অবস্থা পুরনো হতে পারে
    if snap.me.working and snap.peer.working:
        return CONFLICT
    if snap.me.working:
        return ME
    if snap.peer.working:
        return PEER
    return FREE


class Tray:
    def __init__(self, commands, settings_store=None, status_fn=None):
        # কী করছে: ট্রে আইকন ও মেনু তৈরি করে; সব উইন্ডো-অ্যাকশন commands কিউতে পাঠায়
        # কেন লাগছে: pystray নিজের থ্রেডে চলে — সেখান থেকে pyglet উইন্ডো ছোঁয়া নিষেধ (techspec §3)
        # real world-এ এটা কোথায় দেখা যায়: UI থ্রেড ও ট্রে/ব্যাকগ্রাউন্ড থ্রেডের মাঝে message passing
        self.commands = commands
        self.settings = settings_store          # alerts চালু/বন্ধ রাখে ও সেভ করে (userconfig)
        self.status_fn = status_fn or (lambda: config.WINDOW_TITLE)
        self.icons = build_icons()
        self._state = None
        self._title = None
        self._icon = None
        self._thread = None

    # ---- মেনু ----

    def _menu(self):
        alert_items = [
            pystray.MenuItem(label, self._toggle(kind), checked=self._checked(kind))
            for kind, label in (("free", "It's free"), ("conflict", "Both working"))
        ]
        integration = pystray.Menu(
            pystray.MenuItem("Reinstall hooks", self._hooks(claude_settings.install)),
            pystray.MenuItem("Remove hooks", self._hooks(claude_settings.remove)),
        )
        return pystray.Menu(
            pystray.MenuItem("Open rooms", self._send(SHOW), default=True),
            pystray.MenuItem("Hide window", self._send(HIDE)),
            pystray.Menu.SEPARATOR,
            # dibs ও autostart পরের ফেজে (১৪ ও ১৫) — এখন নিষ্ক্রিয় প্লেসহোল্ডার
            pystray.MenuItem("Call dibs", None, enabled=False),
            pystray.MenuItem("Start with Windows", None, enabled=False),
            pystray.MenuItem("Alerts", pystray.Menu(*alert_items)),
            pystray.MenuItem("Claude Code integration", integration),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._send(QUIT)),
        )

    def _send(self, command):
        def handler(icon=None, item=None):
            self.commands.put(command)
        return handler

    def _checked(self, kind):
        return lambda item: bool(self.settings and self.settings.is_enabled(kind))

    def _toggle(self, kind):
        def handler(icon=None, item=None):
            if self.settings is not None:
                self.settings.toggle(kind)      # ফাইলে সেভ হয়, তাই রিস্টার্টেও মনে থাকে
        return handler

    def _hooks(self, action):
        # কী করছে: মেনু থেকে claude_settings-এর install/remove চালায় ও ফল টোস্টে জানায়
        # কেন লাগছে: ট্রে থেকেই ইন্টিগ্রেশন ঠিক করা যায় (appflow §14); এটি শুধু ফাইল কাজ, উইন্ডো নয়
        # real world-এ এটা কোথায় দেখা যায়: ট্রে মেনু থেকে রক্ষণাবেক্ষণের কাজ চালানো
        def handler(icon=None, item=None):
            result = action()
            self.notify("Claude Code integration", result.message[:200])
        return handler

    # ---- জীবনচক্র ----

    def start(self):
        self._icon = pystray.Icon("work_sleep_repeat", self.icons[FREE],
                                  config.WINDOW_TITLE, self._menu())
        self._thread = threading.Thread(target=self._icon.run, name="tray", daemon=True)
        self._thread.start()

    def stop(self):
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def update(self, snap, status_text):
        # কী করছে: অবস্থা বদলালে আইকন ও টুলটিপ বদলায় (না বদলালে কিছুই করে না)
        # কেন লাগছে: প্রতি সেকেন্ডে একই ছবি বসালে ট্রে ঝিকমিক করতে পারে; বদলেই শুধু কাজ
        # real world-এ এটা কোথায় দেখা যায়: UI diffing — যা বদলায়নি তা আবার আঁকি না
        if self._icon is None:
            return
        state = icon_state(snap)
        title = status_text if snap.connected else status_text + " — offline"
        if state != self._state:
            self._state = state
            self._icon.icon = self.icons[state]
        if title != self._title:
            self._title = title
            self._icon.title = title

    def notify(self, title, body):
        # কী করছে: Windows টোস্ট দেখায় (ট্রে আইকন থেকে)
        # কেন লাগছে: অ্যাপ লুকানো থাকলেও "Claude ফাঁকা" জানানোই Phase 13-এর মূল কথা
        # real world-এ এটা কোথায় দেখা যায়: ব্যাকগ্রাউন্ড অ্যাপের ব্যালুন/টোস্ট নোটিফিকেশন
        if self._icon is None:
            return
        try:
            self._icon.notify(body, title)
        except Exception as exc:              # টোস্ট ব্যর্থ হলেও অ্যাপ চলবে
            print("WSR: toast failed:", exc)


class AlertSettings:
    def __init__(self, store=None):
        # কী করছে: কোন অ্যালার্ট চালু তা ধরে রাখে ও বদলালে userconfig দিয়ে ফাইলে লেখে
        # কেন লাগছে: gate বলে — বন্ধ করলে রিস্টার্টের পরেও বন্ধ থাকতে হবে
        # real world-এ এটা কোথায় দেখা যায়: ছোট সেটিংস স্টোর, মেনুর চেকবক্সের পেছনে
        self._lock = threading.Lock()
        self._values = dict(config.ALERTS_DEFAULT)
        self._store = store                    # callable(dict) — ফাইলে সেভ করে

    def load(self, values):
        with self._lock:
            for kind in alerts.KINDS:
                if kind in (values or {}):
                    self._values[kind] = bool(values[kind])

    def is_enabled(self, kind):
        with self._lock:
            return self._values.get(kind, True)

    def toggle(self, kind):
        with self._lock:
            self._values[kind] = not self._values.get(kind, True)
            snapshot = dict(self._values)
        if self._store is not None:
            self._store(snapshot)
        return snapshot[kind]

    def as_dict(self):
        with self._lock:
            return dict(self._values)


def make_commands():
    # কী করছে: ট্রে → main থ্রেডের কমান্ড কিউ বানায়
    # কেন লাগছে: এক জায়গায় রাখলে main শুধু drain করে; tray কখনো উইন্ডো ছোঁয় না
    # real world-এ এটা কোথায় দেখা যায়: thread-safe command queue
    return queue.Queue()
