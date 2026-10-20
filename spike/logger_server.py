"""Phase 9 spike — logging HTTP server.

Stands in for the real listener (techspec §8). Captures everything Claude Code
sends to /hook and /statusline so we can inspect real payloads on Windows:
hook event names, session ids, and the status-line JSON (to see whether
`rate_limits` is present and what format `resets_at` uses).

Run:   python spike/logger_server.py
Stop:  Ctrl+C

Every request is appended as one JSON line to spike/logs/events.jsonl.
Nothing here imports or touches the real app modules.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 47821
MAX_BODY = 256 * 1024  # mirror techspec §8 body limit

LOG_DIR = Path(__file__).resolve().parent / "logs"
EVENTS_FILE = LOG_DIR / "events.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_event(record: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with EVENTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _summary(path: str, body_json) -> str:
    """Short human line for the console."""
    if isinstance(body_json, dict):
        if path == "/hook":
            ev = body_json.get("hook_event_name", "?")
            sid = str(body_json.get("session_id", "?"))
            return f"hook  event={ev:<16} session={sid[:12]}"
        if path == "/statusline":
            rl = None
            # status line payload nests rate_limits in a few possible places
            for key in ("rate_limits",):
                if key in body_json:
                    rl = body_json[key]
            has_rl = "rate_limits PRESENT" if rl is not None else "rate_limits MISSING"
            sid = str(body_json.get("session_id", "?"))
            return f"status session={sid[:12]} {has_rl}"
    return f"{path} (non-dict / raw body)"


class Handler(BaseHTTPRequestHandler):
    # keep the console clean; we print our own lines
    def log_message(self, fmt, *args):  # noqa: N802
        pass

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            length = MAX_BODY
        return self.rfile.read(length) if length else b""

    def _record(self, path: str, raw: bytes):
        text = raw.decode("utf-8", errors="replace")
        body_json = None
        try:
            body_json = json.loads(text) if text.strip() else None
        except (json.JSONDecodeError, ValueError):
            body_json = None
        record = {
            "time": _now_iso(),
            "path": path,
            "client": self.client_address[0],
            "body_json": body_json,
            "body_raw": None if body_json is not None else text,
        }
        _append_event(record)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {_summary(path, body_json)}",
              flush=True)
        return body_json

    def do_POST(self):  # noqa: N802
        raw = self._read_body()
        if self.path.startswith("/hook"):
            self._record("/hook", raw)
            self.send_response(204)
            self.end_headers()
        elif self.path.startswith("/statusline"):
            self._record("/statusline", raw)
            msg = b"SPIKE OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/health"):
            msg = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
        else:
            self.send_response(404)
            self.end_headers()


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        print(f"Could not bind {HOST}:{PORT} — {exc}", file=sys.stderr)
        print("Is another copy of the logger (or the real app) already running?",
              file=sys.stderr)
        return 1
    print(f"Spike logger listening on http://{HOST}:{PORT}")
    print(f"  POST /hook        -> 204, logged")
    print(f"  POST /statusline  -> 200 'SPIKE OK', logged")
    print(f"  GET  /health      -> 200 'ok'")
    print(f"Appending events to: {EVENTS_FILE}")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
