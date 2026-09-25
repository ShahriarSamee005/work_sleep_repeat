# Work•Sleep•Repeat — Design

This file holds every visual decision for the project. If something on screen looks wrong, check it against this file first.

Mockup reference: https://claude.ai/artifact/EqC21inzuQQesJz63qFBYA

---

## 1. The idea in one line

Two pixel-art rooms side by side. If a person is **not** using the shared Pro AI account, their character sleeps in bed. When they toggle "working", the character gets up, walks to the desk, sits down, the monitor and lamp turn on, and they start typing. Both friends see the same scene in real time.

## 2. Look and feel

- **Style:** 2D pixel art, top-down 3/4 view (like Stardew Valley). Image 4 from our discussion is the target, but more pixelated and with fewer objects.
- **Mood:** cozy, night-time, warm wood, soft blue blankets.
- **Idle:** the whole room is dim and slightly blue.
- **Working:** the room is still dim, but warm yellow lamp light spreads from the desk and the monitor glows blue.
- **Simplicity rule for v1:** only the objects listed in section 5. No extra decorations until everything works.

## 3. Screen and grid

| Item | Value |
|---|---|
| Logical grid | **240 × 96** pixels |
| Pixel size | 6 × 6 screen pixels |
| Window size | **1440 × 576** |
| Scene area | grid x 0–191 |
| Panel area | grid x 192–239 |
| Coordinate setup | `gluOrtho2D(0, 240, 96, 0)` → **y = 0 is the top** |

### Scene layout (grid coordinates)

| Part | x | y | Notes |
|---|---|---|---|
| Outer frame | 0–191 | 0–95 | 2-pixel dark border (`OUTLINE`) |
| Samee's room | 2–94 | 2–93 | 93 × 92, drawn normally |
| Divider | 95–96 | 2–93 | x 95 = `#3a3346`, x 96 = `#2c2637` |
| Rifat's room | 97–189 | 2–93 | same room, **mirrored**: `x' = 92 - x` |

Name labels sit under each rug: Samee centered at local x ≈ 59, local y ≈ 85. Rifat uses the mirrored position.

## 4. Color palette

Keep every color in `config.py`. Never type a hex code anywhere else.

### Room

| Name | Hex | Used for |
|---|---|---|
| `OUTLINE` | `#231c2b` | all outlines, frame (dark purple-brown, softer than black) |
| `WALL` | `#56657a` | back wall |
| `WALL_L` | `#65768d` | wall highlight row |
| `WALL_D` | `#46526a` | wall top shadow |
| `TRIM` | `#3b2a22` | baseboard |
| `TRIM_L` | `#553b2c` | baseboard top edge |
| `FLOOR` | `#7b4b2e` | wood floor |
| `FLOOR_D` | `#673d25` | plank lines and seams |
| `FLOOR_L` | `#875535` | plank highlights |
| `NIGHT` | `#15132a` | darkness overlay |

### Bed

| Name | Hex | Used for |
|---|---|---|
| `WOOD` | `#6b4128` | headboard |
| `WOOD_D` | `#4f2e1c` | bed frame |
| `WOOD_L` | `#8a5836` | headboard highlight |
| `SHEET` | `#e6e1d6` | mattress sheet |
| `SHEET_D` | `#c4bcad` | sheet wrinkles, pillow outline |
| `PILLOW` | `#f3efe6` | pillow |
| `BLANKET` | `#4a6aa8` | blanket |
| `BLANKET_D` | `#37508a` | blanket shadow |
| `BLANKET_L` | `#6286c4` | blanket fold and highlight |

### Desk area

