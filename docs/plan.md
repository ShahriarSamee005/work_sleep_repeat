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
| 9 | Spike: verify assumptions | ✅ Done — see tracker | — |
| 10 | Local detection | hooks → character moves on one PC; toggle removed; **pyglet window** | 9 |
| 11 | Supabase sync | two PCs in sync; time today persists; offline handling | 10 |
| ~~12~~ | ~~Usage limits + split~~ — **DROPPED** (no status line on VS Code/desktop; tracker 2026-10-20) | — |
| 13 | Tray + alerts | tray icon/menu, close-to-tray, toasts (free, conflict) | 11 |
| 14 | Dibs | dibs button, bubble, toasts | 13 |
| 15 | Setup + autostart | first-run dialog, safe settings merge UI, start with Windows | 14 |
| 16 | Package + cleanup | PyInstaller build running on both PCs | 15 |
| 17 | 7-day trial | real daily use, bugs fixed, PRD §6 met | 16 |

> **Phase numbers kept as-is** though 12 is cut, so references stay stable. Phase 13 now depends on 11. Usage bars, split, status-line text and "limit" alerts are gone everywhere.

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

**Goal:** real Claude Code activity on this PC moves *my* character. The toggle is gone. No network yet. **Also: move the window from GLUT to pyglet** — Phase 9 found GLUT's X button quits instead of hiding, and we need hide-to-tray later.

**Reads:** techspec §3, §4, §7, §8, §11 · appflow §2–6, §15 · design §2 (toggle removal only) · tracker Decisions (pyglet, Git Bash shell, VS Code + desktop surfaces, usage dropped).

**Phase 10 runs in two steps with a gate between them.** The window swap touches everything the rooms draw, so prove it alone before adding detection on top.

**Step A — window swap:** move only the windowing/event/loop layer from GLUT to pyglet. All phase 0–8 drawing (immediate-mode `glBegin`, display lists) must keep working unchanged behind it. The spike's `pyglet_tray.py` already proved legacy GL renders under pyglet.

Step A gate:
- [ ] pyglet window opens; rooms render exactly as before (characters, lamp, lighting, panel).
- [ ] `D` debug, `G` grid, `ESC`, keys `1`/`2` all still work.
- [ ] Window **X** is routed through our own close handler (quits cleanly for now; becomes hide-to-tray in Phase 13), not pyglet's default.
- [ ] No GLUT import left in `main.py`; app runs with freeglut absent.

**Step B — detection:** wire hooks → my character, toggle removed.

Step B gate:
- [ ] `pytest` green (activity rules incl. idle timeout, stale cap, multiple sessions; settings merge/remove incl. invalid JSON, idempotent install).
- [ ] `python claude_settings.py install` → prompt in Claude Code (VS Code or desktop Code tab) → my character goes to the desk within ~1 s.
- [ ] Claude finishes → still working; after `IDLE_TIMEOUT` (60 s via `--idle` for the test) → back to bed.
- [ ] Two Claude Code sessions: closing one doesn't send me to bed.
- [ ] App closed → Claude Code works normally (this also covers the deferred NFR1 no-slowdown check).
- [ ] Second copy of the app exits and shows the first one's window.
- [ ] `--dev` keys 1/2 still drive my character; without `--dev` they do nothing.
- [ ] `python claude_settings.py remove` leaves settings.json identical to before install (diff).

````markdown
# Phase 10 — Local detection + pyglet window (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §3, §4, §7, §8, §11 and `docs/appflow.md` §2–6, §15. Also read `docs/tracker.md` → Decisions (Phase 9 spike) and FOLLOW them: window layer is **pyglet** (GLUT's X quits instead of hiding), hook shell is Git Bash, supported surfaces are VS Code + desktop Code tab (no terminal CLI, no status line, no usage feature).

Diagnose before changing: open `main.py`, `panel.py`, `character.py` and describe in 5–10 lines (a) how GLUT currently owns the window, main loop, timer and keyboard/mouse callbacks, and (b) how the toggle sets the character's target. Then make changes. Do NOT touch the drawing internals of pixel/room/character/lighting beyond what the window swap strictly requires.

