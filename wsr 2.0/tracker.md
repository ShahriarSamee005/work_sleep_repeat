# Work•Sleep•Repeat — Tracker (v2)

> Update at the end of every phase: status, gate results, decisions, bugs. Newest entries at the top of each log.

**Current phase:** 9 — Spike
**Last updated:** 2026-09-29

---

## Phase status

| Phase | Name | Status | Gate passed | Commit |
|---|---|---|---|---|
| 0–8 | Lab build (graphics, animation, lighting, panel) | ✅ Done | ✅ | (see git log) |
| 9 | Spike: verify assumptions | ⬜ Not started | — | — |
| 10 | Local detection | ⬜ Not started | — | — |
| 11 | Supabase sync | ⬜ Not started | — | — |
| 12 | Usage limits + split | ⬜ Not started | — | — |
| 13 | Tray + alerts | ⬜ Not started | — | — |
| 14 | Dibs | ⬜ Not started | — | — |
| 15 | Setup + autostart | ⬜ Not started | — | — |
| 16 | Package + cleanup | ⬜ Not started | — | — |
| 17 | 7-day trial | ⬜ Not started | — | — |

Legend: ⬜ not started · 🟨 in progress · 🟥 blocked · ✅ done

---

## Current phase checklist — Phase 9

Copy the gate from `plan.md` here while working, tick as you go.

- [ ] Terminal Claude Code: six events logged
- [ ] VS Code Claude Code: six events logged
- [ ] Desktop app Code tab: six events logged (yes/no)
- [ ] Status line has `rate_limits` (5h + 7d); `resets_at` format: ______
- [ ] Hook with app closed: no slowdown (< 1 s)
- [ ] Hook shell: ______ · curl path: ______
- [ ] GLUT hide/show/X/toast OK — or pyglet result
- [ ] `spike/FINDINGS.md` written
- [ ] Spike hooks removed, settings restored

---

## Open questions

| ID | Question | Answer | Answered in |
|---|---|---|---|
| OQ1 | Do hooks + status line work in terminal / VS Code / desktop app Code tab? | | Phase 9 |
| OQ2 | GLUT or pyglet for the window layer? | | Phase 9 |
| OQ3 | Does `rate_limits` appear on our plan, and in what `resets_at` format? | | Phase 9 |
| OQ4 | How is freeglut provided on Windows today (for packaging)? | | Phase 9 / 16 |

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

---

## Bugs

| Date | Phase | What happened | Cause | Fix / commit | Status |
|---|---|---|---|---|---|
| | | | | | |

---

## Tech debt

| Item | From | Plan |
|---|---|---|
| FPS counter prints to terminal | Lab | Remove in Phase 16 |
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
| Limit alert thresholds | 5h 80/95, week 75 | | |

---

## Backlog (not scheduled)

- Browser extension to detect claude.ai web chat
- More walking frames
- Room window that follows real time of day
- More than two users
- Sound cues (off by default)
- Security redo (per-user keys / auth) before opening up
