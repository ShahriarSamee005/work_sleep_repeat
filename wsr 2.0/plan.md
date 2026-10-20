# Work•Sleep•Repeat — Build Plan (v2)

> Phases 0–8 are done. v2 continues from Phase 9.
> Rules for every phase:
> 1. Read `prd.md`, `techspec.md`, `design.md`, `appflow.md` sections named in the phase before coding.
> 2. Build only what the phase lists. No extra features.
> 3. Stop at the verification gate. Don't start the next phase until every check passes and `tracker.md` is updated.
> 4. If a contract in `techspec.md` needs to change, change the doc first and note it in `tracker.md` → Decisions.

---

## Phase overview

| Phase | Name | Output | Depends on |
|---|---|---|---|
| 9 | Spike: verify assumptions | `spike/FINDINGS.md`, decisions logged | — |
| 10 | Local detection | hooks → character moves on one PC; toggle removed | 9 |
| 11 | Supabase sync | two PCs in sync; time today persists; offline handling | 10 |
| 12 | Usage limits + split | usage bars, countdowns, split, status line text | 11 |
| 13 | Tray + alerts | tray icon/menu, close-to-tray, toasts (free, limits, conflict) | 12 |
| 14 | Dibs | dibs button, bubble, toasts | 13 |
| 15 | Setup + autostart | first-run dialog, safe settings merge UI, start with Windows | 14 |
| 16 | Package + cleanup | PyInstaller build running on both PCs | 15 |
| 17 | 7-day trial | real daily use, bugs fixed, PRD §6 met | 16 |

---

## Phase 9 — Spike: verify assumptions

**Goal:** answer PRD open questions OQ1 and OQ2 and every **[VERIFY IN SPIKE]** in `techspec.md`, with real evidence, before building anything.

**Builds (throwaway, in `spike/` only):**
- `spike/logger_server.py` — tiny server on `127.0.0.1:47821`, logs every `/hook` and `/statusline` body with a timestamp to `spike/logs/`; `/statusline` replies `SPIKE OK`.
- `spike/install_spike_hooks.py` — backs up `~/.claude/settings.json`, adds the hook command for all six events + status line; `--remove` restores the backup.
- `spike/glut_tray.py` — GLUT window + `pystray` icon on another thread: hide/show from tray, intercept the X button, send a toast.
- `spike/pyglet_tray.py` — same test with pyglet, only if GLUT fails.

**Verification gate (you run these by hand):**
- [ ] Terminal Claude Code: all six events logged with `session_id` and `hook_event_name`.
- [ ] VS Code Claude Code: same check.
- [ ] Claude desktop app, Code tab: same check. (Record yes/no — a "no" is a valid finding.)
- [ ] Status line JSON contains `rate_limits.five_hour` and `seven_day` on your plan. Note `resets_at` format.
- [ ] With the logger server stopped, a prompt in Claude Code is not slowed down (hook < 1 s, no error shown).
- [ ] Which shell runs hooks on Windows; `curl` found.
- [ ] GLUT: window can hide/show from tray, X button hides instead of quitting, toast appears. If not → pyglet result.
- [ ] `spike/FINDINGS.md` written; `tracker.md` Decisions updated (window layer, supported Claude Code surfaces).
- [ ] Spike hooks removed, original settings.json restored.

````markdown
# Phase 9 — Spike: verify assumptions (Work•Sleep•Repeat v2)

Read `docs/prd.md` §8 and every section marked **[VERIFY IN SPIKE]** in `docs/techspec.md` first.

This phase is a spike. Do NOT modify any existing module. Put everything in a new `spike/` folder.

## Build
1. `spike/logger_server.py`
   - `ThreadingHTTPServer` bound to `127.0.0.1:47821`.
   - `POST /hook` and `POST /statusline`: append `{time, path, body_json_or_raw}` as one JSON line to `spike/logs/events.jsonl`. `/hook` → 204. `/statusline` → 200 `SPIKE OK`.
   - `GET /health` → `ok`.
   - Print each event name / session id to the console.