| Name | Hex | Used for |
|---|---|---|
| `DESK` | `#8a5a36` | desk top |
| `DESK_L` | `#a26c43` | desk highlight |
| `DESK_D` | `#5c3a22` | desk front edge |
| `MONITOR` | `#1f1d29` | monitor frame |
| `SCREEN_OFF` | `#2b3141` | screen off |
| `SCREEN_ON` | `#3f79b8` | screen on |
| `CODE` | `#b3e2ff` | code lines on screen |
| `CODE2` | `#ffd27a` | highlighted code lines |
| `KEY` | `#8d8a99` | keyboard |
| `KEY_D` | `#65627a` | keys |
| `LAMP_OFF` | `#6e5c4a` | lamp shade off |
| `LAMP_ON` | `#ffe29a` | lamp shade on |
| `LAMP_BULB` | `#fff4c8` | bright line under shade when on |
| `METAL` | `#3b3440` | lamp pole, monitor stand, chair post |
| `CHAIR` | `#8e2c33` | chair seat |
| `CHAIR_D` | `#611b22` | chair back |
| `CHAIR_L` | `#a8414a` | chair highlight |
| `MUG` | `#e9e4da` | mug |
| `BOOK` | `#9a3b3b` | red book |
| `BOOK2` | `#3f6b8a` | blue book |

### Decor

| Name | Hex |
|---|---|
| `PLANT` / `PLANT_D` | `#5a8a4c` / `#3e6436` |
| `POT` / `POT_D` | `#a8603a` / `#7d4428` |
| `POSTER_FRAME` | `#2e2536` |
| `POSTER_1` / `2` / `3` | `#e8a05a` / `#b8526a` / `#3d3a66` |

### Rugs (each room has its own)

| Room | Base | Dark edge | Light edge |
|---|---|---|---|
| Samee (grey-blue) | `#4b5669` | `#3a4354` | `#5a6781` |
| Rifat (green) | `#4f6a58` | `#3c5244` | `#607f6a` |

### Character

| Name | Hex |
|---|---|
| `SKIN` (body white) | `#f4f2ee` |
| `SKIN_S` (lavender shadow) | `#b9b1d9` |

### Light

| Name | Hex |
|---|---|
| `GLOW_WARM` | `#ffc26e` |
| `GLOW_SCREEN` | `#8fd0ff` |
| `WARNING` | `#e0484f` (conflict: both working) |

### Panel

| Name | Hex |
|---|---|
| `PANEL_BG` | `#2b2433` |
| `PANEL_BORDER` | `#1c1822` |
| `PANEL_CARD` | `#3a3144` |
| `PANEL_CARD_ACTIVE` | `#4a3a2c` |
| `ACCENT` | `#e8a857` (toggle on, active card border) |
| `TOGGLE_OFF` | `#4a4156` |
| `TEXT` | `#f1e9dd` |
| `TEXT_MUTED` | `#d9cbb8` |
| `TEXT_DIM` | `#a99bb5` |
| `GOLD` | `#ffd27a` (active time, status when working) |

## 5. Objects in one room (local coordinates)

Each room is 93 × 92. `(0, 0)` is the room's top-left. The right room uses the same numbers, mirrored.

`box(x, y, w, h)` means: fill with the color, plus a 1-pixel `OUTLINE` border.

### Wall and floor

- Wall: `rect(0, 0, 93, 16, WALL)`, top shadow `rect(0, 0, 93, 2, WALL_D)`, highlight row `rect(0, 12, 93, 1, WALL_L)`
- Baseboard: `rect(0, 16, 93, 2, TRIM)`, top edge `rect(0, 16, 93, 1, TRIM_L)`
- Floor: rows y 18–91, planks 5 pixels tall. For each pixel, with `row = (y - 18) // 5`:
  - if `(y - 18) % 5 == 4` → `FLOOR_D` (line between planks)
  - else if `(x + row * 13) % 29 == 0` → `FLOOR_D` (plank end seam)
  - else if `(y - 18) % 5 == 0` and `(x + row * 7) % 11 < 4` → `FLOOR_L` (highlight)
  - else → `FLOOR`

### Poster (on wall)

`box(32, 3, 10, 8, POSTER_FRAME)`, sky `rect(33, 4, 8, 3, POSTER_3)`, stripe `rect(33, 7, 8, 1, POSTER_2)`, ground `rect(33, 8, 8, 2, POSTER_1)`, sun pixel `(38, 5, POSTER_1)`

### Plant (corner by the divider)

- Pot: `box(84, 11, 7, 6, POT)`, shadow `rect(85, 15, 5, 1, POT_D)`
- Leaves sprite at `(83, 3)`, see section 7

### Bed

