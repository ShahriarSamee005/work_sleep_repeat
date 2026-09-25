# Algorithms Explained — viva prep

Every algorithm in `algorithms.py` is written by hand (no library does the algorithm). This file
explains each one in plain English: what it does, where we use it, the code line-by-line, what
breaks if you delete a key line, and one likely viva question.

Coordinate reminder: our grid is `gluOrtho2D(0, 240, 96, 0)`, so **y grows downward** (y=0 is the top).

---

## 1. `bresenham_line(x0, y0, x1, y1)`

**What it does:** finds every integer grid cell on the straight line from `(x0,y0)` to `(x1,y1)`, using only integer add/subtract.

**Where we use it:** the messy blanket outline (Phase 4) and the lamp light rays (Phase 7).

```python
def bresenham_line(x0, y0, x1, y1):
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points
```

**Line by line:**
- `dx, dy` — how far to go horizontally and vertically, as positive numbers.
- `sx, sy` — the *direction* of travel (+1 or −1). Splitting distance from direction is what makes it work in all 8 directions.
- `err = dx - dy` — the "error" tracks how far we've drifted from the true line. It decides, at each step, whether to move in x, in y, or both.
- `points.append((x, y))` — record the current cell.
- `if x == x1 and y == y1: break` — stop once we reach the end.
- `e2 = 2 * err` — doubling lets us compare with `dx`/`dy` using integers only (no fractions).
- `if e2 > -dy:` step in x; `if e2 < dx:` step in y. On a 45° line both fire; on a shallow line mostly x fires; on a steep line mostly y fires.

**If you delete this line…**
- Delete `if x == x1 and y == y1: break` → the loop never ends (infinite loop / hang).
- Delete `if e2 > -dy: ... x += sx` → x never advances, so you only ever draw a vertical line.
- Change `sx = 1 if x0 < x1 else -1` to always `1` → lines going leftward (x0 > x1) draw in the wrong direction and never reach the end (hang).

**Likely viva question:** *Why not just use `y = mx + c` with floats?* Because floating-point is slower and rounding drifts; Bresenham uses only integer add/subtract, is exact on the grid, and is what real rasterizers use.

---

## 2. `cubic_bezier(p0, p1, p2, p3, t)`

**What it does:** given 4 control points and a value `t` from 0 to 1, returns one point `(x, y)` on a smooth curve.

**Where we use it:** the character's curved walk from bed to desk (Phase 6). `t=0` is the start point `P0`, `t=1` is the end point `P3`; `P1`/`P2` bend the path.

```python
def cubic_bezier(p0, p1, p2, p3, t):
    u = 1 - t
    x = (u * u * u * p0[0] + 3 * u * u * t * p1[0]
         + 3 * u * t * t * p2[0] + t * t * t * p3[0])
    y = (u * u * u * p0[1] + 3 * u * u * t * p1[1]
         + 3 * u * t * t * p2[1] + t * t * t * p3[1])
    return (x, y)
```

**Line by line:**
- `u = 1 - t` — the "how far from the end" weight, to keep the formula short.
- The formula is `B(t) = (1−t)³P0 + 3(1−t)²t·P1 + 3(1−t)t²·P2 + t³P3`. The four weights always add up to 1, so the point is a **blend** of the four control points.
- At `t=0`: only `u³ = 1` survives → the point is exactly `P0`. At `t=1`: only `t³ = 1` survives → exactly `P3`.
- We apply the identical blend to x and y separately.

**If you delete this line…**
- Delete `u = 1 - t` → `u` is undefined → crash (`NameError`).
- Drop the middle terms (`P1`, `P2`) → you get a straight line from `P0` to `P3` (no curve).

**Likely viva question:** *Does the curve pass through P1 and P2?* No. It passes through `P0` and `P3` only; `P1` and `P2` "pull" the curve toward them but the curve doesn't touch them.

---

## 3. `bezier_points(p0, p1, p2, p3, steps)`

**What it does:** samples the whole curve into `steps + 1` points by calling `cubic_bezier` at evenly spaced `t` values.

**Where we use it:** drawing the walk path in the debug overlay (Phase 7).

```python
def bezier_points(p0, p1, p2, p3, steps):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        pts.append(cubic_bezier(p0, p1, p2, p3, t))
    return pts
```

**Line by line:**
- `for i in range(steps + 1)` — `steps + 1` so we include both `t=0` and `t=1`.
- `t = i / steps` — turns the counter `i` into a fraction 0 … 1.
- `pts.append(cubic_bezier(...))` — one curve point per step.