2. `spike/install_spike_hooks.py`
   - Path: `%USERPROFILE%\.claude\settings.json` (create `{}` if missing).
   - First write a backup `settings.json.wsr-spike-backup-<timestamp>`.
   - Add hooks for SessionStart, UserPromptSubmit, PostToolUse (matcher `*`), Notification, Stop, SessionEnd using exactly the command in techspec §4.2, and the status line command in techspec §5.2.
   - Append to existing lists; never delete other entries. If a statusLine already exists, print it and ask y/n before replacing.
   - `--remove`: restore the newest spike backup.
   - To find the shell: add one extra UserPromptSubmit hook that runs `echo "$SHELL|$0|$(command -v curl)" >> <abs path>/spike/logs/shell.txt || true`.
3. `spike/glut_tray.py`
   - Minimal freeglut window (clear to a color) + `pystray` icon started on a background thread.
   - Tray menu: Show, Hide, Toast, Quit.
   - Use `glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION)` and `glutCloseFunc` to try to make X hide instead of exit; report exactly what happens.
   - Menu actions must be marshalled to the GLUT thread (e.g. a thread-safe queue read in the idle/timer func). Don't call GLUT from the tray thread.
4. `spike/pyglet_tray.py` — only if step 3 fails any check: same test with a pyglet window + legacy OpenGL immediate mode (draw one quad with `glBegin`) to confirm existing PyOpenGL calls would still work.
5. `spike/FINDINGS.md` — a table: check · result · evidence (paste the relevant log line) · decision.

## Verify (I will do these manually; give me a numbered checklist to follow)
- Terminal, VS Code, and desktop-app Code tab: each of the six events logged.
- Status line JSON contains rate_limits; record resets_at format.
- Logger stopped → Claude Code still responds normally; time the hook.
- Shell + curl path recorded.
- GLUT (or pyglet) hide/show/X/toast all work.
- `--remove` restores settings exactly (diff against backup).

Finish by summarising the findings and proposing the decisions to record in `docs/tracker.md`. Do not start Phase 10.
````

---

## Phase 10 — Local detection

**Goal:** real Claude Code activity on this PC moves *my* character. The toggle is gone. No network yet.

**Reads:** techspec §3, §4, §7, §8, §10 (partial), §11 · appflow §2–6, §15 · design §2 (toggle removal only).

**Builds:** `config.py` (new constants), `clock.py`, `state.py`, `activity.py`, `listener.py`, `claude_settings.py` (with CLI), `main.py` wiring, `panel.py` (toggle removed), `tests/test_activity.py`, `tests/test_claude_settings.py`.

**Verification gate:**
- [ ] `pytest` green (activity rules incl. idle timeout, stale cap, multiple sessions; settings merge/remove incl. invalid JSON, existing status line, idempotent install).
- [ ] `python claude_settings.py install` → prompt in Claude Code → my character goes to the desk within ~1 s.
- [ ] Claude finishes → still working; after `IDLE_TIMEOUT` (set to 60 s for the test) → back to bed.
- [ ] Two Claude Code windows: closing one doesn't send me to bed.
- [ ] App closed → Claude Code works normally.
- [ ] Second copy of the app exits and shows the first one's window.
- [ ] `--dev` keys 1/2 still drive my character; without `--dev` they do nothing.
- [ ] `python claude_settings.py remove` leaves settings.json identical to before install (diff).

````markdown
# Phase 10 — Local detection (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §3, §4, §7, §8, §11 and `docs/appflow.md` §2–6, §15. Also read `docs/tracker.md` → Decisions (from the Phase 9 spike) and follow them (window layer, shell, supported surfaces).

Diagnose before changing: open `main.py`, `panel.py`, `character.py` and describe in 5–10 lines how the toggle currently sets the character's target. Then make changes.

