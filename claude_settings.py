import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import config

# ছয়টি ইভেন্ট (techspec §4.1) — PostToolUse-এ matcher "*" লাগে, বাকিগুলোতে নয়
HOOK_EVENTS = (
    ("SessionStart", None),
    ("UserPromptSubmit", None),
    ("PostToolUse", "*"),
    ("Notification", None),
    ("Stop", None),
    ("SessionEnd", None),
)

# statusLine ইচ্ছাকৃতভাবে বাদ — usage ফিচার ২০২৬-১০-২০-এ কাটা হয়েছে (tracker Decisions)।
# কারো statusLine থাকলে (আমাদের পুরনোটিও) আমরা ছুঁই না।


@dataclass
class Result:
    # কী করছে: এক অপারেশনের ফল — সফল কিনা, কী বদলেছে, ব্যাকআপ কোথায়, বার্তা কী
    # কেন লাগছে: CLI ছাপবে, আর Phase 15-এর setup UI একই তথ্য ডায়ালগে দেখাবে
    # real world-এ এটা কোথায় দেখা যায়: ইনস্টলার/মাইগ্রেশন টুলের রিপোর্ট অবজেক্ট
    ok: bool
    action: str
    message: str
    path: str = ""
    backup: str = ""
    changed: list = field(default_factory=list)
    present: list = field(default_factory=list)


def settings_path():
    # কী করছে: Claude Code-এর ইউজার settings.json-এর পথ দেয়
    # কেন লাগছে: হুক এখানেই লেখা হয় (techspec §4.3); টেস্ট নিজের temp পথ দেয়
    # real world-এ এটা কোথায় দেখা যায়: অ্যাপের per-user config ফাইলের স্ট্যান্ডার্ড জায়গা
    return Path.home() / ".claude" / "settings.json"


def hook_command(host=config.LISTEN_HOST, port=config.LISTEN_PORT):
    # কী করছে: সব ইভেন্টের জন্য এক curl কমান্ড বানায় — JSON stdin থেকে নিয়ে আমাদের পোর্টে POST
    # কেন লাগছে: সবসময় exit 0 (|| true) ও ১ সেকেন্ড টাইমআউট, যাতে অ্যাপ বন্ধ থাকলেও Claude Code
    #           কখনো আটকে বা ব্লক না হয় (exit 2 হলে CC কাজ থামাত) — techspec §4.2
    # real world-এ এটা কোথায় দেখা যায়: fire-and-forget webhook — ব্যর্থতা চুপচাপ গিলে ফেলা
    return ("curl -s -m 1 -X POST --data-binary @- "
            "http://%s:%d/hook >/dev/null 2>&1 || true" % (host, port))


def marker(host=config.LISTEN_HOST, port=config.LISTEN_PORT):
    # কী করছে: "127.0.0.1:47821" — যে টুকরো দেখে আমাদের এন্ট্রি চিনি
    # কেন লাগছে: install/remove শুধু নিজের এন্ট্রি ছুঁবে, অন্যের হুক নয় (techspec §4.3)
    # real world-এ এটা কোথায় দেখা যায়: শেয়ার্ড কনফিগে নিজের অংশ চেনার জন্য ট্যাগ/মার্কার
    return "%s:%d" % (host, port)


def _entry(event, matcher, command):
    # কী করছে: একটি হুক এন্ট্রি (dict) বানায়; matcher থাকলে সেটি আগে বসে
    # কেন লাগছে: §4.3-এর ঠিক সেই শেপ লিখতে হয়, নাহলে Claude Code চিনবে না
    # real world-এ এটা কোথায় দেখা যায়: কনফিগ স্কিমা মেনে নোড তৈরি করা
    inner = {"hooks": [{"type": "command", "command": command}]}
    if matcher is None:
        return inner
    return {"matcher": matcher, "hooks": inner["hooks"]}


