# Work•Sleep•Repeat — Technical Spec

## 1. Stack

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Course requirement |
| Graphics | PyOpenGL + GLUT (freeglut) | Course requirement |
| Sync backend | Supabase (Postgres + REST API) | Free, already familiar, simple HTTP |
| HTTP | `requests` | Plain REST calls are easy to explain; no extra SDK |
| Config secrets | `python-dotenv` | Keeps keys out of the code |

```
pip install PyOpenGL PyOpenGL_accelerate requests python-dotenv
```

On Windows, if `glutInit` raises `NullFunctionError`, freeglut is missing. Install a freeglut DLL next to the project or use a PyOpenGL wheel that bundles it.

Run with:

```
python main.py --me rifat
python main.py --me samee
python main.py --me rifat --offline
```

## 2. Folder structure

```
work-sleep-repeat/
├── main.py          # entry point: window, callbacks, main loop
├── config.py        # ALL numbers and colors
├── pixel.py         # low-level drawing helpers
├── sprites.py       # sprite grids as text
├── algorithms.py    # hand-written CG algorithms
├── room.py          # draws one room (static parts)
├── character.py     # character state machine and drawing
├── lighting.py      # darkness, glow, rays, emissive parts
├── panel.py         # side panel, toggle, time cards
├── sync.py          # Supabase polling in a background thread
├── .env             # SUPABASE_URL, SUPABASE_KEY (not committed)
├── .env.example
├── requirements.txt
└── docs/            # these .md files
```

**Dependency direction:** `main` → `room` / `character` / `lighting` / `panel` / `sync` → `pixel` / `algorithms` / `sprites` → `config`. Lower modules never import higher ones.

## 3. Rendering approach

### 3.1 Coordinate system

```python
gluOrtho2D(0, 240, 96, 0)   # left, right, bottom, top → y = 0 at top
```

One unit = one grid pixel. `draw_pixel(x, y)` draws a quad from `(x, y)` to `(x + 1, y + 1)`. The window is 1440 × 576, so each unit becomes 6 × 6 screen pixels. The grid scaling is itself a scaling transformation handled by the projection.

### 3.2 Layers per frame

```
display():
    clear
    for each room (Samee normal, Rifat mirrored):
        glPushMatrix()
        apply room transform (translate, and reflection for Rifat)
        call cached static room display list (neat or messy blanket variant)
        draw dynamic parts: screen state, lamp shade
        draw character
        draw lighting layers (darkness → glow → rays → emissive)
        glPopMatrix()
    draw divider and frame
    draw panel
    if debug: draw debug overlay
    glutSwapBuffers()
```

### 3.3 Mirroring with a transform

Rifat's room reuses the exact same drawing code:

```python
glTranslatef(97 + 93, 2, 0)   # move to the right edge of Rifat's room
glScalef(-1, 1, 1)            # reflect horizontally
```

Samee's room only needs `glTranslatef(2, 2, 0)`. This is the reflection transformation shown in the viva.

Text and name labels are drawn **outside** the mirrored matrix, otherwise they would appear backwards.

### 3.4 Performance: display lists

Drawing every pixel as a separate quad each frame is slow in Python. The fix:

1. Draw the static room once into a **display list** (`glGenLists`, `glNewList`, `glEndList`).
2. Keep two lists: `ROOM_NEAT` and `ROOM_MESSY` (the blanket differs).
3. Each frame, just `glCallList(...)`.
4. `draw_rect` sends one quad per rectangle, not per pixel.

Only the character, lighting, and panel are drawn fresh each frame.

### 3.5 Transparency

Lighting needs alpha blending:

```python
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
```

## 4. Module contracts

Every function listed here must exist with this signature. Colors are hex strings from `config.py`.

### 4.1 `config.py`