## Step A — swap GLUT → pyglet (STOP and let me verify before Step B)
1. Replace only the window/loop/event layer in `main.py` with pyglet: a `pyglet.window.Window`, an `on_draw` handler, `pyglet.clock.schedule_interval` for the tick (replacing `glutTimerFunc`), and `on_key_press` / `on_mouse_press` (replacing GLUT callbacks). Keep the existing projection so the 240×96 grid at 6× maps identically (orthographic projection matching the old `gluOrtho2D`/viewport, y=0 at top).
2. All phase 0–8 drawing (immediate-mode `glBegin/glEnd`, display lists) must be called unchanged from `on_draw`. If display lists misbehave under pyglet's context, report it — do not rewrite the drawing.
3. Intercept window close via `on_close`: for now call `pyglet.app.exit()` cleanly, but route it through our own handler so Phase 13 can switch it to hide-to-tray. No pyglet default close.
4. Remove GLUT imports/usage from `main.py`; the app must run with freeglut absent.

## Step B — detection
5. `config.py`: add `LISTEN_HOST="127.0.0.1"`, `LISTEN_PORT=47821`, `IDLE_TIMEOUT=600`, `TURN_STALE_CAP=1800`, `TZ="Asia/Dhaka"`. No magic numbers elsewhere.
6. `clock.py`: `now()`, `dhaka_today()`, `parse_ts(value)` (accept unix seconds or ISO — keep dual-format; cheap), `fmt_duration(seconds)`.
7. `state.py`: `AppState` with one `threading.Lock`, frozen `PersonView`, `StateSnapshot` per techspec §7. `snapshot()` returns a copy. Peer can be a placeholder. Omit `UsageView` (usage dropped); if §7 lists it, skip it and say so in your reply.
8. `activity.py`: pure logic per techspec §4.4. `handle(event: dict, now)` and `tick(now) -> bool`. No threading, no I/O inside. Injected clock for tests.
9. `listener.py`: `ThreadingHTTPServer` on 127.0.0.1:47821 in a daemon thread. Routes per techspec §8, EXCEPT `/statusline`: no longer a feature — reply `204` and ignore the body (keep the route so a stale installed hook can't error). Reject non-local clients, cap body 256 KB, never raise into the server loop. `try_bind()` → False if port taken; then `POST /show` and exit.
10. `claude_settings.py`: install/remove per techspec §4.3 merge rules, CLI `install|remove|status`. **Install only the six hooks — NOT a statusLine** (dropped). If a foreign statusLine exists, leave it untouched. Returns a result object for the later setup UI.
11. `main.py`: start listener; each second call `activity.tick()` and write `me.working` into `AppState` (set `since` on change); each `on_draw` pass `snapshot()` to render modules. Add `--dev` (keys 1/2 inject fake events), `--port N` (dev only) and `--idle N` (dev only, overrides IDLE_TIMEOUT).
12. `panel.py`: remove the toggle drawing and click handling. Leave its space empty for now. Keep everything else.
13. Tests: `tests/test_activity.py`, `tests/test_claude_settings.py` (temp dirs; never touch the real settings file).

Keep the layer rules in techspec §3. Render modules must not import state/activity/listener.

## Verify
After Step A, STOP for my manual check (rooms render, D/G/ESC/1/2 work, X is ours). After Step B, run `pytest`, then give me a numbered manual checklist covering the Step B gate in `docs/plan.md` (use `--idle 60`). Update `docs/tracker.md`. Stop after this phase.
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

## ~~Phase 12 — Usage limits + split~~ — DROPPED (2026-10-20)

**Why:** usage %s come only from Claude Code's terminal status line. The user works in VS Code and the desktop Code tab, where the status line never runs (confirmed in the Phase 9 spike — zero `/statusline` events, and no `claude` CLI installed). A number that only refreshes in the terminal would sit stale in daily use, which is worse than showing nothing.

**What this removes everywhere:** usage bars, reset countdowns, usage "updated ago", the R/S usage split, the `/statusline` feature and its status-line reply text, the "limit" toasts (Phase 13), and the usage-related Supabase pieces (`wsr_usage`, `wsr_usage_share`, `wsr_report_usage`, `wsr_credit`, the `usage`/`shares` parts of `wsr_get_state`). The `/statusline` HTTP route stays but just returns 204, so any stale installed hook can't error.

**If it comes back later** (browser extension, or a future API that works outside the terminal): the full spec is preserved in techspec §5 / design §2.2 and this plan's git history. It would slot back in as its own phase.

---

## Phase 13 — Tray + alerts

**Goal:** the app lives in the tray, closing hides it, and it tells you things without you looking.

**Reads:** techspec §9 · appflow §5, §9, §13 · design §4, §5.

**Builds:** `tray.py` (icon from sprite grids, menu, notify), `alerts.py`, close-to-tray + ESC hide, `--tray`, alert on/off settings saved to config.

**Verification gate:**
- [ ] Tray icon changes with state (free / peer working / me working / conflict / offline); tooltip correct.
- [ ] X and ESC hide; tray "Open rooms" shows; Quit exits cleanly (no zombie threads, port released).
- [ ] Toasts: It's free, conflict (>30 s overlap). Each fires once, not repeatedly. (**No limit toasts — usage dropped.**)
- [ ] Each alert can be turned off and stays off after restart.
- [ ] `--tray` starts hidden.
- [ ] Window hidden → CPU < ~2% (render loop throttled when hidden).
- [ ] Unit tests for `alerts.py` transitions and dedupe with scripted snapshots.

````markdown
# Phase 13 — Tray + alerts (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §9, `docs/appflow.md` §5, §9, §13, `docs/design.md` §4, §5, and `docs/tracker.md` Decisions. Note: usage is dropped, so **skip the "limit" alert rows** in techspec §9 and design §5. Window layer is pyglet (Phase 10).

## Build
1. `tray.py`: `pystray` on its own thread. Icons generated at runtime from new sprite grids (16/32 px) per design §4. Menu per techspec §9 — but drop any usage/limit menu items; dibs item is a disabled placeholder until Phase 14; integration items call `claude_settings`. All window actions go through a thread-safe queue consumed on the pyglet window thread — never touch the window from the tray thread.
2. `alerts.py`: pure function `check(prev: StateSnapshot, cur: StateSnapshot, memory) -> list[Toast]` with dedupe memory. Implement only the **It's free** and **Conflict** rows (plus dibs rows arrive in Phase 14). Do NOT implement the 5h/weekly limit toasts. Copy wording from design §5.
3. `main.py`: run `alerts.check` at 1 Hz, send toasts via `tray.notify`. Make the Phase 10 `on_close` handler now **hide to tray** instead of exit; ESC also hides. `--tray` → start hidden. Throttle rendering when hidden (stop redraw, keep a 1 Hz timer for tick/alerts).
4. `userconfig.py`: now also writes (alerts on/off). Atomic write (temp file + replace).
5. Tests: `tests/test_alerts.py` with scripted snapshot sequences for the free + conflict rows.

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

### Phase 14b — Dibs percentage + debug cleanup (2026-10-22)

**Step A:** removed lab debug view (D/G keys, grid overlay, debug ray coloring, Bezier viz, clip rect, FPS counter, `--debug` flag).

**Step B:** added `wants_next_pct` (0–100, step 10, default 50) — slider on dibs card, Supabase column + RPC, peer display ("keep NN% for me"), clear rules. Diagonal ray lines (`draw_rays`) removed from the normal render path; glow untouched.

All 126 tests pass. See `tracker.md` for full results.

---

## Phase 15 — Setup + autostart

**Goal:** Samee can set it up without editing any file.

**Reads:** techspec §4.3, §10, §11 · appflow §1, §14 · design §7.

**Builds:** `setup_ui.py`, `autostart.py`, `userconfig.py` write path, `--setup`, tray "Start with Windows" + integration items wired.

**Verification gate:**
- [ ] Fresh Windows user profile (or deleted config): dialog appears, Test connection works (✓ and a readable error).
- [ ] Hooks installed; dialog tells the user to restart open Claude Code sessions.
- [ ] Start with Windows on → after reboot app is in tray, window hidden. Off → gone from Run key.
- [ ] Tray Remove hooks → settings.json back to pre-install (diff). Reinstall works.
- [ ] Setup never runs while the pyglet window exists (runs before it).

````markdown
# Phase 15 — Setup + autostart (Work•Sleep•Repeat v2)

Read first: `docs/techspec.md` §4.3, §10, §11, `docs/appflow.md` §1, §14, `docs/design.md` §7.

## Build
1. `setup_ui.py`: tkinter dialog per design §7, run before the pyglet window is created and fully destroyed after. Validates inputs; Test connection calls `wsr_get_state` with a 5 s timeout.
2. Install the six hooks via `claude_settings.install()`. No status line is installed (usage dropped). Any existing statusLine is left untouched.
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

**Builds:** `build.spec` / build script, bundled **pyglet** runtime deps (no freeglut — window layer is pyglet), app version constant, log file, tech-debt cleanup.

**Verification gate:**
- [ ] `build.bat` produces `dist/WorkSleepRepeat/` with `WorkSleepRepeat.exe`.
- [ ] Runs on a PC with **no Python installed** (Samee's, or a clean VM).
- [ ] No console window. Logs in `%APPDATA%\WorkSleepRepeat\wsr.log`, rotating.
- [ ] Autostart points at the exe, not python.
- [ ] Hook commands work from the packaged app.
- [ ] FPS no longer printed to terminal (debug view only).
- [ ] Antivirus / SmartScreen behaviour noted in tracker (unsigned exe warning expected).

````markdown
# Phase 16 — Package + cleanup (Work•Sleep•Repeat v2)

Read first: `docs/tracker.md` (window layer = pyglet), `docs/techspec.md` §2, §11.

Diagnose first: list every runtime file the app needs (pyglet's DLLs/shaders, fonts if any). Report before writing the spec file.

## Build
1. `build.spec` + `build.bat`: PyInstaller `--onedir --windowed`, include pyglet's bundled deps (hidden imports / data as needed), name `WorkSleepRepeat`, icon generated from the tray sprite at build time.
2. `config.py`: `APP_VERSION`. Sent as `app_version` in status updates.
3. Logging to `%APPDATA%\WorkSleepRepeat\wsr.log` via `RotatingFileHandler` (1 MB × 3). Replace prints.
4. Remove the terminal FPS print (debug view only). Resolve other items in tracker → Tech debt if small.
5. `README.md`: install steps for a friend (unzip → run → setup dialog), how to remove hooks, how to uninstall.

## Verify
Give me the Phase 16 gate from `docs/plan.md` as a numbered checklist, including testing on a machine without Python. Update `docs/tracker.md`. Stop after this phase.
````

---

## Phase 16b — Character-head icon + Zoro/Sanji room skins (2026-10-22)

**Step A:** Replaced lamp/moon tray icon with character head sprite (`TRAY_HEAD` 16×16). Same head used for taskbar (`window.set_icon`), exe icon, and all tray states (with overlay dots for status).

**Step B:** Added hair (`H`) and clothes (`C`/`c`) cells to all character sprite grids. Per-person color dicts: Samee = Zoro (green hair, teal clothes), Rifat = Sanji (blond hair, dark suit). Shape/animation unchanged.

---

## Phase 17 — 7-day trial

**Goal:** PRD §6 success criteria.

- Both install the packaged build and use it normally for 7 days.
- Every issue goes into `tracker.md` → Bugs with date, what happened, and the log snippet.
- Fix with the diagnose-first rule: reproduce → find cause → smallest fix → add a test.
- Done when: 7 days, no "are you on it?" messages, no unfixed crash/stuck status, usage within a few % of `/usage`.

Then decide the next step (browser extension for claude.ai, polish backlog, or opening it up — which needs the security redo first).
