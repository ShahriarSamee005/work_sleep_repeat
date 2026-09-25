# Work•Sleep•Repeat — Tracker

Status key: ⬜ not started · 🟨 in progress · ✅ done · ⛔ blocked

## Overview

| Phase | Name | Status | Gate passed | Date |
|---|---|---|---|---|
| 0 | Project setup | ✅ | ✅ | 2026-09-25 |
| 1 | Grid and pixel helpers | ✅ | ✅ | 2026-09-25 |
| 2 | One static room | ✅ | ✅ | 2026-09-25 |
| 3 | Two rooms + display lists | ⬜ | ⬜ | |
| 4 | Hand-written algorithms | ⬜ | ⬜ | |
| 5 | Working state (no animation) | ⬜ | ⬜ | |
| 6 | Animation | ⬜ | ⬜ | |
| 7 | Lighting + debug view | ⬜ | ⬜ | |
| 8 | Panel | ⬜ | ⬜ | |
| 9 | Real-time sync | ⬜ | ⬜ | |
| 10 | Finish and prepare | ⬜ | ⬜ | |

---

## Phase checklists

### Phase 0: Project setup
- [x] Folder structure created (modules at root, one-line docstring each)
- [x] requirements.txt, .env.example, .gitignore
- [x] `--me` and `--offline` arguments
- [x] Window opens, ESC quits (ESC close confirmed manually 2026-09-25)
- [ ] GitHub repo created and first commit pushed
- [ ] **Understood:** glutInit, display mode, main loop

### Phase 1: Grid and pixel helpers
- [x] config.py has all constants and colors (§5 object positions deferred to Phase 2)
- [x] pixel.py functions done (7 functions; hex_to_rgb moved out of main.py)
- [x] Red box top-left, blue box bottom-right (verified by pixel check + screenshot)
- [x] Sprite draws the right way up (verified: round top, eyes row 4, shadow on right, not mirrored)
- [ ] **Understood:** why the y axis is flipped
- Gate passed 2026-09-25. Bullet "•" fixed inside draw_text (draws a small square + advances one char width).

### Phase 2: One static room
- [x] Wall, baseboard, floor planks
- [x] Poster, plant
- [x] Bed with sleeping head
- [x] Desk, monitor (off), keyboard, lamp (off), mug, books
- [x] Chair, rug
- [x] Matches the idle mockup (pixel-checked bed/desk/rug/floor; layout verified)
- [ ] **Changed by hand:** one object's color and position
- Gate passed 2026-09-25. Rug stitch dots use the rug's dark edge color (matches mockup). No §5 coordinate changed; WALK_A sprite width normalized 10→9 (see Discoveries).

### Phase 3: Two rooms + display lists
- [ ] Rifat's room mirrored with glScalef(-1, 1, 1)
- [ ] Different rug colors
- [ ] Divider
- [ ] Labels readable
- [ ] Display lists in use
- [ ] FPS close to 60
- [ ] **Understood:** why translate by 97 + 93

### Phase 4: Hand-written algorithms
- [ ] bresenham_line
- [ ] cubic_bezier, bezier_points, ease_in_out
- [ ] boundary_fill (stack-based)
- [ ] scanline_circle
- [ ] compute_outcode, cohen_sutherland
- [ ] Self-test passes
- [ ] Messy blanket built with line + fill
- [ ] **Can explain every line of every algorithm**

### Phase 5: Working state
- [ ] Sitting pose and arms
- [ ] Typing animation
- [ ] Screen on with code lines
- [ ] Lamp shade on
- [ ] Keys 1/2 switch instantly

### Phase 6: Animation
- [ ] Character class with 8 states
- [ ] Bezier walk with easing
- [ ] Walk frames + bob + sit squash
- [ ] Devices turn on/off in order
- [ ] Reverse mid-walk works
- [ ] Blanket becomes neat only after lying down
- [ ] **Understood:** Bezier formula and easing

