# Work•Sleep•Repeat — Build Plan

## How to use this plan

1. Put all six `.md` files in a `docs/` folder inside the project.
2. Do the phases **in order**. Paste each phase's prompt into Claude Code.
3. Don't start the next phase until the **gate** passes.
4. After each phase, do the **"Understand it"** step. You have to explain and change this code live in the viva, so this step is not optional.
5. Tick off tasks in `tracker.md`, and write down bugs and discoveries there as they happen. They become your reflection report.

**Standing rule for every prompt:** Claude Code must read `docs/design.md` and `docs/techspec.md` first, and follow the Bangla comment style from techspec section 7.

---

## Phase 0: Project setup

**Goal:** empty project that opens a window.

```text
Read docs/prd.md, docs/techspec.md, docs/design.md, docs/appflow.md.

Set up the project "work-sleep-repeat" with the exact folder structure from techspec section 2.
- Create empty modules with a one-line docstring each.
- Create requirements.txt (PyOpenGL, PyOpenGL_accelerate, requests, python-dotenv).
- Create .env.example with SUPABASE_URL and SUPABASE_KEY, and a .gitignore that ignores .env and __pycache__.
- In main.py, parse --me (samee|rifat) and --offline with argparse, then open a 1440x576 GLUT window
  titled "Work•Sleep•Repeat" that clears to #231c2b. ESC quits.
- Do NOT implement anything else yet.

Verification:
1. Run `python main.py --me rifat`. A dark window opens and ESC closes it.
2. Run `python main.py` with no --me. It prints usage and exits.
3. If glutInit fails with NullFunctionError, stop and explain how to install freeglut on Windows. Do not work around it.
```

**Gate:** window opens and closes on ESC.
**Understand it:** what do `glutInit`, `glutInitDisplayMode`, and `glutMainLoop` do?

---

## Phase 1: Grid and pixel helpers

**Goal:** a 240 × 96 pixel grid with y = 0 at the top.

```text
Read docs/techspec.md sections 3.1, 4.1, 4.2 and docs/design.md sections 3 and 4.

1. Fill config.py with every constant from techspec 4.1 and every color from design.md section 4.
   Use the exact names from design.md.
2. Implement every function in pixel.py from techspec 4.2.
3. In main.py, set gluOrtho2D(0, 240, 96, 0) and enable alpha blending.
4. Temporary test in display(): red box at (0,0,10,10), blue box at (230,86,10,10),
   and a sprite test drawing HEAD_SLEEP at (50,40) (add HEAD_SLEEP to sprites.py from design.md section 7).
5. Every function gets the Bangla comment block from techspec section 7.

Verification:
1. The red box is top-LEFT, the blue box is bottom-RIGHT.
2. The head sprite is not upside down or mirrored.
3. Pixels are crisp squares, 6x6 screen pixels each.
Report what you checked.
```

**Gate:** boxes in the right corners, sprite the right way up.
**Understand it:** why does `gluOrtho2D(0, 240, 96, 0)` flip the y axis? What breaks if you change it to `(0, 240, 0, 96)`?

---

## Phase 2: One static room (idle)

**Goal:** Samee's room, idle, matching the mockup.

```text
Read docs/design.md sections 5 and 7 and docs/techspec.md section 4.5.

1. Add every sprite from design.md section 7 to sprites.py.
2. Implement room.py: draw_wall_and_floor, draw_decor, draw_bed(messy=False), draw_desk, draw_chair,
   draw_rug, draw_screen(on=False), draw_lamp_shade(on=False, warn=False).
   Use EXACTLY the coordinates in design.md section 5, read from config.py.
   All coordinates are room-local.
3. In main.py, draw Samee's room with glTranslatef(2, 2, 0) inside glPushMatrix/glPopMatrix,
   and draw the sleeping head at its bed position.
4. Draw the 2-pixel outer frame.
5. Do NOT build display lists yet. Do NOT do lighting yet.

Verification:
1. Compare with the left room of the Idle mockup: bed on the left, desk center-right against the wall,
   chair below the desk, rug in the lower middle, plant in the right corner, poster on the wall.
2. The floor has plank lines and seams, not a flat color.
3. List any coordinate you had to change from design.md and why.
```

