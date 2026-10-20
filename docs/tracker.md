# Work•Sleep•Repeat — Tracker (v2)

> Update at the end of every phase: status, gate results, decisions, bugs. Newest entries at the top of each log.

**Current phase:** 10 — Local detection + pyglet window (✅ built, awaiting manual gate) → next: Phase 11
**Last updated:** 2026-10-20

---

## Phase status

| Phase | Name | Status | Gate passed | Commit |
|---|---|---|---|---|
| 0–8 | Lab build (graphics, animation, lighting, panel) | ✅ Done | ✅ | (see git log) |
| 9 | Spike: verify assumptions | ✅ Done | ✅ | (spike/) |
| 10 | Local detection + pyglet window | 🟨 Built, manual gate pending | Step A ✅ | `04914fc` (Step A) |
| 11 | Supabase sync | ⬜ Not started | — | — |
| 12 | ~~Usage limits + split~~ **Dropped** | ⬛ Cut | — | — |
| 13 | Tray + alerts | ⬜ Not started | — | — |
| 14 | Dibs | ⬜ Not started | — | — |
| 15 | Setup + autostart | ⬜ Not started | — | — |
| 16 | Package + cleanup | ⬜ Not started | — | — |
| 17 | 7-day trial | ⬜ Not started | — | — |

Legend: ⬜ not started · 🟨 in progress · 🟥 blocked · ✅ done

---

## Phase 10 results (2026-10-20)

**Step A — pyglet window swap (commit `04914fc`):** gate passed.

| Check | Result |
|---|---|
| pyglet window opens, rooms render as before | ✅ Four snapshots (idle / working / both / debug) **byte-identical** to the GLUT build |
| `D` / `G` / `ESC` / keys `1`,`2` work | ✅ Verified by dispatching the real handlers |
| Window **X** routed through our own handler | ✅ `on_close` → `request_close()`; loop returns, window not destroyed (`has_exit=False`) |
| No GLUT import in `main.py`; runs with freeglut absent | ✅ Ran at 60 FPS with all six `freeglut*.dll` moved out of `OpenGL/DLLS` |
| GL context | 4.6 Compatibility Profile (explicit `Config(major_version=2, minor_version=1)`); immediate mode + display lists fine |

**Step B — detection:** built; `pytest` green (34 tests). End-to-end proven with a real app process and real POSTs; the manual gate in `docs/plan.md` is still to run.

| Check | Result |
|---|---|
| `pytest` | ✅ 34 passed (`test_activity.py` 13, `test_claude_settings.py` 16, `test_character.py` 5 + 1) |
| Hook → character | ✅ `POST /hook` `UserPromptSubmit` → `working -> True` within a frame; reply 204 in 12–28 ms |
| Long run keep-alive | ✅ `PostToolUse` every 2 s with `--idle 5` never flipped to not-working |
| Two sessions | ✅ Closing one kept working; closing both → off after idle |
| Stop → idle timeout | ✅ Still working 2 s after `Stop`, back to bed after the idle window |
| Single instance | ✅ Second copy: "already running — showed its window", exit 0 (needs `allow_reuse_address = False` on Windows) |
| App closed → Claude Code unaffected | ✅ Connection refused in ~54 ms, so `curl -m 1 … \|\| true` returns at once (covers NFR1) |
| Routes | ✅ `/health` 200 `ok`; `/statusline` 204 (ignored); unknown 404; malformed body 204 + logged once |
| `--dev` keys | ✅ `1`/`2` inject fake `UserPromptSubmit`/`SessionEnd`; without `--dev` they do nothing; `--port`/`--idle` refused without `--dev` |
| Hooks installed fresh | ✅ `claude_settings.py install` wrote all six events; `permissions` / `effortLevel` untouched, no statusLine. Backup: `settings.json.wsr-backup-20261020-230647` |

---

## Phase 9 results (2026-10-20)

| Check | Result |
|---|---|
| Terminal Claude Code: six events | ⚠️ Not tested — `claude` CLI not installed on this PC (`command not found`) |
| VS Code Claude Code: events | ✅ UserPromptSubmit, PostToolUse, Stop, SessionEnd all logged |
| Desktop app Code tab: events | ✅ SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd all logged |
| Status line `rate_limits` | ❌ Never fired — status line is a terminal-CLI feature; no terminal CLI here, so no surface triggers it |
| `resets_at` format | Unknown — never observed (no status line on this setup) |
| Hook with app closed: no slowdown | ⏭️ Deferred to Phase 10 (closed port rejects instantly; low risk) |
| Hook shell / curl path | ✅ Git Bash (MINGW64); curl at `/mingw64/bin/curl` |
| Window: GLUT hide/show/toast | ✅ Show / Hide / Toast all worked via pystray |
| Window: GLUT X button | ❌ X **quits** the process (not hide) — needs pyglet |
| `spike/FINDINGS.md` written | ✅ |
| Spike hooks installed | ✅ Removed before Phase 10 (backups `settings.json.pre-remove-*`); Phase 10 installed its own fresh set via `claude_settings.py` |

**Bottom line:** detection works in both surfaces actually used (VS Code + desktop). Usage limits can't be auto-read on this setup → feature dropped. Window layer moves to pyglet.

---

## Open questions