def _read(path):
    # কী করছে: ফাইল পড়ে (data, error) দেয় — না থাকলে ({}, None), ভুল JSON হলে (None, কারণ)
    # কেন লাগছে: ভুল JSON-এ কিছুই লেখা যাবে না, পরিষ্কার error দেখাতে হবে (techspec §4.3, §12)
    # real world-এ এটা কোথায় দেখা যায়: কনফিগ পড়ার সময় fail-fast, আংশিক লেখা নয়
    if not path.exists():
        return {}, None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, "could not read %s: %s" % (path, exc)
    if not raw.strip():
        return {}, None
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, "%s is not valid JSON (%s) — nothing was changed" % (path, exc)
    if not isinstance(data, dict):
        return None, "%s does not contain a JSON object — nothing was changed" % path
    return data, None


def _backup(path):
    # কী করছে: লেখার আগে টাইমস্ট্যাম্প-সহ ব্যাকআপ কপি বানায় (ফাইল থাকলে); পথ ফেরত দেয়
    # কেন লাগছে: §4.3-এর নিয়ম — "always write a timestamped backup first"
    # real world-এ এটা কোথায় দেখা যায়: কনফিগ বদলানোর আগে .bak রেখে দেওয়া
    if not path.exists():
        return ""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(path.name + ".wsr-backup-" + stamp)
    dest.write_bytes(path.read_bytes())
    return str(dest)


def _write(path, data):
    # কী করছে: ২-স্পেস indent-এ JSON লিখে (temp ফাইল হয়ে) জায়গামতো বসায়
    # কেন লাগছে: Claude Code-এর নিজের ফরম্যাট ২-স্পেস, তাই remove-এর পর ফাইল আগের মতোই দেখায়;
    #           temp + replace মানে মাঝপথে ক্র্যাশেও অর্ধেক লেখা ফাইল থাকে না
    # real world-এ এটা কোথায় দেখা যায়: atomic config write (write-temp-then-rename)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".wsr-tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _hooks_of(data, tag):
    # কী করছে: data["hooks"] ফেরত দেয় (না থাকলে খালি dict); অন্য টাইপ হলে error বার্তা
    # কেন লাগছে: কেউ হাতে লিখে "hooks" অন্য কিছু বানালে আমরা তা নষ্ট করব না
    # real world-এ এটা কোথায় দেখা যায়: ডিফেনসিভ কনফিগ পার্সিং
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return None, "%s: \"hooks\" is not an object — nothing was changed" % tag
    return hooks, None


def install(path=None, host=config.LISTEN_HOST, port=config.LISTEN_PORT):
    # কী করছে: ছয়টি ইভেন্টে আমাদের curl হুক যোগ করে (আগে ব্যাকআপ); যেটা আগেই আছে তা ছোঁয় না
    # কেন লাগছে: এটাই ডিটেকশন চালু করার একমাত্র ধাপ; বারবার চালালেও ডুপ্লিকেট হবে না (§4.3)
    # real world-এ এটা কোথায় দেখা যায়: idempotent installer — "ensure present", "set" নয়
    path = Path(path) if path is not None else settings_path()
    data, error = _read(path)
    if error:
        return Result(False, "install", error, str(path))
    hooks, error = _hooks_of(data, str(path))
    if error:
        return Result(False, "install", error, str(path))

    tag = marker(host, port)
    command = hook_command(host, port)
    changed, present = [], []
    planned = {}
    for event, matcher in HOOK_EVENTS:
        entries = hooks.get(event, [])
        if not isinstance(entries, list):
            return Result(False, "install",
                          "%s: hooks.%s is not a list — nothing was changed" % (path, event),
                          str(path))
        if any(tag in json.dumps(e) for e in entries):
            present.append(event)                      # আমাদের এন্ট্রি আগেই আছে
            continue
        planned[event] = list(entries) + [_entry(event, matcher, command)]
        changed.append(event)

    if not changed:
        return Result(True, "install", "already installed — nothing to do",
                      str(path), "", [], present)

    backup = _backup(path)
    data.setdefault("hooks", hooks)                    # "hooks" না থাকলে এখন যোগ হবে (শেষে)
    for event, entries in planned.items():
        hooks[event] = entries
    _write(path, data)
    return Result(True, "install", "installed hooks: " + ", ".join(changed),
                  str(path), backup, changed, present)