| Part | Drawing |
|---|---|
| Headboard | `box(5, 9, 23, 8, WOOD)`, highlight `rect(6, 10, 21, 1, WOOD_L)`, posts `rect(5, 9, 2, 8, OUTLINE)` and `rect(26, 9, 2, 8, OUTLINE)` |
| Frame | `box(5, 16, 23, 47, WOOD_D)` |
| Mattress | `rect(7, 17, 19, 44, SHEET)` |
| Pillow | `box(9, 18, 15, 7, PILLOW)` with `SHEET_D` outline, bottom shadow `rect(10, 23, 13, 1, SHEET_D)` |

**Idle blanket (neat, someone sleeping):**
- Sleeping head sprite at `(12, 20)`
- Blanket `rect(6, 27, 21, 34, BLANKET)`
- Folded sheet edge `rect(6, 27, 21, 2, SHEET)`, fold line `rect(6, 29, 21, 1, BLANKET_L)`
- Side shadows `rect(6, 30, 1, 31, BLANKET_D)`, `rect(26, 30, 1, 31, BLANKET_D)`, bottom `rect(6, 59, 21, 2, BLANKET_D)`
- Body bump under the blanket: for y 32–51, `w = int(6 * sqrt(1 - ((y - 42) / 11)²))`, dark pixel at `x = 16 - w`, light pixel at `x = 17 + w`
- Wrinkles: `rect(11, 36, 3, 1, BLANKET_D)`, `rect(20, 50, 4, 1, BLANKET_D)`, `rect(10, 54, 3, 1, BLANKET_L)`

**Working blanket (messy, bed empty):**
- Pillow dent: pixels `(15, 21)`, `(16–18, 21)`, `(14, 22)` in `SHEET_D`
- Sheet wrinkles: `rect(9, 29, 5, 1)`, `rect(12, 33, 6, 1)`, `rect(8, 38, 4, 1)` in `SHEET_D`
- Blanket pushed down diagonally. For each row y 30–60:
  - `edge = 7 + max(0, int((52 - y) * 0.85)) + (2 if y % 7 < 2 else 0)`
  - fill x from `max(6, edge)` to 26
  - pixel at `x == edge` → `BLANKET_L` (or `BLANKET_D` when `y % 3 == 0`)
  - `x == 26` or `y >= 59` → `BLANKET_D`
  - `(x + y) % 9 == 0` and `x > edge + 2` → `BLANKET_D` (wrinkles)
  - otherwise `BLANKET`
- Hanging corner: `rect(6, 57, 2, 4, BLANKET_D)`

> This messy blanket is the best place to show the **color fill** technique: draw its outline with lines, then fill the inside with your own boundary fill (see techspec.md).

### Desk

| Part | Drawing |
|---|---|
| Top | `box(44, 13, 33, 13, DESK)`, highlight `rect(45, 14, 31, 1, DESK_L)` |
| Front edge | `rect(44, 25, 33, 3, OUTLINE)`, inside `rect(45, 25, 31, 2, DESK_D)` |
| Legs | `rect(45, 28, 2, 3, OUTLINE)`, `rect(74, 28, 2, 3, OUTLINE)` |
| Monitor | `box(55, 3, 13, 10, MONITOR)`, screen `rect(56, 4, 11, 8)` |
| Monitor stand | `rect(60, 13, 3, 2, METAL)`, base `rect(58, 15, 7, 1, METAL)` |
| Keyboard | `box(55, 18, 13, 4, KEY)`, keys: for x in 56, 58 … 66 → `(x, 19)` and `(x + 1, 20)` in `KEY_D` |
| Lamp base | `rect(46, 20, 5, 2, METAL)` |
| Lamp pole | `rect(48, 12, 1, 8, METAL)` |
| Lamp shade | `rect(47, 8, 4, 1, OUTLINE)`, `rect(46, 9, 6, 3, OUTLINE)`, inside `rect(47, 9, 4, 2, LAMP_OFF/ON)`, rim `rect(45, 11, 8, 1, OUTLINE)` |
| Bulb line (on only) | `rect(46, 11, 6, 1, LAMP_BULB)` |
| Mug | `box(70, 17, 4, 4, MUG)`, handle `(74, 18)` and `(74, 19)` in `OUTLINE`, coffee `(71, 18, WOOD)` |
| Books | `box(69, 14, 7, 2, BOOK)`, top book `rect(70, 13, 5, 1, BOOK2)` |

