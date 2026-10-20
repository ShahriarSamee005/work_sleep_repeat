import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config

LOCAL_CLIENTS = ("127.0.0.1", "::1", "::ffff:127.0.0.1")   # শুধু এই পিসি


class _Server(ThreadingHTTPServer):
    # কী করছে: ThreadingHTTPServer-এর দুটি ডিফল্ট বদলায় — ঠিকানা পুনর্ব্যবহার বন্ধ, থ্রেড daemon
    # কেন লাগছে: Windows-এ SO_REUSEADDR থাকলে দ্বিতীয় কপিও একই পোর্টে bind করতে পারে — তাহলে
    #           "পোর্ট দখল = single-instance লক" ভেঙে যেত (techspec §8)। daemon থ্রেড অ্যাপ বন্ধে আটকায় না।
    # real world-এ এটা কোথায় দেখা যায়: একই পোর্টে দুই কপি চালু হওয়া আটকাতে bind-কে লক হিসেবে ব্যবহার
    allow_reuse_address = False
    daemon_threads = True


class _Handler(BaseHTTPRequestHandler):
    # কী করছে: হুক ও কন্ট্রোল রিকোয়েস্ট সামলায় (techspec §8-এর রুট তালিকা)
    # কেন লাগছে: Claude Code-এর হুক curl দিয়ে JSON POST করে; দ্রুত উত্তর দিতে হয় যাতে CC না আটকায়
    # real world-এ এটা কোথায় দেখা যায়: লোকাল এজেন্ট/ডেমনের ছোট HTTP কন্ট্রোল API
    server_version = "WorkSleepRepeat"

    def _client_is_local(self):
        return self.client_address[0] in LOCAL_CLIENTS

    def _reply(self, code, body=b""):
        # কী করছে: স্ট্যাটাস + (দরকার হলে) ছোট বডি পাঠায়; সকেট ভেঙে গেলেও ফেলে দেয় না
        # কেন লাগছে: curl -m 1 আগেই সংযোগ ছেড়ে দিতে পারে; তাতে সার্ভার লুপ মরতে পারে না
        # real world-এ এটা কোথায় দেখা যায়: client disconnect-এ সহনশীল সার্ভার কোড
        try:
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)
        except OSError:
            pass

    def _read_body(self):
        # কী করছে: Content-Length দেখে বডি পড়ে (সর্বোচ্চ MAX_BODY_BYTES), bytes দেয়
        # কেন লাগছে: বড় বা ভুল পেলোড যেন মেমরি/সময় না খায় (techspec §8)
        # real world-এ এটা কোথায় দেখা যায়: যেকোনো সার্ভারে request body size limit
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return b""
        if length <= 0:
            return b""
        return self.rfile.read(min(length, config.MAX_BODY_BYTES))

    def do_POST(self):
        if not self._client_is_local():
            self._reply(403)
            return
        path = self.path.split("?", 1)[0]
        if path == "/hook":
            raw = self._read_body()
            self._reply(204)                       # আগে উত্তর, তারপর কাজ — হুক দ্রুত ছাড়া পায়
            self.server.wsr_dispatch(raw)
        elif path == "/statusline":
            self._read_body()                      # usage ফিচার বাদ; পুরনো হুক থাকলেও যাতে error না পায়
            self._reply(204)
        elif path == "/show":
            self._reply(204)
            self.server.wsr_show()
        else:
            self._reply(404)

    def do_GET(self):
        if not self._client_is_local():
            self._reply(403)
            return
        if self.path.split("?", 1)[0] == "/health":
            self._reply(200, b"ok")
        else:
            self._reply(404)

    def log_message(self, fmt, *args):
        # কী করছে: ডিফল্ট stderr অ্যাক্সেস লগ বন্ধ করে
        # কেন লাগছে: প্রতি হুকে এক লাইন কনসোলে এলে চলার সময় ভরে যেত
        # real world-এ এটা কোথায় দেখা যায়: লাইব্রেরির ডিফল্ট লগিং নিজের লগারে বদলে নেওয়া
        pass