Constants only, no logic:
- `GRID_W = 240`, `GRID_H = 96`, `PIXEL = 6`, `WINDOW_W = 1440`, `WINDOW_H = 576`
- `ROOM_W = 93`, `ROOM_H = 92`, `SAMEE_ORIGIN = (2, 2)`, `RIFAT_ORIGIN = (97, 2)`
- All palette colors from `design.md` section 4
- All object positions from `design.md` section 5 (as tuples)
- Timing: `GET_UP_TIME = 0.3`, `WALK_TIME = 2.0`, `SIT_TIME = 0.3`, `DEVICE_DELAY = 0.3`, `TYPE_INTERVAL = 0.15`, `STEP_INTERVAL = 0.15`
- Bezier: `WALK_P0 = (30, 40)`, `WALK_P1 = (34, 62)`, `WALK_P2 = (52, 60)`, `WALK_P3 = (57, 44)`
- Lighting: `DARK_IDLE = 0.40`, `DARK_WORK = 0.30`, `GLOW_CENTER = (49, 13)`, `GLOW_RADII = [43, 31, 21, 13, 7]`, `GLOW_ALPHA = 0.08`, `RAY_COUNT = 12`
- Sync: `POLL_INTERVAL = 1.5`, `TIMEZONE = "Asia/Dhaka"`
- `FPS = 60`

### 4.2 `pixel.py`

| Function | Does |
|---|---|
| `hex_to_rgb(hex) -> (r, g, b)` | `"#4a6aa8"` → floats 0–1 |
| `set_color(hex, alpha=1.0)` | calls `glColor4f` |
| `draw_pixel(x, y, color, alpha=1.0)` | one grid cell |
| `draw_rect(x, y, w, h, color, alpha=1.0)` | filled rectangle as one quad |
| `draw_box(x, y, w, h, fill, outline=OUTLINE)` | rectangle with 1-pixel outline |
| `draw_sprite(x, y, rows, color_map)` | draws a text-grid sprite; `.` is skipped |
| `draw_text(x, y, text, color, font)` | `glRasterPos2f` + `glutBitmapCharacter` |

### 4.3 `algorithms.py` (hand-written; the heart of the viva)