### Phase 7: Lighting + debug
- [ ] Darkness overlay (idle 0.40, working 0.30)
- [ ] Glow circles (scanline circle, clipped)
- [ ] Rays (Cohen-Sutherland)
- [ ] Emissive parts on top
- [ ] Debug view (D) and grid (G)
- [ ] Light never crosses the divider

### Phase 8: Panel
- [ ] Moon/sun icon
- [ ] Status lines
- [ ] Toggle drawn and clickable
- [ ] Time cards with live counter
- [ ] Conflict warning

### Phase 9: Sync
- [ ] Supabase table + rows + policy
- [ ] Polling thread with lock
- [ ] Background PATCH on toggle
- [ ] Offline indicator
- [ ] Two instances stay in sync
- [ ] Window never freezes

### Phase 10: Finish
- [ ] All Bangla comments present
- [ ] README + screenshots
- [ ] Part 1 page written
- [ ] Part 3 reflection written
- [ ] Demo rehearsed (under 2 min)
- [ ] All live edits practiced

---

## Bug log → reflection Q1 "Where did you get most stuck?"

Write it down while it's fresh. The best reflection answers come from here.

| Date | Phase | What went wrong | What caused it | How I fixed it |
|---|---|---|---|---|
| 2026-09-25 | 0 | `glutCreateWindow` crashed: `'str' object cannot be interpreted as ctypes.c_char_p` | PyOpenGL 3.1.10 passes the title straight to a C `c_char_p`, which needs `bytes`, not a Python `str` | Encoded the title with `.encode("utf-8")` before passing it to `glutCreateWindow` |

## Lessons → reflection Q2 "What did this teach you that theory couldn't?"

- 

## Discoveries → viva bonus "I discovered something never covered before…"

Candidates to watch for:
- Why a recursive fill crashes in Python (recursion limit) and a stack fixes it
- Why mirroring needs an extra translate, not just `glScalef(-1, 1, 1)`
- Why text must be drawn outside the mirrored matrix
- Why network calls in the draw loop freeze the window (threads)
- How easing makes linear motion look alive

| Date | What I discovered | How I'd explain it in one sentence |
|---|---|---|
| 2026-09-25 | GLUT bitmap fonts only support char codes 1–255; "•" (U+2022) renders nothing and advances 0 px | Old bitmap fonts carry a 256-glyph table, so any Unicode character above 255 is silently skipped. |
| 2026-09-25 | `glutCreateWindow` needs a `bytes` title, not a `str` (else `ctypes.ArgumentError`) | PyOpenGL passes the title straight to a C `char*`, which only accepts bytes, so the string must be `.encode()`d first. |
| 2026-09-25 | design §7 WALK_A leg rows were 10 px wide while STAND is 9 px | The design doc had a stray trailing dot; I trimmed it so the walk frame lines up with the standing sprite. |

## Future ideas → reflection Q4 "One more week?"

- Queue button: "I want it next"
- Walking animation with more frames
- Day/night window that follows the real clock
- More than two users
- Automatic detection of AI usage instead of a manual toggle

---

## Viva prep

### 2-minute demo script
1. (15 s) The problem: we share one Pro AI account and keep asking each other.
2. (15 s) Show both rooms idle: "Both asleep = the account is free."
3. (30 s) Click the toggle: get up, curved walk, sit, monitor, lamp.
4. (20 s) Show the second laptop updating (or use key `2` if offline).
5. (20 s) Press `D`: Bezier curve and control points, clipped vs unclipped rays.
6. (20 s) Toggle both to show the conflict warning.

### Must-answer questions
- [ ] Explain the project to a non-technical person
- [ ] Walk through `cubic_bezier`
- [ ] Walk through `cohen_sutherland`
- [ ] Walk through `boundary_fill`
- [ ] How the room is mirrored
- [ ] What the state machine does
- [ ] Weakest part (security of the shared key / manual toggle)
- [ ] "Delete this line, what happens?" for any line in algorithms.py