**If you delete this line…** change `range(steps + 1)` to `range(steps)` → you never sample `t=1`, so the drawn curve stops just short of the end point.

**Likely viva question:** *More steps = better?* Smoother curve but more points to draw; past a point the extra smoothness isn't visible, so we pick a modest number.

---

## 4. `ease_in_out(t)`

**What it does:** reshapes a 0→1 progress value so motion starts slow, speeds up in the middle, and slows down at the end (smoothstep).

**Where we use it:** the walk (Phase 6). We feed `ease_in_out(progress)` into the Bezier `t` so the character accelerates and decelerates naturally instead of moving at constant speed.

```python
def ease_in_out(t):
    return t * t * (3 - 2 * t)
```

**Line by line:**
- `t * t * (3 - 2 * t)` is the smoothstep polynomial. At `t=0` it gives 0, at `t=1` it gives 1, and at `t=0.5` it gives 0.5 — but its *slope* is zero at both ends, which is what makes the start and stop gentle.

**If you delete this line…** return `t` unchanged instead → the walk moves at constant speed and looks robotic (no ease).

**Likely viva question:** *Why does it look natural?* Real things can't jump to full speed instantly; easing gives near-zero speed at the ends and maximum speed in the middle, like a real person starting and stopping.

---

## 5. `boundary_fill(grid, x, y, fill, boundary)`

**What it does:** starting at `(x, y)`, spreads the `fill` value to all 4-connected cells until it hits `boundary` cells — using an **explicit stack**, not recursion.

**Where we use it:** filling the inside of the messy blanket outline (Phase 4).

```python
def boundary_fill(grid, x, y, fill, boundary):
    height = len(grid)
    width = len(grid[0])
    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if cx < 0 or cy < 0 or cx >= width or cy >= height:
            continue
        current = grid[cy][cx]
        if current == boundary or current == fill:
            continue
        grid[cy][cx] = fill
        stack.append((cx + 1, cy))
        stack.append((cx - 1, cy))
        stack.append((cx, cy + 1))
        stack.append((cx, cy - 1))
```

**Line by line:**
- `stack = [(x, y)]` — our own to-do list of cells to visit (a plain Python list used as a stack).
- `while stack:` — keep going while there is work.
- `cx, cy = stack.pop()` — take the most recent cell.
- the bounds `if` — skip anything off the grid.
- `if current == boundary or current == fill: continue` — **stop conditions**: don't cross the outline, and don't re-fill a cell we already did (this prevents an infinite loop).
- `grid[cy][cx] = fill` — paint this cell.
- the four `stack.append(...)` — queue the 4 neighbours (right, left, down, up) = 4-connected.

**If you delete this line…**
- Delete `if current == boundary ...: continue` → the fill ignores the outline and floods the entire grid; also it revisits cells forever (hang).
- Delete one neighbour push (e.g. `(cx, cy - 1)`) → the fill can't travel upward, leaving unfilled gaps.

**Likely viva question:** *Why a stack instead of recursion?* A recursive flood fill calls itself once per cell; on a big area Python hits its recursion limit (~1000) and crashes. An explicit stack keeps the "to-do list" in a normal list on the heap, so it handles any size.

---

## 6. `scanline_circle(cx, cy, r)`

**What it does:** for a circle of radius `r`, returns one horizontal span `(y, x_start, x_end)` per row, so the circle can be filled row by row.

**Where we use it:** the warm lamp glow and screen glow (Phase 7) — stacked filled circles.

```python
def scanline_circle(cx, cy, r):
    spans = []
    for dy in range(-r, r + 1):
        half = int(math.sqrt(r * r - dy * dy))
        y = cy + dy
        spans.append((y, cx - half, cx + half))
    return spans
```

**Line by line:**
- `for dy in range(-r, r + 1)` — walk each row from the top of the circle to the bottom.
- `half = int(math.sqrt(r * r - dy * dy))` — from the circle equation `x² + y² = r²`, the half-width at height `dy` is `sqrt(r² − dy²)`. `int(...)` snaps it to whole cells (this is what makes the glow look pixel-stepped).
- `spans.append((y, cx - half, cx + half))` — the filled run for this row, from left edge to right edge.

**If you delete this line…** replace `int(math.sqrt(r*r - dy*dy))` with a constant → you get a rectangle, not a circle. Drop the `int(...)` → `x_start`/`x_end` become floats and can't index grid cells cleanly.

**Likely viva question:** *Why spans instead of plotting each circle pixel?* Filling by horizontal runs is fewer draw calls and matches how raster fills work; we also reuse the same spans to skip cells outside the room.

---

## 7. `compute_outcode(x, y, rect)`