**Gate:** looks like the left room of the idle mockup (without the dark tint).
**Understand it:** open `room.py`, pick one object, and change its color and position yourself.

---

## Phase 3: Two rooms with reflection + display lists

**Goal:** Rifat's room as a mirror image, and faster drawing.

```text
Read docs/techspec.md sections 3.2, 3.3, 3.4.

1. Draw Rifat's room using the same room functions with glTranslatef(97 + 93, 2, 0) and glScalef(-1, 1, 1).
   Samee's rug is grey-blue, Rifat's is green (design.md section 4).
2. Draw the divider at x 95-96 with the two colors from design.md section 3.
3. Draw "Samee" and "Rifat" name labels OUTSIDE the mirrored matrix so text is not backwards.
4. Implement room.build_room_lists(): display lists for neat and messy variants per rug color.
   (Messy blanket can be a placeholder for now.) Use glCallList in display().
5. Print the FPS to the console once per second.

Verification:
1. Rifat's room is an exact mirror: bed on the right, desk center-left.
2. The labels read normally.
3. FPS is 60, or close to it.
4. Remove glScalef(-1,1,1) temporarily and describe what happens, then put it back.
```

**Gate:** correct mirror, readable labels, smooth FPS.
**Understand it:** explain why the translate is `97 + 93` and not `97` when mirroring.

---

## Phase 4: Hand-written algorithms

**Goal:** all 5 CG algorithms in `algorithms.py`, each testable on its own.

```text
Read docs/techspec.md section 4.3.

1. Implement every function in algorithms.py by hand: no library does the algorithm.
   - boundary_fill must use an explicit stack, not recursion.
   - cohen_sutherland must use compute_outcode with named bit constants.
2. Add a test block under `if __name__ == "__main__":` in algorithms.py that prints results for:
   a line from (0,0) to (7,3); bezier t=0, 0.5, 1; a fill on a small 6x6 test grid;
   a circle of radius 3; lines fully inside, fully outside, and crossing the clip rect.
3. Build the messy blanket from design.md section 5 using bresenham_line for the outline and
   boundary_fill for the inside, and use it in the ROOM_MESSY display lists.

Verification:
1. `python algorithms.py` prints correct results. Explain each expected value.
2. Temporarily force messy=True: the messy blanket looks like the Working mockup.
```

**Gate:** tests pass, messy blanket matches the mockup.
**Understand it:** this is the most important phase for the viva. For each algorithm, explain in your own words what each line does. Practice: "delete this line, what happens?"

---

## Phase 5: Working state (no animation)

**Goal:** keys `1` / `2` instantly switch between sleeping and working.

```text
Read docs/design.md section 6 and docs/appflow.md section 3.

1. Implement the sitting pose (HEAD_BACK, BODY_BACK, arms) with the typing animation.
2. Implement draw_screen(on=True) with code lines, and draw_lamp_shade(on=True).
3. Keys 1 and 2 toggle Samee/Rifat between IN_BED and WORKING instantly (temporary).
   The bed switches to messy when not IN_BED.

Verification:
1. Pressing 1 makes Samee's side match the Working mockup (lighting not done yet).
2. Hands alternate typing.
3. Rifat's side works the same, mirrored.
```

**Gate:** both states look right with instant switching.

---

## Phase 6: Animation (state machine + Bezier walk)

**Goal:** the full get-up, walk, sit sequence.