def remove(path=None, host=config.LISTEN_HOST, port=config.LISTEN_PORT):
    # কী করছে: শুধু যে এন্ট্রিগুলোতে আমাদের মার্কার আছে সেগুলো মুছে দেয় (আগে ব্যাকআপ);
    #           কোনো ইভেন্টের তালিকা ফাঁকা হলে চাবিটিও যায়, "hooks" ফাঁকা হলে সেটিও
    # কেন লাগছে: অন্য কারো হুক, statusLine বা অন্য চাবি অবিকৃত থাকতে হবে; আর install-এর আগের
    #           ফাইলের সাথে মিলতে হবে (plan Step B gate)
    # real world-এ এটা কোথায় দেখা যায়: uninstaller যা শুধু নিজের লেখা অংশ ফিরিয়ে নেয়
    path = Path(path) if path is not None else settings_path()
    data, error = _read(path)
    if error:
        return Result(False, "remove", error, str(path))
    hooks, error = _hooks_of(data, str(path))
    if error:
        return Result(False, "remove", error, str(path))

    tag = marker(host, port)
    changed = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            continue                                   # আমাদের নয় — ছুঁই না
        kept = [e for e in entries if tag not in json.dumps(e)]
        if len(kept) != len(entries):
            changed[event] = kept

    if not changed:
        return Result(True, "remove", "nothing of ours to remove", str(path))

    backup = _backup(path)
    for event, kept in changed.items():
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]                           # ফাঁকা তালিকা রেখে যাই না
    if not hooks and "hooks" in data:
        del data["hooks"]                              # আমরা যোগ করেছিলাম, তাই ফাঁকা হলে তুলে নিই
    _write(path, data)
    return Result(True, "remove", "removed our hooks from: " + ", ".join(changed),
                  str(path), backup, list(changed))


def status(path=None, host=config.LISTEN_HOST, port=config.LISTEN_PORT):
    # কী করছে: কোন ইভেন্টে আমাদের হুক আছে/নেই তা জানায়, আর কোনো statusLine থাকলে সেটি বলে
    # কেন লাগছে: ইনস্টল করার আগে/পরে অবস্থা দেখতে; setup UI-ও এটিই দেখাবে
    # real world-এ এটা কোথায় দেখা যায়: "doctor"/"status" সাব-কমান্ড
    path = Path(path) if path is not None else settings_path()
    data, error = _read(path)
    if error:
        return Result(False, "status", error, str(path))
    hooks, error = _hooks_of(data, str(path))
    if error:
        return Result(False, "status", error, str(path))

    tag = marker(host, port)
    present, missing = [], []
    for event, _matcher in HOOK_EVENTS:
        entries = hooks.get(event, [])
        entries = entries if isinstance(entries, list) else []
        (present if any(tag in json.dumps(e) for e in entries) else missing).append(event)
    note = ""
    if "statusLine" in data:
        note = "  (a statusLine exists; we never install or touch one — usage feature dropped)"
    message = "installed: %s | missing: %s%s" % (
        ", ".join(present) or "none", ", ".join(missing) or "none", note)
    return Result(True, "status", message, str(path), "", missing, present)


def main(argv):
    # কী করছে: CLI — install | remove | status, ফল ছাপে ও exit কোড দেয়
    # কেন লাগছে: Phase 10-এ হাতে চালিয়ে ডিটেকশন চালু/বন্ধ করা যায় (plan Step B)
    # real world-এ এটা কোথায় দেখা যায়: ছোট টুলের সাব-কমান্ড CLI
    actions = {"install": install, "remove": remove, "status": status}
    action = argv[1] if len(argv) > 1 else ""
    if action not in actions:
        print("usage: python claude_settings.py install|remove|status")
        return 2
    result = actions[action]()
    print("%s: %s" % (result.action, result.message))
    print("file  : %s" % result.path)
    if result.backup:
        print("backup: %s" % result.backup)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