## Build
1. `config.py`: add `LISTEN_HOST="127.0.0.1"`, `LISTEN_PORT=47821`, `IDLE_TIMEOUT=600`, `TURN_STALE_CAP=1800`, `TZ="Asia/Dhaka"`. No magic numbers elsewhere.
2. `clock.py`: `now()`, `dhaka_today()`, `parse_ts(value)` accepting unix seconds or ISO strings, `fmt_duration(seconds)`.
3. `state.py`: `AppState` with one `threading.Lock`, and frozen `PersonView`, `UsageView`, `StateSnapshot` exactly as techspec §7. `snapshot()` returns a copy. Peer and usage can be placeholders for now.
4. `activity.py`: pure logic per techspec §4.4. `handle(event: dict, now)` and `tick(now) -> bool`. No threading, no I/O inside. Injected clock for tests.
5. `listener.py`: `ThreadingHTTPServer` on 127.0.0.1:47821 in a daemon thread. Routes per techspec §8 (`/statusline` can just reply `WSR` for now). Reject non-local clients, cap body at 256 KB, never raise into the server loop. `try_bind()` returns False if the port is taken; then `POST /show` and exit.
6. `claude_settings.py`: install/remove per techspec §4.3 merge rules, with a CLI: `python claude_settings.py install|remove|status`. Returns a result object (e.g. `existing_statusline`) so a UI can use it later. For now, if a foreign statusLine exists, `install` skips it and prints a warning.
7. `main.py`: start listener; each second call `activity.tick()` and write `me.working` into `AppState` (set `since` on change); each frame pass `snapshot()` to render modules. Add `--dev` (keys 1/2 inject fake events), `--port N` (dev only, for running two copies later) and `--idle N` (dev only, overrides IDLE_TIMEOUT).
8. `panel.py`: remove the toggle drawing and click handling. Leave its space empty for now. Keep everything else.
9. Tests: `tests/test_activity.py`, `tests/test_claude_settings.py` (use temp dirs; never touch the real settings file in tests).

Keep the layer rules in techspec §3. Render modules must not import state/activity/listener.

## Verify
Run `pytest`, then give me a numbered manual checklist covering every item in the Phase 10 gate in `docs/plan.md` (use IDLE_TIMEOUT=60 via a `--idle` dev override for the manual test). Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 11 — Supabase sync

**Goal:** both PCs see each other in real time. Time today persists and resets at Dhaka midnight. Offline doesn't break anything.

**Reads:** techspec §6, §10 (supabase fields), §12 · appflow §3, §5, §10–12 · design §2.1, §2.4, §3 (offline).

**Builds:** `supabase/schema.sql` (tables + functions + grants from techspec §6), `sync.py`, `userconfig.py` (read-only for now + `.env` fallback), time-today logic, panel status text + online dots + connection line, offline room overlay.

**Verification gate:**
- [ ] `schema.sql` runs clean on a fresh Supabase project; anon key can call the three RPCs and **cannot** select/update tables directly.
- [ ] Two copies on one PC (`--me rifat` default port, `--me samee --port 47822 --dev`): key 1 on Samee's copy → Rifat's copy shows Samee working within 3 s.
- [ ] Real prompt on PC A → PC B updates within 3 s (once both PCs have it).
- [ ] Wi-Fi off → "offline — retrying", no freeze, detection still works; Wi-Fi on → catches up.
- [ ] Kill peer app → after ~60 s shows "Samee is offline" + darker room.
- [ ] Restart app mid-day → time today continues. Change system date/time zone test or unit test for midnight Dhaka reset.
- [ ] Sleep PC 2+ min, wake → reconnects without restart.
- [ ] Unit tests for outbox latest-wins, backoff sequence, time-jump detection, midnight split.

````markdown
# Phase 11 — Supabase sync (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §6, §7, §10, §12 and `docs/appflow.md` §3, §5, §10–12, `docs/design.md` §2.1, §2.4, §3.

Diagnose first: check what the old `sync.py` stub contains and whether anything imports it. Report before replacing it.