**What it does:** returns a 4-bit code saying whether a point is inside a rectangle, or which side(s) it is outside of.

**Where we use it:** the helper for Cohen-Sutherland clipping of the light rays (Phase 7).

```python
INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8

def compute_outcode(x, y, rect):
    xmin, ymin, xmax, ymax = rect
    code = INSIDE
    if x < xmin:
        code |= LEFT
    elif x > xmax:
        code |= RIGHT
    if y < ymin:
        code |= TOP
    elif y > ymax:
        code |= BOTTOM
    return code
```

**Line by line:**
- `code = INSIDE` (0) — assume inside until proven outside.
- `x < xmin → LEFT`, `x > xmax → RIGHT` — horizontal position.
- `y < ymin → TOP`, `y > ymax → BOTTOM` — vertical position. **Note:** because y grows downward, *small* y is the TOP, so `y < ymin` sets `TOP`.
- `|=` (bitwise OR) — a corner point can be outside on two sides at once (e.g. `TOP | LEFT`).

**If you delete this line…** swap `TOP` and `BOTTOM` (forget the y-is-down rule) → clipping still "works" mathematically but the labels are wrong, which bites you in the debug view where TOP-clipped rays would be mislabelled.

**Likely viva question:** *Why 1, 2, 4, 8 and not 1, 2, 3, 4?* They are single bits, so one integer can hold several flags at once and we can test a side with a fast bitwise AND.

---

## 8. `cohen_sutherland(x0, y0, x1, y1, rect)`

**What it does:** clips a line to a rectangle — returns the part inside as `(x0,y0,x1,y1)`, or `None` if the line is entirely outside.

**Where we use it:** clipping each lamp light ray to the room rectangle so light never crosses the divider into the other person's room (Phase 7).

```python
def cohen_sutherland(x0, y0, x1, y1, rect):
    xmin, ymin, xmax, ymax = rect
    out0 = compute_outcode(x0, y0, rect)
    out1 = compute_outcode(x1, y1, rect)
    while True:
        if out0 == INSIDE and out1 == INSIDE:
            return (x0, y0, x1, y1)
        if out0 & out1:
            return None
        out = out0 if out0 != INSIDE else out1
        if out & TOP:
            x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
            y = ymin
        elif out & BOTTOM:
            x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
            y = ymax
        elif out & RIGHT:
            y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
            x = xmax
        else:  # LEFT
            y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
            x = xmin
        if out == out0:
            x0, y0 = x, y
            out0 = compute_outcode(x0, y0, rect)
        else:
            x1, y1 = x, y
            out1 = compute_outcode(x1, y1, rect)
```

**Line by line:**
- compute an outcode for each endpoint.
- `if out0 == INSIDE and out1 == INSIDE: return (...)` — **trivial accept**: both ends inside, keep the whole line.
- `if out0 & out1: return None` — **trivial reject**: both ends share an outside side (their AND is non-zero), so the whole line is outside that edge → nothing to draw.
- `out = out0 if out0 != INSIDE else out1` — pick an endpoint that is outside; we'll pull it onto the rectangle.
- the four branches — find where the line crosses the edge named by the set bit, using the line equation (similar triangles). Only the matching branch runs.
- the last `if/else` — move that endpoint to the crossing point, recompute its outcode, and loop. Each pass makes the line shorter until both ends are inside or the line is rejected.

**If you delete this line…**
- Delete `if out0 & out1: return None` → lines fully outside are never rejected; you can loop forever or draw garbage.
- Delete the recompute (`out0 = compute_outcode(...)`) → the endpoint's code never updates, so the loop never reaches the accept/reject condition (infinite loop).
- Skip clipping entirely in the caller → rays cross the divider into the other room (this is exactly the "remove clipping" demo in the viva).

**Likely viva question:** *What do the trivial accept and trivial reject do?* Accept = both ends inside, keep the line as-is. Reject = both ends past the *same* edge, so the whole line is outside and we drop it. Only lines that are partly in, partly out get clipped step by step.

---

## Quick recall table

| Algorithm | One line | Used for |
|---|---|---|
| `bresenham_line` | integer line → cells | blanket outline, light rays |
| `cubic_bezier` | 4 points + t → curve point | walk path |
| `bezier_points` | sample the whole curve | debug view of the path |
| `ease_in_out` | slow-fast-slow timing | natural walk speed |
| `boundary_fill` | stack flood fill inside a border | fill the messy blanket |
| `scanline_circle` | circle as row spans | lamp / screen glow |
| `compute_outcode` | which side of the rect | helper for clipping |
| `cohen_sutherland` | clip a line to a rect | keep light inside the room |