```text
Read docs/appflow.md section 3 and docs/techspec.md section 4.6.

1. Implement the Character class exactly as in techspec 4.6, with all 8 states from appflow section 3.
2. Walking uses cubic_bezier with ease_in_out and the WALK_P0..P3 points from config.
3. Walk frames alternate every STEP_INTERVAL. Add the 1-pixel bob and the sit squash (glScalef).
4. Monitor turns on DEVICE_DELAY after sitting, lamp DEVICE_DELAY after that. Reverse order when leaving.
5. Reversing mid-walk: progress = 1 - progress (appflow section 3).
6. Use glutTimerFunc with real dt from time.perf_counter().
7. Keys 1/2 now call set_working instead of switching instantly.

Verification:
1. Press 1: Samee gets up, walks a curved path over the rug, sits, the monitor turns on, then the lamp.
2. Press 1 again: the reverse happens, and the blanket becomes neat only after he is back in bed.
3. Press 1 twice quickly mid-walk: he turns around smoothly, no jump.
4. Change WALK_TIME in config to 1.0 and confirm it is faster.
```

**Gate:** all four checks pass.
**Understand it:** explain the Bezier formula and why `ease_in_out` makes the walk look natural.

---

## Phase 7: Lighting + debug view

**Goal:** cozy dark rooms and a warm lamp glow that stays inside its room.

```text
Read docs/design.md section 8 and 11, and docs/techspec.md section 4.7.

1. Implement lighting.py in the draw order from design.md section 8.
2. Glow circles use scanline_circle and skip cells outside the room.
3. Rays use cohen_sutherland against the room rect, then bresenham_line.
4. Emissive parts (screen, lamp shade, bulb) are redrawn after the lighting.
5. Key D: debug overlay from design.md section 11 (grid, Bezier curve + control points,
   clip rects, rays unclipped in red and clipped in green). Key G: grid only.

Verification:
1. Idle rooms are dim blue. A working room has a warm stepped glow around the lamp.
2. The glow and rays never cross the divider (check with D).
3. The screen and lamp shade stay bright.
4. Compare side by side with both mockup frames.
```

**Gate:** matches the mockup, clipping visible in debug.

---

## Phase 8: Panel

**Goal:** the right-side panel with a working toggle and time counters.

```text
Read docs/design.md section 9, docs/techspec.md section 4.8, docs/appflow.md sections 5-7.

1. Implement panel.py: icon (moon/sun), title, status lines, toggle, two time cards, conflict warning.
2. Mouse click on the toggle toggles the --me user's status (local only for now).
3. Time tracking per appflow section 6 (local only for now).
4. Conflict: both working → "Both working!" and red blinking lamp shades.

Verification:
1. Clicking the toggle does the same as pressing that user's key.
2. The time counter increases while working and stops when off.
3. Both working → the warning shows.
```

**Gate:** panel fully works locally.

---

## Phase 9: Real-time sync

**Goal:** two laptops show the same thing.

```text
Read docs/techspec.md sections 4.9, 5, 9 and docs/appflow.md sections 4 and 9.

1. Give me the SQL to create the `status` table and insert rows for samee and rifat,
   plus the RLS policy needed. I will run it in Supabase myself.
2. Implement sync.py with requests and a daemon polling thread, protected by a Lock.
   The GLUT thread must never wait on the network.
3. The toggle PATCHes in a background thread. The local state updates immediately.
4. Panel shows "offline" when polling fails. --offline skips sync entirely.

Verification:
1. Run two instances: `--me rifat` and `--me samee`. Toggling in one appears in the other within about 3 s.
2. Turn off Wi-Fi: the app keeps running, shows offline, and keys still work.
3. The window never freezes during a slow network call.
```

**Gate:** two instances stay in sync. Offline mode is safe.

---

## Phase 10: Finish and prepare

- [ ] Check every function has the Bangla comment block
- [ ] Remove dead test code, keep the `algorithms.py` self-test
- [ ] README with how to run, screenshots, and the GitHub link
- [ ] Write the Part 1 page (answers are in `prd.md` section 8)
- [ ] Write the Part 3 reflection from `tracker.md` notes
- [ ] Rehearse the 2-minute demo (script in `tracker.md`)
- [ ] Practice every live edit in `techspec.md` section 8 at least once

---

## Tips for working with Claude Code

- Keep one phase per session so its context stays focused.
- If something looks wrong, ask it to **diagnose first**: "Explain why X happens before changing anything."
- After each phase, ask: "Walk me through every function you wrote in this phase, in simple language."
- Make at least one change yourself by hand in every phase. That's your viva practice.
