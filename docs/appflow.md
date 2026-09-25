# Work•Sleep•Repeat — App Flow

This file explains what happens, step by step, from starting the app to a toggle appearing on the other person's screen.

## 1. Startup

```mermaid
flowchart TD
    A[python main.py --me rifat] --> B{--me valid?}
    B -- no --> X[Print usage and exit]
    B -- yes --> C[Load config.py and .env]
    C --> D{Keys found and not --offline?}
    D -- yes --> E[sync.start: background polling thread]
    D -- no --> F[Offline mode]
    E --> G[glutInit, create 1440x576 window]
    F --> G
    G --> H[gluOrtho2D 0,240,96,0 and enable blending]
    H --> I[room.build_room_lists: cache static rooms]
    I --> J[Create 2 Characters: Samee, Rifat, both IN_BED]
    J --> K[Register display, timer, keyboard, mouse]
    K --> L[glutMainLoop]
```

## 2. The main loop (every ~16 ms)

```mermaid
flowchart TD
    T[tick] --> A[dt = now - last_time]
    A --> B[state = sync.get_state or local state]
    B --> C[samee.set_working state.samee.working]
    C --> D[rifat.set_working state.rifat.working]
    D --> E[samee.update dt, rifat.update dt]
    E --> F[glutPostRedisplay]
    F --> G[glutTimerFunc 16, tick]
    F --> H[display: draw everything]
```

**Key idea:** the sync state says what *should* happen. The character's state machine decides *how* to get there with animation. The two never fight each other.

## 3. Character state machine

```mermaid
stateDiagram-v2
    [*] --> IN_BED
    IN_BED --> GETTING_UP: target = working
    GETTING_UP --> WALKING_TO_DESK: after 0.3 s
    WALKING_TO_DESK --> SITTING_DOWN: Bezier t reaches 1
    SITTING_DOWN --> WORKING: after 0.3 s, then monitor on, then lamp on
    WORKING --> STANDING_UP: target = sleeping (lamp off, monitor off first)
    STANDING_UP --> WALKING_TO_BED: after 0.3 s
    WALKING_TO_BED --> LYING_DOWN: Bezier t reaches 0
    LYING_DOWN --> IN_BED: after 0.3 s, blanket becomes neat

    WALKING_TO_DESK --> WALKING_TO_BED: target flips (progress = 1 - progress)
    WALKING_TO_BED --> WALKING_TO_DESK: target flips (progress = 1 - progress)
```

What's on screen in each state:

| State | Sprite | Bed | Monitor | Lamp |
|---|---|---|---|---|
| `IN_BED` | head on pillow | neat | off | off |
| `GETTING_UP` | standing beside bed | messy | off | off |
| `WALKING_TO_DESK` | walk frames on the curve | messy | off | off |
| `SITTING_DOWN` | sitting (with squash) | messy | off | off |
| `WORKING` | sitting + typing | messy | on (after 0.3 s) | on (after 0.6 s) |
| `STANDING_UP` | standing at chair | messy | off | off |
| `WALKING_TO_BED` | walk frames, curve reversed | messy | off | off |
| `LYING_DOWN` | standing beside bed | messy | off | off |

States like `GETTING_UP` and `SITTING_DOWN` can't be interrupted. They are short (0.3 s), and the new target is applied once they finish.

## 4. Toggle flow (the full journey)

When Rifat clicks the toggle:

```mermaid
sequenceDiagram
    participant R as Rifat's app
    participant DB as Supabase
    participant S as Samee's app

    R->>R: mouse click → toggle_hit is true
    R->>R: sync.set_my_status(true): local state updated now
    R->>R: next tick: Rifat's character starts GETTING_UP
    R-)DB: PATCH status id=rifat {working: true, since: now} (background)
    loop every 1.5 s
        S->>DB: GET status (background thread)
        DB-->>S: rifat.working = true
    end
    S->>S: next tick: Rifat's character starts GETTING_UP on Samee's screen too
```

- Rifat sees his own change **instantly**, because the local update comes first.
- Samee sees it within **about 1.5–3 s**, depending on the poll timing.

## 5. Input map

| Input | Online mode | Offline mode |
|---|---|---|
| Click toggle | toggles **my** status and syncs it | toggles my status locally |
| `1` | toggles Samee locally (demo only, not synced) | toggles Samee |
| `2` | toggles Rifat locally (demo only, not synced) | toggles Rifat |
| `D` | debug overlay on/off | same |
| `G` | grid lines on/off | same |
| `ESC` | quit | same |

In online mode, a remote update overrides a local `1`/`2` change on the next poll. This is expected, since keys are for demos.

## 6. Time tracking flow

```mermaid
flowchart TD
    A[Toggle ON] --> B[since = now]
    B --> C[Panel shows today_seconds + now - since, updates every frame]
    C --> D[Toggle OFF]
    D --> E[today_seconds += now - since]
    E --> F[since = null]
    G[App start or poll] --> H{day != today in Asia/Dhaka?}
    H -- yes --> I[Treat today_seconds as 0, save new day on next write]
    H -- no --> C
```

## 7. Conflict flow (both working)

```mermaid
flowchart TD
    A[tick] --> B{samee.working AND rifat.working?}
    B -- no --> C[Normal panel and lamps]
    B -- yes --> D[Status: Both working! in red]
    D --> E[Both lamp shades blink red every 0.5 s]
```

This warns about exactly the problem the app exists to prevent.

## 8. Draw order per frame

```
1. Clear screen
2. Samee's room (translate only)
   a. static room display list (neat or messy)
   b. screen + lamp shade (dynamic)
   c. character
   d. darkness → glow → rays → screen glow
   e. emissive parts (screen, lamp shade, bulb) redrawn on top
3. Rifat's room (translate + reflect), same steps
4. Divider and outer frame
5. Name labels (not mirrored)
6. Panel
7. Debug overlay (if on)
8. Swap buffers
```

## 9. Offline / failure flow

```mermaid
flowchart TD
    A[Poll or PATCH fails] --> B[Keep last good state]
    B --> C[Panel shows offline]
    C --> D[Keys and toggle still work locally]
    D --> E{Next poll succeeds?}
    E -- yes --> F[Back online, remote state wins]
    E -- no --> C
```