## Build
1. `supabase/schema.sql`: tables, seed rows, the four functions (security definer, search_path=public), RLS on, grants/revokes exactly as techspec §6.3. Idempotent where practical (`create or replace`, `if not exists`).
2. `userconfig.py`: load `%APPDATA%\WorkSleepRepeat\config.json` if present, else `.env` (`SUPABASE_URL`, `SUPABASE_KEY`), `--me` overrides. Read-only this phase.
3. `sync.py`: daemon thread per techspec §6.4. `requests.Session`, 5 s timeout. Outbox with latest-wins per kind. Heartbeat every 20 s. Backoff 2→4→8→16→30. Time-jump (>30 s) → immediate reconnect + full re-push. Applies `wsr_get_state` into `AppState` under the lock, including `server_now` offset and peer online (heartbeat > 60 s = offline). Never touches OpenGL.
4. Startup: read own row; resume `today_seconds` if `today_date == dhaka_today()`.
5. Time today: accumulate while working (1 Hz in main), push on change and every 60 s while working, reset at Dhaka midnight (`clock.py` helper, unit tested).
6. `panel.py`: status text rules from design §2.1, online dots, bottom connection line. Reads the snapshot only.
7. Offline room: extra darkness on the peer's room + "OFFLINE" plaque when peer is offline (design §3). Reuse the lighting overlay.
8. `--offline` flag skips the sync thread entirely.
9. Tests: outbox, backoff, time-jump, midnight split, applying a sample `wsr_get_state` JSON to state. Mock HTTP; no real network in tests.

## Verify
`pytest`, then walk me through the Phase 11 gate in `docs/plan.md` as a numbered checklist, including how to create the Supabase project and run `schema.sql`, and a query to prove anon can't read tables directly. Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 12 — Usage limits + split

**Goal:** real 5h/weekly numbers from the status line, shared, with countdowns, staleness and split.

**Reads:** techspec §5, §6.2 (`wsr_report_usage`, `wsr_credit`, `wsr_get_state`) · appflow §7 · design §2.2, §6.

**Builds:** `usage.py`, `/statusline` handler, usage outbox kind, panel usage block + split row, status line reply text.

**Verification gate:**
- [ ] Claude Code status line shows the WSR line (design §6).
- [ ] Panel % matches Claude Code `/usage` within a few %.
- [ ] Peer PC shows the same numbers and "by Name".
- [ ] "updated N min ago" ticks; reset passing → "reset — no new data yet" (unit test with fake clock).
- [ ] `rate_limits` missing → no crash, last values kept.
- [ ] Split row appears after both have used Claude Code in the same 5h window; SQL test: stale report ignored, same-window increase credited, new window starts fresh, decreases ignored.
- [ ] Pushes throttled (not one per status line render).

````markdown
# Phase 12 — Usage limits + split (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §5, §6.2, §7 and `docs/appflow.md` §7, `docs/design.md` §2.2, §6.

## Build
1. `usage.py`: `parse_statusline(json) -> UsageReport | None` (each window optional; `resets_at` via `clock.parse_ts`). Formatting helpers: `% left`, bar color bucket, reset text (<24 h countdown, else Dhaka day+time), staleness label, status line text per design §6 (≤ ~70 chars).
2. `listener.py` `/statusline`: parse, store the latest report in state, reply with the status line text within 50 ms. Queue a usage push only if a value changed or 60 s passed.
3. `sync.py`: usage outbox kind → `wsr_report_usage(me, observed_at, …)`. Apply `usage` and `shares` from `wsr_get_state` to `UsageView`.
4. `panel.py`: usage block + split row exactly as design §2.2. Colors added to `config.py` per design §8.
5. `supabase/tests.sql`: a script that exercises `wsr_report_usage` cases (stale, same window increase, new window, decrease, missing window) and prints resulting rows. Must be safe to run (use a transaction + rollback).
6. Unit tests for parsing (both timestamp formats, missing windows, missing rate_limits), formatting, staleness/reset rules.

## Verify
`pytest` + run `supabase/tests.sql`, then give me the Phase 12 gate from `docs/plan.md` as a numbered manual checklist. Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 13 — Tray + alerts

**Goal:** the app lives in the tray, closing hides it, and it tells you things without you looking.

**Reads:** techspec §9 · appflow §5, §9, §13 · design §4, §5.

