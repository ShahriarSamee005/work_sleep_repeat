# Phase 9 Spike — Findings

Verifies the assumptions marked **[VERIFY IN SPIKE]** in `docs/techspec.md` and
answers OQ1–OQ4 in `docs/tracker.md`. Nothing in the real app was modified; all
code lives in `spike/`.

**Environment:** Windows 11, Python 3.14.6, PyOpenGL 3.1.10 (+accelerate),
Pillow 12.3.0, requests 2.34.2. `pystray` and `pyglet` are **not installed yet**.

Legend: ✅ confirmed automatically in this spike · ⏳ needs the manual verify run
(see checklist at the bottom) · ⚠️ action needed.

| # | Check (spec ref) | Result | Evidence | Decision |
|---|---|---|---|---|
| 1 | Logger `POST /hook` → 204, logs JSON line (techspec §8) | ✅ | `http=204`; `events.jsonl`: `{"path":"/hook",...,"body_json":{"hook_event_name":"UserPromptSubmit",...}}` | Keep the `/hook` → 204 contract as specced. |
| 2 | Logger `POST /statusline` → 200 + one line (techspec §8, §5.2) | ✅ | Response body `SPIKE OK`; logged with `rate_limits PRESENT` summary | Status line = app's reply works; real app returns the WSR line. |
| 3 | Logger `GET /health` → `ok` | ✅ | `curl .../health` → `ok` | Keep for tests. |
| 4 | Malformed JSON ignored, not crash (techspec §12) | ✅ | `echo 'not json'` → `http=204`, logged as `body_raw:"not json\n"`, server stayed up | Real `listener`/`usage` must log-once + ignore; confirmed shape. |
| 5 | `curl` present & on PATH for hooks (techspec §4.2) | ✅ | `command -v curl` → `/mingw64/bin/curl`; all POSTs above succeeded | curl is available (Git-for-Windows). Confirm the **shell Claude Code itself uses** in row 12. |
| 6 | Install writes a timestamped backup **first** (techspec §4.3) | ✅ | Temp-settings test: `Backup written: ...wsr-spike-backup-<ts>`, `[PASS] backup created` | Keep backup-first rule in real `claude_settings.py`. |
| 7 | Install **appends**, never destroys other hooks/keys (§4.3) | ✅ | `[PASS] foreign model preserved / PreToolUse preserved / SessionStart foreign entry preserved` | Merge-by-append is safe; carry to real installer. |
| 8 | All six events + `PostToolUse` matcher `*` written (§4.1) | ✅ | `[PASS]` for SessionStart/UserPromptSubmit/PostToolUse/Notification/Stop/SessionEnd; `[PASS] PostToolUse matcher is *` | Event set is correct. |
| 9 | Existing foreign `statusLine` **not** silently replaced (§4.3) | ✅ | Prompt shown; declined → `[PASS] foreign statusLine NOT replaced` | Real setup UI must ask the user; confirmed logic. |
| 10 | Re-install is idempotent (no duplicate spike entries) | ✅ | `[PASS] SessionStart still exactly 1 spike entry`; guard: "already contain spike entries — keeping clean backup" | Good; real installer should match by the `127.0.0.1:47821` substring. |
| 11 | `--remove` restores settings **byte-exact** (§4.3) | ✅ | `[PASS] remove restored foreign statusLine / dropped all spike hooks / restored == original pre` | Restore-from-backup is reliable. |
| 12 | Which shell runs hooks; `$0`; curl path (§4.2) **[VERIFY]** | ⏳ | `spike/logs/shell.txt` after a prompt (written by the shell-probe hook) | Fill in after manual run → records OQ answer. |
| 13 | Hooks fire in **terminal** CC — all six events (OQ1) | ⏳ | `spike/logs/events.jsonl` | Expected yes. |
| 14 | Hooks fire in **VS Code** CC — all six (OQ1) | ⏳ | `events.jsonl` | Expected yes. |
| 15 | Hooks fire in **desktop-app Code tab** — all six (OQ1) **[VERIFY]** | ⏳ | `events.jsonl` | **The key unknown.** If no, desktop-app use won't be detected (document as an accepted limit like claude.ai). |
| 16 | `rate_limits` present on this plan + Windows; `resets_at` format (OQ3, §5.1) **[VERIFY]** | ⏳ | `events.jsonl` `/statusline` body | Record epoch-seconds vs ISO. `clock.parse_ts()` must accept the one seen. |
| 17 | Hook returns < 1 s with the app **closed** (NFR1, §4.2) **[VERIFY]** | ⏳ | time a prompt with the logger stopped | `-m 1` curl + `|| true` should keep CC responsive. |
| 18 | GLUT + pystray coexist; X = hide; Show/Hide/Toast work (OQ2) **[VERIFY]** | ⏳ | `spike/logs/tray.txt` | Decides OQ2. Run `pyglet_tray.py` only if GLUT fails a check. |
| 19 | freeglut window layer available for packaging (OQ4) | ✅ (partial) | `glut_tray.py` imported every `glut*` symbol with no error (failed only at the missing `pystray`) | freeglut ships via PyOpenGL on this machine; confirm bundling in Phase 16. |
| 20 | `pystray` / `pyglet` availability | ⚠️ | both `ModuleNotFoundError` | `pip install pystray pillow` before the tray test; add to `requirements.txt` in Phase 13. |

## How to reproduce the automated rows
- Rows 1–5: start `python spike/logger_server.py`, then the `curl` calls in this
  spike (see `spike/logs/events.jsonl` and `spike/logs/server_console.txt`).
- Rows 6–11: logic test run against a throwaway settings file (not the real one):
  install → checks → re-install (idempotency) → `--remove` → diff == original.
- Rows 19–20: `python spike/glut_tray.py` / `pyglet_tray.py` import stage.

## Manual verify checklist (run on real Claude Code)
See the numbered checklist in the chat summary / `docs/tracker.md` Phase 9
section. Fill rows 12–18 from the log files, then complete the Decisions below.

## Decisions to record (draft — confirm after manual run)
- **OQ2 (window layer):** GLUT if row 18 passes all of hide/show/X/toast;
  otherwise pyglet (row from `pyglet_tray.py`).
- **OQ1 (desktop-app Code tab):** detected or documented as an accepted blind
  spot, per row 15.
- **OQ3 (`resets_at`):** record the exact format seen; keep `parse_ts()` dual.
- **OQ4 (freeglut packaging):** freeglut present via PyOpenGL; verify PyInstaller
  bundles the DLL in Phase 16.
