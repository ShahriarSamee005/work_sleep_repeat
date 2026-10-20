"""Phase 9 spike — install / remove temporary Claude Code hooks + status line.

Writes the spike hooks (techspec §4.2 command) and status line (§5.2 command)
into %USERPROFILE%\\.claude\\settings.json so we can observe, on real Windows
Claude Code, which events fire and what the status-line JSON looks like.

Safety (mirrors the real claude_settings.py contract, techspec §4.3):
  * Always writes a timestamped backup first.
  * Appends to existing hook lists; never deletes other people's entries.
  * Never silently replaces an existing statusLine — prints it and asks y/n.
  * Aborts on invalid JSON, changing nothing.

Usage:
  python spike/install_spike_hooks.py            # install
  python spike/install_spike_hooks.py --remove   # restore newest spike backup

This is a SPIKE tool. It only writes the spike backup name
(settings.json.wsr-spike-backup-<timestamp>) so --remove never touches a
backup made by the real installer.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

PORT_MARKER = "127.0.0.1:47821"

HOOK_CMD = (
    'curl -s -m 1 -X POST --data-binary @- '
    'http://127.0.0.1:47821/hook >/dev/null 2>&1 || true'
)
STATUS_CMD = (
    'curl -s -m 1 -X POST --data-binary @- '
    'http://127.0.0.1:47821/statusline 2>/dev/null || true'
)

# Events to subscribe to (techspec §4.1). PostToolUse carries matcher "*".
HOOK_EVENTS = [
    "SessionStart",
    "UserPromptSubmit",
    "PostToolUse",
    "Notification",
    "Stop",
    "SessionEnd",
]

SETTINGS_PATH = Path(os.path.expandvars(r"%USERPROFILE%")) / ".claude" / "settings.json"
BACKUP_PREFIX = "settings.json.wsr-spike-backup-"

# Absolute path to spike/logs, forward slashes so it works inside Git Bash
# (Claude Code's expected hook shell on Windows).
LOGS_DIR = (Path(__file__).resolve().parent / "logs").as_posix()
SHELL_PROBE_FILE = f"{LOGS_DIR}/shell.txt"
# One extra UserPromptSubmit hook that records the shell, $0, and the curl path.
SHELL_PROBE_CMD = (
    f'echo "$SHELL|$0|$(command -v curl)" >> "{SHELL_PROBE_FILE}" || true'
)


def _hook_block(command: str, matcher: str | None = None) -> dict:
    block: dict = {"hooks": [{"type": "command", "command": command}]}
    if matcher is not None:
        block["matcher"] = matcher
    return block


def _is_spike_block(block: dict) -> bool:
    """True if a hook block is one of ours (contains our port or probe file)."""
    for h in block.get("hooks", []):
        cmd = h.get("command", "")
        if PORT_MARKER in cmd or SHELL_PROBE_FILE in cmd:
            return True
    return False


def _load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        print(f"{SETTINGS_PATH} does not exist — will create a new {{}}.")
        return {}
    text = SETTINGS_PATH.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"ABORT: {SETTINGS_PATH} is not valid JSON ({exc}). Nothing changed.",
              file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(data, dict):
        print("ABORT: settings.json top level is not an object. Nothing changed.",
              file=sys.stderr)
        raise SystemExit(2)
    return data


def _write_backup() -> Path | None:
    if not SETTINGS_PATH.exists():
        print("No existing settings.json to back up (creating fresh).")
        return None
    # Don't let a re-install back up an already-spiked file: that backup would
    # shadow the clean one and make --remove restore spiked settings.
    current = SETTINGS_PATH.read_text(encoding="utf-8")
    if PORT_MARKER in current or SHELL_PROBE_FILE in current:
        print("Current settings already contain spike entries — keeping the "
              "existing clean backup, not overwriting it.")
        return None
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup = SETTINGS_PATH.with_name(BACKUP_PREFIX + ts)
    backup.write_bytes(SETTINGS_PATH.read_bytes())
    print(f"Backup written: {backup}")
    return backup


def _save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {SETTINGS_PATH}")


def _ask_yes_no(prompt: str) -> bool:
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def install() -> int:
    data = _load_settings()
    _write_backup()

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        print("ABORT: existing 'hooks' is not an object. Nothing changed.",
              file=sys.stderr)
        return 2

    added = 0
    for event in HOOK_EVENTS:
        lst = hooks.setdefault(event, [])
        if not isinstance(lst, list):
            print(f"ABORT: hooks['{event}'] is not a list. Nothing changed.",
                  file=sys.stderr)
            return 2
        # skip if one of ours is already present (idempotent re-install)
        if any(isinstance(b, dict) and _is_spike_block(b) for b in lst):
            print(f"  {event}: spike hook already present, skipping.")
            continue
        matcher = "*" if event == "PostToolUse" else None
        lst.append(_hook_block(HOOK_CMD, matcher))
        added += 1
        print(f"  {event}: spike hook appended.")

    # extra UserPromptSubmit hook: shell / $0 / curl probe
    ups = hooks.setdefault("UserPromptSubmit", [])
    if not any(isinstance(b, dict) and SHELL_PROBE_FILE in json.dumps(b) for b in ups):
        ups.append(_hook_block(SHELL_PROBE_CMD))
        added += 1
        print("  UserPromptSubmit: shell-probe hook appended.")
    else:
        print("  UserPromptSubmit: shell-probe hook already present, skipping.")

    # status line — never silently replace one that isn't ours
    existing_sl = data.get("statusLine")
    if existing_sl is None:
        data["statusLine"] = {"type": "command", "command": STATUS_CMD}
        print("  statusLine: installed spike status line.")
    else:
        existing_cmd = ""
        if isinstance(existing_sl, dict):
            existing_cmd = existing_sl.get("command", "")
        if PORT_MARKER in existing_cmd:
            print("  statusLine: spike status line already present, skipping.")
        else:
            print("\n  An existing statusLine is set:")
            print(f"    {json.dumps(existing_sl)}")
            if _ask_yes_no("  Replace it with the spike status line? [y/N] "):
                data["statusLine"] = {"type": "command", "command": STATUS_CMD}
                print("  statusLine: replaced (original is in the backup).")
            else:
                print("  statusLine: left unchanged. "
                      "Status-line JSON will NOT be observed this run.")

    _save_settings(data)
    print(f"\nDone. {added} hook entr{'y' if added == 1 else 'ies'} added.")
    print("Start the logger (python spike/logger_server.py), then use Claude Code.")
    print("Run with --remove to restore the pre-spike settings.")
    return 0


def _newest_spike_backup() -> Path | None:
    candidates = sorted(SETTINGS_PATH.parent.glob(BACKUP_PREFIX + "*"))
    return candidates[-1] if candidates else None


def remove() -> int:
    backup = _newest_spike_backup()
    if backup is None:
        print("No spike backup found. If the settings had no backup (file was "
              "created fresh by install), delete the spike entries by hand or "
              "remove settings.json if you had none before.", file=sys.stderr)
        return 1
    # Safety copy of the current file before we overwrite it.
    if SETTINGS_PATH.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        pre = SETTINGS_PATH.with_name(f"settings.json.pre-remove-{ts}")
        pre.write_bytes(SETTINGS_PATH.read_bytes())
        print(f"Current settings copied to: {pre}")
    SETTINGS_PATH.write_bytes(backup.read_bytes())
    print(f"Restored settings from: {backup}")
    print("Spike hooks + status line removed. Diff against the backup to confirm.")
    return 0


def main(argv: list[str]) -> int:
    if "--remove" in argv:
        return remove()
    return install()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