**Builds:** `tray.py` (icon from sprite grids, menu, notify), `alerts.py`, close-to-tray + ESC hide, `--tray`, alert on/off settings saved to config.

**Verification gate:**
- [ ] Tray icon changes with state (free / peer working / me working / conflict / offline); tooltip correct.
- [ ] X and ESC hide; tray "Open rooms" shows; Quit exits cleanly (no zombie threads, port released).
- [ ] Toasts: It's free, 5h 80% / 95%, weekly 75%, conflict (>30 s overlap). Each fires once, not repeatedly.
- [ ] Each alert can be turned off and stays off after restart.
- [ ] `--tray` starts hidden.
- [ ] Window hidden → CPU < ~2% (render loop throttled when hidden).
- [ ] Unit tests for `alerts.py` transitions and dedupe with scripted snapshots.

````markdown
# Phase 13 — Tray + alerts (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §9, `docs/appflow.md` §5, §9, §13, `docs/design.md` §4, §5, and the window-layer decision in `docs/tracker.md`.

## Build
1. `tray.py`: `pystray` on its own thread. Icons generated at runtime from new sprite grids (16/32 px) per design §4. Menu per techspec §9 (dibs item can be a disabled placeholder until Phase 14; integration items call `claude_settings`). All window actions go through a thread-safe queue consumed on the window thread — never call GLUT from the tray thread.
2. `alerts.py`: pure function `check(prev: StateSnapshot, cur: StateSnapshot, memory) -> list[Toast]` with dedupe memory per techspec §9 table. Copy from design §5.
3. `main.py`: run `alerts.check` at 1 Hz, send toasts via `tray.notify`. Close button + ESC → hide. `--tray` → start hidden. Throttle rendering when hidden (e.g. stop redisplay, keep a 1 Hz timer for tick/alerts).
4. `userconfig.py`: now also writes (alerts on/off). Atomic write (temp file + replace).
5. Tests: `tests/test_alerts.py` with scripted snapshot sequences for every row in techspec §9.

## Verify
`pytest`, then the Phase 13 gate from `docs/plan.md` as a numbered checklist (use `--dev` + `--port` second copy to trigger peer transitions). Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 14 — Dibs

**Goal:** "I want it next" without interrupting.

**Reads:** techspec §9 (dibs rules) · appflow §8 · design §2.3, §3, §5.

**Builds:** dibs state + push, panel button (clickable), tray item, bubble sprite, auto-clear rules, toasts.

**Verification gate:**
- [ ] Button only visible while peer is working.
- [ ] Call dibs → peer gets toast + sees bubble within 3 s.
- [ ] Peer stops → I get "Your turn" (not the plain "free" toast).
- [ ] I start working → dibs clears; cancel clears; 2 h expiry clears (unit test).
- [ ] Tray item mirrors panel button.

````markdown
# Phase 14 — Dibs (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §6.1 (`wants_next*`), §9, `docs/appflow.md` §8, `docs/design.md` §2.3, §3, §5.

## Build
1. State: `me.wants_next`, `wants_next_at`; push via `wsr_update_status`.
2. Rules: auto-clear when I start working, on cancel, or after `DIBS_EXPIRE` (config, 2 h). Button hidden when peer isn't working.
3. `panel.py`: clickable dibs button with the three states in design §2.3 (hit-testing in grid units, same style as the old toggle).
4. `sprites.py`: `BUBBLE_DIBS`; draw above the character who called dibs, 1 Hz bob.
5. `tray.py`: enable the dibs menu item.
6. `alerts.py`: "Samee wants it next"; "Your turn" replaces "Claude is free" when I had dibs.
7. Tests for rules and alerts.

## Verify
`pytest`, then the Phase 14 gate from `docs/plan.md` as a numbered checklist. Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 15 — Setup + autostart

**Goal:** Samee can set it up without editing any file.

**Reads:** techspec §4.3, §10, §11 · appflow §1, §14 · design §7.

**Builds:** `setup_ui.py`, `autostart.py`, `userconfig.py` write path, `--setup`, tray "Start with Windows" + integration items wired.