| ID | Question | Answer | Answered in |
|---|---|---|---|
| OQ1 | Do hooks work in terminal / VS Code / desktop Code tab? | **VS Code ✅, desktop Code tab ✅.** Terminal not tested (no CLI). Hooks are reliable in both surfaces used. | Phase 9 |
| OQ2 | GLUT or pyglet for the window layer? | **pyglet.** GLUT's X button quits instead of hiding to tray. | Phase 9 |
| OQ3 | Does `rate_limits` appear, and in what format? | **Not available on this setup.** Status line is terminal-only; no terminal CLI here. Usage feature dropped. | Phase 9 |
| OQ4 | How is freeglut provided on Windows (for packaging)? | **Moot — freeglut is gone.** Phase 10 Step A removed the last GLUT call (fonts included) and the app was verified running with every `freeglut*.dll` deleted. Phase 16 only has to bundle pyglet's deps. | Phase 9 / 10 / 16 |

---

## Decisions log

| Date | Decision | Why | Docs changed |
|---|---|---|---|
| 2026-09-29 | Windows-only tray app, Python + PyOpenGL kept | Reuse phases 0–8; only two users | prd, techspec |
| 2026-09-29 | Manual toggle removed; detection via Claude Code hooks | Toggle was the weakest part | prd, techspec, design |
| 2026-09-29 | Usage limits from Claude Code status line JSON only; no credentials file, no undocumented endpoints | Official, safe | techspec §5 |
| 2026-09-29 | Supabase access via RPC functions only, RLS on tables | Small surface, server time for heartbeats | techspec §6 |
| 2026-09-29 | Usage split computed server-side in `wsr_report_usage` | Atomic; no race between two PCs | techspec §6.2 |
| 2026-09-29 | History feature dropped | Out of scope by choice | prd §4 |
| 2026-09-29 | Idle timeout 10 min, stale-turn cap 30 min | Starting values; tune in trial | techspec §4.4 |
| 2026-10-20 | Window layer: **pyglet**, not GLUT | GLUT X button quits instead of hiding to tray | techspec §2, plan Ph10 |
| 2026-10-20 | **Usage limits (F3/F4) dropped** | Status line is terminal-CLI only; user uses VS Code + desktop, so numbers can't stay fresh. Stale usage is worse than none. | prd §4, techspec §5, design, appflow, plan |
| 2026-10-20 | Detection confirmed in VS Code + desktop Code tab | Phase 9 spike logged full hook cycle in both | prd §4, techspec §4 |
| 2026-10-20 | No terminal `claude` CLI on user's PC | Accepted; nothing in plan requires it now that usage is dropped | — |
| 2026-10-20 | Bitmap fonts extracted from freeglut into `font.py` | freeglut **exits the process** if `glutBitmapWidth`/`glutBitmapCharacter` run without `glutInit`, so GLUT-free meant GLUT-free text too. `tools/extract_font.py` captured the real 8x13/9x15 glyphs, so text is pixel-identical | techspec §3 (new render module) |
| 2026-10-20 | `listener` sets `allow_reuse_address = False` | On Windows SO_REUSEADDR lets a second process bind the same port, which would break "port bind = single-instance lock" | techspec §8 |
| 2026-10-20 | Hook events reach `activity` through a `queue` | `activity` stays pure (no threads/locks); the listener thread only enqueues, the main loop drains each frame | techspec §3 |
| 2026-10-20 | `panel.draw_panel` keeps its dict argument | `main` builds the dict from `state.snapshot()` each frame, so the lock rule in §7 holds without a panel rewrite; the panel takes the snapshot itself when it grows dibs/online dots (Phase 14) | — |
| 2026-10-20 | No new `TZ` constant | `config.TIMEZONE` already held `"Asia/Dhaka"`; `clock.py` uses it with the fixed UTC+6 offset, so no `tzdata` dependency on Windows | — |

---

## Bugs

| Date | Phase | What happened | Cause | Fix / commit | Status |
|---|---|---|---|---|---|
| | | | | | |

---

## Tech debt

| Item | From | Plan |
|---|---|---|
| FPS counter prints to terminal | Lab | Now debug-view only (appflow §15); remove in Phase 16 |
| `Character` keeps its own `today_seconds` / `since` | Phase 10 | `AppState` is the truth now and the panel reads the snapshot; the character's copies are unused. Strip in Phase 11 when sync owns the counter |
| `clock.fmt_duration` duplicates `panel.format_time` | Phase 10 | Render modules may not import layer 1 (techspec §3). Keep both in step; revisit if the panel ever takes formatted strings |
| `tests/test_character.py` uses soft `check()` asserts | Lab | A final `test_no_check_failures` now makes pytest see them; convert to plain asserts if the file is touched again |
| `config.TOGGLE_*` constants unused | Phase 10 | Toggle removed; Phase 14's dibs button reuses that space and those boxes |
| `hex_to_rgb` memoized | Lab | Revisit only if palette grows |
| Debug view redraws unclipped rays (~40 fps in debug) | Lab | Leave; dev tool only |
| Untidy commit labels phases 5–6 (`dbe9700`…) | Lab | Leave as is |
| Shared anon key = anyone with it can change status | v2 design | Must fix before anyone beyond Rifat + Samee |

---

## Tuning notes (fill during trial)

| Setting | Start | Changed to | Why |
|---|---|---|---|
| IDLE_TIMEOUT | 600 s | | |
| TURN_STALE_CAP | 1800 s | | |
| POLL_INTERVAL | 2 s | | |
| PEER_OFFLINE_AFTER | 60 s | | |


---

## Backlog (not scheduled)

- **Usage limits (F3/F4)** — revisit when there's a source that works in VS Code/desktop (browser extension reading claude.ai, or a future Anthropic API). Spec kept in techspec §5 / design §2.2 history for when it returns.
- Browser extension to detect claude.ai web chat
- More walking frames
- Room window that follows real time of day
- More than two users
- Sound cues (off by default)
- Security redo (per-user keys / auth) before opening up