**Screen off:** `SCREEN_OFF` with two reflection pixels `(57, 5)` and `(58, 5)` in `#3a4254`.

**Screen on:** `SCREEN_ON` plus code lines:

| x | y | length | color |
|---|---|---|---|
| 57 | 5 | 5 | `CODE` |
| 58 | 6 | 6 | `CODE2` |
| 58 | 7 | 4 | `CODE` |
| 57 | 8 | 7 | `CODE` |
| 58 | 9 | 3 | `CODE2` |
| 57 | 10 | 5 | `CODE` |

### Chair

- Seat `box(56, 31, 11, 7, CHAIR)`, highlight `rect(57, 32, 9, 1, CHAIR_L)`
- Back `box(56, 37, 11, 4, CHAIR_D)`
- Post `rect(61, 41, 1, 2, METAL)`, base `rect(58, 43, 7, 1, OUTLINE)`

### Rug

`box(34, 54, 50, 27, RUG_BASE)`, light edges `rect(36, 56, 46, 1)` and `rect(36, 56, 1, 23)`, dark edges `rect(36, 78, 46, 1)` and `rect(81, 56, 1, 23)`, stitch dots every 4 pixels at y 67 from x 38 to 78.

## 6. Character poses

The character style is the simple round-head figure from image 2: white body, lavender shadow, dark outline.

| Pose | Sprite | Where |
|---|---|---|
| Sleeping | `HEAD_SLEEP` only (body hidden by blanket) | `(12, 20)` |
| Standing / walking | `STAND`, `WALK_A`, `WALK_B` | along the Bezier path |
| Sitting and typing | `HEAD_BACK` + `BODY_BACK` + arms | head `(57, 21)`, body `(57, 27)` |

**Sitting arms:** outline lines `rect(56, 21, 1, 8)` and `rect(66, 21, 1, 8)`, inner arms `rect(57, 22, 1, 7, SKIN)` and `rect(65, 22, 1, 7, SKIN_S)`, hands `rect(56, 20, 3, 2, OUTLINE)` with `(57, 20, SKIN)`, and `rect(64, 20, 3, 2, OUTLINE)` with `(65, 20, SKIN)`.

**Typing animation:** every ~0.15 s, move one hand up 1 pixel, alternating left and right.

**Draw order when sitting:** chair → arms → body → head.

## 7. Sprites

Legend: `#` = `OUTLINE`, `W` = `SKIN`, `S` = `SKIN_S`, `.` = transparent.

```
HEAD_SLEEP (9×7)      HEAD_BACK (9×7)       BODY_BACK (10×5)
..#####..             ..#####..             #WWWWWWWS#
.#WWWWW#.             .#WWWWW#.             #WWWWWWWS#
#WWWWWWS#             #WWWWWWS#             #WWWWWWSS#
#W##W##S#             #WWWWWWS#             .#WWWSSS#.
#WWWWWWS#             #WWWWWSS#             .########.
.#WWWWS#.             .#WSSSS#.
..#####..             ..#####..
```

```
STAND (9×13)          WALK_A (last 2 rows)   WALK_B (last 2 rows)
..#####..             .#W#..#S#.             .##..#S#.
.#WWWWW#.             .##...##..             .....##..
#WWWWWWS#
#W#WW#WS#                (swap WALK_A and WALK_B every 0.15 s while walking)
#WWWWWWS#
.#WWWWS#.
..#####..
.#WWWWS#.
.#WWWWS#.
.#WWWSS#.
.#WW#SS#.
.#W#.#S#.
.##..##..
```

```
PLANT (9×6)   G = PLANT, g = PLANT_D
..G.G....
.GGgGG...
GGgGGgG..
gGGgGGG..
.GgGGg...
..GGG....
```