**Verification gate:**
- [ ] Fresh Windows user profile (or deleted config): dialog appears, Test connection works (✓ and a readable error).
- [ ] Existing foreign status line → asked keep/replace; both paths behave; backup exists.
- [ ] Hooks installed; dialog tells the user to restart open Claude Code sessions.
- [ ] Start with Windows on → after reboot app is in tray, window hidden. Off → gone from Run key.
- [ ] Tray Remove hooks → settings.json back to pre-install (diff). Reinstall works.
- [ ] Setup never runs while GLUT window exists (runs before it).

````markdown
# Phase 15 — Setup + autostart (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §4.3, §10, §11, `docs/appflow.md` §1, §14, `docs/design.md` §7.

## Build
1. `setup_ui.py`: tkinter dialog per design §7, run before the GLUT window is created and fully destroyed after. Validates inputs; Test connection calls `wsr_get_state` with a 5 s timeout.
2. Uses `claude_settings.install()`'s result to show the "existing status line" choice; on replace, save the old statusLine inside our backup so Remove can restore it.
3. `autostart.py`: HKCU `Software\Microsoft\Windows\CurrentVersion\Run` value `WorkSleepRepeat` = `"<exe or python main.py path>" --tray`. add/remove/is_enabled.
4. `userconfig.py`: full save (atomic). `--setup` forces the dialog.
5. Tray: Start with Windows toggle, Reinstall hooks, Remove hooks wired.
6. Tests: config round-trip, autostart command string building (mock winreg).

## Verify
`pytest`, then the Phase 15 gate from `docs/plan.md` as a numbered checklist. Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 16 — Package + cleanup

**Goal:** a build Samee can unzip and run. No Python needed.

**Builds:** `build.spec` / build script, bundled freeglut (per spike findings), app version constant, log file, tech-debt cleanup.

**Verification gate:**
- [ ] `build.bat` produces `dist/WorkSleepRepeat/` with `WorkSleepRepeat.exe`.
- [ ] Runs on a PC with **no Python installed** (Samee's, or a clean VM).
- [ ] No console window. Logs in `%APPDATA%\WorkSleepRepeat\wsr.log`, rotating.
- [ ] Autostart points at the exe, not python.
- [ ] Hook + status line commands work from the packaged app.
- [ ] FPS no longer printed to terminal (debug view only).
- [ ] Antivirus / SmartScreen behaviour noted in tracker (unsigned exe warning expected).

````markdown
# Phase 16 — Package + cleanup (Work•Sleep•Repeat v2)

Read first: `docs/tracker.md` (spike decision on how GLUT/freeglut is provided on Windows), `docs/techspec.md` §2, §11, §12.

Diagnose first: list every runtime file the app needs (DLLs, fonts if any) and how PyOpenGL finds freeglut on this machine. Report before writing the spec file.

## Build
1. `build.spec` + `build.bat`: PyInstaller `--onedir --windowed`, include freeglut DLL if needed, name `WorkSleepRepeat`, icon generated from the tray sprite at build time.
2. `config.py`: `APP_VERSION`. Sent as `app_version` in status updates.
3. Logging to `%APPDATA%\WorkSleepRepeat\wsr.log` via `RotatingFileHandler` (1 MB × 3). Replace prints.
4. Remove the terminal FPS print (debug view only). Resolve other items in tracker → Tech debt if small.
5. `README.md`: install steps for a friend (unzip → run → setup dialog), how to remove hooks, how to uninstall.

## Verify
Give me the Phase 16 gate from `docs/plan.md` as a numbered checklist, including testing on a machine without Python. Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 17 — 7-day trial

**Goal:** PRD §6 success criteria.

- Both install the packaged build and use it normally for 7 days.
- Every issue goes into `tracker.md` → Bugs with date, what happened, and the log snippet.
- Fix with the diagnose-first rule: reproduce → find cause → smallest fix → add a test.
- Done when: 7 days, no "are you on it?" messages, no unfixed crash/stuck status, usage within a few % of `/usage`.

Then decide the next step (browser extension for claude.ai, polish backlog, or opening it up — which needs the security redo first).