class Listener:
    def __init__(self, on_event, on_show=None,
                 host=config.LISTEN_HOST, port=config.LISTEN_PORT):
        # কী করছে: লোকাল HTTP সার্ভারটি প্রস্তুত করে (এখনো bind করে না)
        # কেন লাগছে: হুক → অ্যাপ পথটা এটাই; on_event কলব্যাক ইভেন্টকে main থ্রেডে পাঠায়
        # real world-এ এটা কোথায় দেখা যায়: ছোট embedded সার্ভারকে ক্লাসে মুড়ে নেওয়া
        self.host = host
        self.port = port
        self._on_event = on_event
        self._on_show = on_show
        self._server = None
        self._thread = None
        self.bad_json_logged = False

    def try_bind(self):
        # কী করছে: পোর্টে bind করার চেষ্টা করে — পারলে True, পোর্ট দখল থাকলে False
        # কেন লাগছে: bind-ই single-instance লক; দখল মানে অ্যাপ আগেই চলছে (appflow §2)
        # real world-এ এটা কোথায় দেখা যায়: "একটাই কপি চলবে" নিশ্চিত করতে পোর্ট/ফাইল লক
        try:
            server = _Server((self.host, self.port), _Handler)
        except OSError:
            return False
        server.wsr_dispatch = self._dispatch
        server.wsr_show = self._show
        self._server = server
        return True

    def start(self):
        # কী করছে: সার্ভারকে নিজের daemon থ্রেডে চালু করে
        # কেন লাগছে: রিকোয়েস্ট সামলানো রেন্ডার লুপকে থামাতে পারে না (techspec §3)
        # real world-এ এটা কোথায় দেখা যায়: UI থ্রেড আলাদা, I/O ব্যাকগ্রাউন্ড থ্রেডে
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="listener", daemon=True)
        self._thread.start()

    def stop(self):
        # কী করছে: সার্ভার থামিয়ে সকেট বন্ধ করে (পোর্ট ছেড়ে দেয়)
        # কেন লাগছে: পরিষ্কার বন্ধ হলে পরের কপি সাথে সাথে bind করতে পারে
        # real world-এ এটা কোথায় দেখা যায়: graceful shutdown — লক ছেড়ে দিয়ে বেরোনো
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def _dispatch(self, raw):
        # কী করছে: হুকের কাঁচা বডি JSON হিসেবে পড়ে কলব্যাকে দেয়; ভুল JSON একবার লগ করে উপেক্ষা
        # কেন লাগছে: খারাপ পেলোড কখনো সার্ভার লুপে exception তুলতে পারে না (techspec §12)
        # real world-এ এটা কোথায় দেখা যায়: বাইরের ইনপুট পার্সিং — ব্যর্থ হলে ড্রপ, ক্র্যাশ নয়
        try:
            event = json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, AttributeError):
            if not self.bad_json_logged:
                self.bad_json_logged = True
                print("WSR: ignoring malformed hook payload (logged once)")
            return
        if not isinstance(event, dict):
            return
        try:
            self._on_event(event)
        except Exception as exc:                  # কলব্যাকের ভুলেও সার্ভার মরবে না
            print("WSR: hook callback failed:", exc)

    def _show(self):
        if self._on_show is None:
            return
        try:
            self._on_show()
        except Exception as exc:
            print("WSR: show callback failed:", exc)


def ping_show(host=config.LISTEN_HOST, port=config.LISTEN_PORT,
              timeout=config.HTTP_TIMEOUT):
    # কী করছে: চলতি কপিকে POST /show পাঠায় — সফল হলে True
    # কেন লাগছে: পোর্ট দখল থাকলে দ্বিতীয় কপি প্রথমটির উইন্ডো দেখিয়ে নিজে বেরিয়ে যায় (appflow §2)
    # real world-এ এটা কোথায় দেখা যায়: single-instance অ্যাপে "already running → focus it"
    conn = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("POST", "/show", body=b"", headers={"Content-Length": "0"})
        return conn.getresponse().status < 400
    except OSError:
        return False
    finally:
        if conn is not None:
            conn.close()
