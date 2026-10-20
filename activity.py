import config

# যে ইভেন্টগুলো আমরা বুঝি (techspec §4.1); অন্য নাম এলে চুপচাপ উপেক্ষা
SESSION_START = "SessionStart"
USER_PROMPT_SUBMIT = "UserPromptSubmit"
POST_TOOL_USE = "PostToolUse"
NOTIFICATION = "Notification"
STOP = "Stop"
SESSION_END = "SessionEnd"

KEEP_ALIVE = (SESSION_START, POST_TOOL_USE, NOTIFICATION)
UNKNOWN_SESSION = "-"      # পেলোডে session_id না থাকলে সবাই এই এক বালতিতে


class _Session:
    __slots__ = ("turn_active", "last_event")

    def __init__(self, now):
        self.turn_active = False
        self.last_event = now


class Activity:
    def __init__(self, idle_timeout=None, stale_cap=None):
        # কী করছে: Claude Code-এর হুক ইভেন্ট থেকে "আমি কাজ করছি কিনা" বের করার ইঞ্জিন বানায়
        # কেন লাগছে: টগল বাদ; এখন প্রতি সেশনের turn_active ও শেষ ইভেন্টের সময়ই একমাত্র সত্য
        # real world-এ এটা কোথায় দেখা যায়: presence/heartbeat সার্ভিস — ইভেন্ট থেকে "active" ঠিক করা
        # নোট: এখানে থ্রেড/সকেট/ফাইল কিছু নেই — সময় বাইরে থেকে দেওয়া হয়, তাই টেস্ট করা সহজ
        self.idle_timeout = config.IDLE_TIMEOUT if idle_timeout is None else idle_timeout
        self.stale_cap = config.TURN_STALE_CAP if stale_cap is None else stale_cap
        self.sessions = {}
        self.working = False

    def handle(self, event, now):
        # কী করছে: একটি হুক ইভেন্ট (dict) নিয়ে সেই সেশনের turn_active ও last_event আপডেট করে;
        #           চেনা নাম না হলে কিছু করে না
        # কেন লাগছে: UserPromptSubmit টার্ন শুরু, Stop শেষ, PostToolUse/Notification জীবিত রাখে,
        #           SessionEnd সেশন মুছে দেয় (techspec §4.4)
        # real world-এ এটা কোথায় দেখা যায়: event handler যা ঘটনা → state transition-এ বদলায়
        if not isinstance(event, dict):
            return False
        name = event.get("hook_event_name")
        if name not in (SESSION_START, USER_PROMPT_SUBMIT, POST_TOOL_USE,
                        NOTIFICATION, STOP, SESSION_END):
            return False                                  # অচেনা ইভেন্ট = উপেক্ষা
        sid = event.get("session_id") or UNKNOWN_SESSION
        if not isinstance(sid, str):
            sid = str(sid)

        if name == SESSION_END:
            self.sessions.pop(sid, None)                  # সেশন শেষ → তালিকা থেকে বাদ
            return True

        session = self.sessions.get(sid)
        if session is None:
            session = self.sessions[sid] = _Session(now)  # যে ইভেন্টেই হোক, সেশন তৈরি হয়
        session.last_event = now
        if name == USER_PROMPT_SUBMIT:
            session.turn_active = True                    # টার্ন চলছে
        elif name == STOP:
            session.turn_active = False                   # টার্ন শেষ, কিন্তু idle timeout বাকি
        return True

    def tick(self, now):
        # কী করছে: বাসি সেশন বাদ দিয়ে এখনকার working মান হিসাব করে ফেরত দেয়
        # কেন লাগছে: Claude Code ক্র্যাশ করলে Stop/SessionEnd আসে না — তাই stale cap লাগে;
        #           আর Stop-এর পরেও IDLE_TIMEOUT পর্যন্ত "কাজ করছে" ধরি (appflow §4, §6)
        # real world-এ এটা কোথায় দেখা যায়: TTL/expiry সহ session store — প্রতি টিকে ঝাড়াই
        for sid in [s for s, sess in self.sessions.items()
                    if now - sess.last_event > self.stale_cap]:
            del self.sessions[sid]
        self.working = any(
            sess.turn_active or (now - sess.last_event < self.idle_timeout)
            for sess in self.sessions.values()
        )
        return self.working