| Function | Algorithm | Returns |
|---|---|---|
| `bresenham_line(x0, y0, x1, y1)` | Bresenham line | list of `(x, y)` cells |
| `cubic_bezier(p0, p1, p2, p3, t)` | `B(t) = (1-t)³P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³P3` | `(x, y)` |
| `bezier_points(p0, p1, p2, p3, steps)` | samples the curve | list of points |
| `ease_in_out(t)` | `t * t * (3 - 2 * t)` (smoothstep) | float 0–1 |
| `boundary_fill(grid, x, y, fill, boundary)` | 4-connected fill with an explicit **stack** (no recursion, since Python's recursion limit would crash) | modifies grid |
| `scanline_circle(cx, cy, r)` | for each row `dy` in `-r..r`, half width `= int(sqrt(r² - dy²))` | list of `(y, x_start, x_end)` spans |
| `compute_outcode(x, y, rect)` | Cohen-Sutherland region code (TOP, BOTTOM, LEFT, RIGHT bits) | int |
| `cohen_sutherland(x0, y0, x1, y1, rect)` | clip a line to a rectangle | clipped `(x0, y0, x1, y1)` or `None` |

**Where fill is used:** the messy blanket shape is built on a small local grid. Its outline is drawn with `bresenham_line`, then `boundary_fill` fills the inside from a seed point. The result is drawn as pixels into the `ROOM_MESSY` display list. The rug interior can be done the same way.

**Where clipping is used:** light rays start at the lamp shade and fan downward at fixed angles, each long enough to leave the room. `cohen_sutherland` clips each ray to the room rectangle `(0, 0, 92, 91)` before drawing it with `bresenham_line`. Glow circles use `scanline_circle` and skip cells outside the room, which is point clipping.

### 4.4 `sprites.py`

Text grids exactly as in `design.md` section 7: `HEAD_SLEEP`, `HEAD_BACK`, `BODY_BACK`, `STAND`, `WALK_A`, `WALK_B`, `PLANT`, `MOON`, `SUN`, plus a color map per sprite.

### 4.5 `room.py`

| Function | Does |
|---|---|
| `draw_wall_and_floor()` | wall, baseboard, planks |
| `draw_decor()` | poster, plant |
| `draw_bed(messy: bool)` | bed; neat or messy blanket |
| `draw_desk()` | desk, keyboard, mug, books, stand (not screen/lamp shade) |
| `draw_chair()` | chair |
| `draw_rug(colors)` | rug with the room's colors |
| `build_room_lists()` | creates display lists `ROOM_NEAT_*` and `ROOM_MESSY_*` for each rug color |
| `draw_screen(on: bool)` | monitor screen and code lines (dynamic) |
| `draw_lamp_shade(on: bool, warn: bool)` | lamp shade (dynamic, red when warning) |

All coordinates are **local** to a room. The caller applies the transform.

### 4.6 `character.py`

```python
class Character:
    name: str
    state: str          # IN_BED | GETTING_UP | WALKING_TO_DESK | SITTING_DOWN | WORKING
                        # | STANDING_UP | WALKING_TO_BED | LYING_DOWN
    progress: float     # 0..1 inside the current state
    target_working: bool
    devices_on: bool    # monitor + lamp

    def set_working(self, working: bool)   # only sets target; update() does the rest
    def update(self, dt: float)            # advances state machine
    def position(self) -> (x, y)           # current sprite position
    def bed_is_messy(self) -> bool         # True unless state == IN_BED
    def draw(self, time_now: float)        # draws the right sprite for the state
```

See `appflow.md` for the full state diagram and transitions.

**Walking uses Bezier:** `t = ease_in_out(progress)`, then `position = cubic_bezier(P0, P1, P2, P3, t)` walking to the desk. Walking back uses `1 - t`.

**Reversing mid-walk (F4):** if the target flips while walking, switch to the opposite walk state and set `progress = 1 - progress`. The character turns around right where they are.

**Small transforms while walking:** a 1-pixel vertical bob (`sin`), and a quick `glScalef(1, 0.9)` squash when sitting down.

### 4.7 `lighting.py`

| Function | Does |
|---|---|
| `draw_darkness(working: bool)` | one `NIGHT` quad over the room, alpha 0.40 or 0.30 |
| `draw_glow()` | 5 circles from `scanline_circle`, clipped to the room |
| `draw_rays(debug: bool)` | rays clipped with `cohen_sutherland`; in debug, unclipped red + clipped green |
| `draw_screen_glow()` | small blue circle at the monitor |

### 4.8 `panel.py`

| Function | Does |
|---|---|
| `draw_panel(state, me, now)` | whole panel |
| `format_time(seconds) -> str` | `—` or `2h 37m` |
| `toggle_hit(grid_x, grid_y) -> bool` | is the click inside the toggle box? |
| `screen_to_grid(mx, my) -> (gx, gy)` | `gx = mx / 6`, `gy = my / 6` (GLUT mouse y is already top-down) |

### 4.9 `sync.py`

| Function | Does |
|---|---|
| `start(me, offline)` | starts a background polling thread (daemon) unless offline |
| `get_state() -> dict` | thread-safe copy of the latest status of both users |
| `set_my_status(working: bool)` | updates local state now, sends PATCH in a background thread |
| `is_online() -> bool` | shown in the panel |

A `threading.Lock` protects the shared dict. **The GLUT thread never waits for the network.**

## 5. Data model (Supabase)

Table `status`:

| Column | Type | Notes |
|---|---|---|
| `id` | text, primary key | `"samee"` or `"rifat"` |
| `working` | boolean | |
| `since` | timestamptz, nullable | when the current session started |
| `today_seconds` | integer | finished sessions today |
| `day` | date | the day `today_seconds` belongs to |
| `updated_at` | timestamptz | |

REST calls:

```
GET   {URL}/rest/v1/status?select=*
PATCH {URL}/rest/v1/status?id=eq.rifat      body: {"working": true, "since": "...", ...}
Headers: apikey: KEY, Authorization: Bearer KEY, Content-Type: application/json
```

**Time logic:**
- Toggle on: `working = true`, `since = now`
- Toggle off: `today_seconds += now - since`, `working = false`, `since = null`
- Display: `today_seconds + (now - since if working else 0)`
- If `day != today` (Asia/Dhaka), treat `today_seconds` as 0 and write the new day on the next update

**Security note:** the anon key plus a permissive policy means anyone with the key can change status. That's fine for a two-person prototype. Say so if asked "what's the weakest part?"

## 6. Main loop and input

| Callback | Does |
|---|---|
| `glutDisplayFunc(display)` | draws the frame |
| `glutTimerFunc(16, tick, 0)` | computes `dt`, updates characters from sync state, `glutPostRedisplay()`, re-registers itself |
| `glutKeyboardFunc(keyboard)` | `1`, `2`, `D`, `G`, `ESC` |
| `glutMouseFunc(mouse)` | left click on the toggle → `sync.set_my_status(not working)` |

**Source of truth:** the sync state (or the local state in offline mode) says who *should* be working. Each `tick`, characters get `set_working(...)` from it, and their animation catches up on its own.

## 7. Mandatory comment style

Every function, and every important block inside one:

```python
# কী করছে: Cohen-Sutherland দিয়ে আলোর রশ্মিকে রুমের সীমার ভেতরে কেটে দিচ্ছে
# কেন লাগছে: না কাটলে আলো দেয়াল পেরিয়ে অন্যজনের রুমে চলে যেত
# real world-এ এটা কোথায় দেখা যায়: GPU rendering pipeline-এ স্ক্রিনের বাইরের অংশ বাদ দিতে
```

Claude Code should write these for every function. You should read each one and be able to say it in your own words.

## 8. Live-edit cheat sheet (viva)

| Teacher asks | Change |
|---|---|
| "Make the blanket red" | `config.BLANKET`, `BLANKET_D`, `BLANKET_L` |
| "Make him walk faster" | `config.WALK_TIME = 1.0` |
| "Change the walking path" | `config.WALK_P1` / `WALK_P2` |
| "Make the room darker" | `config.DARK_IDLE` |
| "Bigger lamp glow" | `config.GLOW_RADII` |
| "Remove clipping" | skip `cohen_sutherland` in `draw_rays` → rays cross the divider (press `D` to show it) |
| "Straight-line walk instead of a curve" | set `WALK_P1 = WALK_P0`, `WALK_P2 = WALK_P3` |
| "Delete this line in boundary_fill" | removing a neighbor push leaves gaps; removing the boundary check fills everything |
| "Don't mirror the second room" | remove `glScalef(-1, 1, 1)` → Rifat's room faces the wrong way and overlaps |

## 9. Error handling

| Situation | Behavior |
|---|---|
| No `.env` or no internet | Start in offline mode, panel shows "offline", keys still work |
| A PATCH fails | Keep the local state, retry on the next toggle, show "offline" |
| Unknown `--me` value | Print usage and exit |
| Poll returns bad data | Ignore it, keep the last good state |

## 10. Dev tools

Not part of the app; used to verify each phase.

### `tools/snapshot.py`

Renders **one frame of the current `display()`** to a PNG, without opening an interactive window loop (it creates a GLUT context, draws one frame, reads the framebuffer, and exits).

```
python tools/snapshot.py out.png
```

- Depends on **Pillow**, listed in `requirements-dev.txt` (kept out of `requirements.txt` so the app itself needs no extra packages). Install with `pip install -r requirements-dev.txt`.
- Because it calls the real `main.display()`, whatever the app draws this phase is what the snapshot shows.
- Reads the front buffer after the frame is drawn and flips vertically (OpenGL's origin is bottom-left, image files are top-left).