```
MOON (12×12)  Y = #f1e6c6, # = #8a7f96     SUN (12×12)  Y = #ffd27a, O = #f2a54a, # = #7a4a1e
....####....                               .....YY.....
..##YYY#....                               .Y...YY...Y.
.#YYYY#.....                               ..Y......Y..
.#YYY#......                               ....####....
#YYYY#......                               ...#OOOO#...
#YYYY#......                               YY.#OOOO#.YY
#YYYYY#.....                               YY.#OOOO#.YY
#YYYYYY#..##                               ...#OOOO#...
.#YYYYYY##Y#                               ....####....
.#YYYYYYYYY#                               ..Y......Y..
..##YYYYY##.                               .Y...YY...Y.
....#####...                               .....YY.....
```

## 8. Lighting

Lighting is drawn as **layers on top** of the room. Nothing in the room drawing itself changes.

**Draw order (per room):**
1. Room (static)
2. Character
3. Darkness overlay: one quad over the room, color `NIGHT`
   - idle alpha **0.40**
   - working alpha **0.30**
4. Warm glow (working only): 5 filled circles centered at the lamp `(49, 13)`, radii **43, 31, 21, 13, 7**, each `GLOW_WARM` at alpha **0.08**. They stack, so the center is brightest. That gives the stepped pixel-art glow.
5. Light rays (working only): about 12 lines fanning down from the lamp shade, `GLOW_WARM` at low alpha, **clipped to the room rectangle** so they never cross the divider
6. Screen glow (working only): 1 circle radius 9 at `(61, 9)`, `GLOW_SCREEN` alpha 0.12
7. Emissive pixels drawn **last** so they stay bright: screen and code lines, lamp shade, bulb line

Glow circles are made of whole grid cells, so they look pixelated. Any cell outside the room is skipped.

## 9. Panel design (grid x 192–239)

Top to bottom, centered in the 48-pixel-wide column:

| Element | Approx. grid position | Content |
|---|---|---|
| Icon | `(210, 6)`, 12×12 | Moon if nobody is working, sun if someone is |
| Title | y ≈ 24 | "PRO AI STATUS" (`TEXT_MUTED`) |
| Status | y ≈ 32 | "Pro AI is free" (`TEXT`) or "Samee is using it" (`GOLD`) |
| Sub-status | y ≈ 38 | "Nobody is working" or "Ask before you start" (`TEXT_DIM`) |
| Toggle | `box(204, 44, 24, 10)` | off = `TOGGLE_OFF`, knob left; on = `ACCENT`, knob right |
| Toggle label | y ≈ 58 | "Sleeping" / "Working" |
| Card 1 | `box(196, 66, 40, 12)` | "Samee · today" + time |
| Card 2 | `box(196, 81, 40, 12)` | "Rifat · today" + time |

- Card is `PANEL_CARD`, or `PANEL_CARD_ACTIVE` with an `ACCENT` border when that person is working.
- The time shows `—` when zero, else `Xh YYm`.
- Text uses GLUT bitmap fonts (`GLUT_BITMAP_8_BY_13` / `HELVETICA_12`).
- **Conflict (both working):** the status line becomes "Both working!" in `WARNING`, and both lamp shades blink red every 0.5 s.

## 10. Animation feel

| Step | Duration |
|---|---|
| Get out of bed (sleep sprite → stand beside bed) | 0.3 s |
| Walk along Bezier curve | 2.0 s, ease in-out |
| Sit down (stand → sitting sprites) | 0.3 s |
| Monitor turns on | 0.3 s later |
| Lamp turns on | 0.3 s later |
| Typing loop | until toggled off |

Going back to bed is the same steps in reverse: lamp off, monitor off, stand, walk back, lie down. The blanket stays messy until the character is back in bed, then becomes neat.

**Walk path (local coordinates, sprite top-left):** start `(30, 40)` beside the bed, control points `(34, 62)` and `(52, 60)`, end `(57, 44)` in front of the chair. The path curves over the rug. These are starting values; tune them in `config.py`.

## 11. Debug view (key `D`)

A debug overlay helps a lot in the viva:
- faint grid lines every 8 pixels
- the Bezier curve and its 4 control points
- the clip rectangle of each room
- light rays **before** clipping in red, **after** clipping in green
