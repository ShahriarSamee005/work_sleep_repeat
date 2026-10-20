# Work•Sleep•Repeat — Design (v2)

> The rooms, characters, animation and lighting from phases 2–7 do not change. This doc covers what's new or changed: the panel, new in-room signals, the tray, toasts and the first-run dialog.
>
> **Note (2026-10-20):** the usage-limit feature is dropped (no status line on VS Code/desktop). The usage block (§2.2), the status-line text (§6) and the USAGE_* colors are **kept below for reference only** and are not built. Everything else stands.
> **Palette rule:** reuse the existing named colors in `config.py`. New colors below are added to `config.py` with these names. Exact pixel positions also live in `config.py`, not here.

---

## 1. Design principles (unchanged + new)

1. Cozy night-time pixel art. Everything new must look like it belongs in the same world.
2. **Glanceable in 1 second.** Who's on it? How much is left? Nothing else needs to be read.
3. **Quiet by default.** No alert unless something changed that you'd act on.
4. **Honest about staleness.** Old numbers always say how old they are.

---

## 2. Panel (updated)

The clickable toggle is removed. Its space goes to the usage block.

```
┌─────────────────────────────┐
│  ☾  / ☀  status icon         │   same as today
│  "Samee is working"          │   status text (same rules, see §2.1)
│                              │
│  (usage block dropped)       │   was 5h/week bars — see note at top
│                              │
│  ── Today ─────────────────  │
│  ● Rifat   2h 14m            │   ● online dot
│  ● Samee   0h 48m            │
│                              │
│  [ ✋ Call dibs ]             │   button; see §2.3
│                              │
│  ○ online                    │   connection line (bottom)
└─────────────────────────────┘
```

### 2.1 Status text

| Situation | Text | Color |
|---|---|---|
| Nobody working | "Claude is free" | existing calm text color |
| Peer working | "Samee is working" | existing working color |
| Me working | "You're working" | existing working color |
| Both | "Both of you are on it!" | existing conflict red, lamps blink (as today) |
| Peer offline | "Samee is offline" | `OFFLINE_GREY` |
| Me disconnected | status as last known + bottom line "offline — retrying" | `OFFLINE_GREY` |

### 2.2 Usage bars — ⛔ DROPPED (reference only)

> Not built. Kept for if usage returns via a future source.


- Bar shows **% left** (100 − used). People care about what remains.
- Colors by % left: `> 30%` `USAGE_OK` (soft green), `10–30%` `USAGE_WARN` (amber), `< 10%` `USAGE_CRIT` (red).
- Stale rules:
  - `updated < 60 s` → "live"
  - older → "updated N min ago · by Name"
  - reset time passed → bar full, grey, label "reset — no new data yet"
  - never had data → bar empty outline, "no data yet — use Claude Code once"
- Reset text: under 24 h → "resets in 1h 20m"; otherwise day + time in Asia/Dhaka ("resets Thu 9:00 PM").
- Split row: two short bars with initials, lengths proportional to each person's points in the current 5h window. Tooltip-less; the numbers aren't shown on purpose (it's an estimate). Hidden when there's no share data.

### 2.3 Dibs button

| State | Button | Meaning |
|---|---|---|
| Peer working, no dibs | `[ ✋ Call dibs ]` | enabled |
| I called dibs | `[ ✋ Waiting… cancel ]` | pressed style |
| Peer called dibs | no button; peer's time card shows `✋ next` | |
| Nobody working | button hidden | no need |

### 2.4 Online dots

`●` `ONLINE_GREEN` if heartbeat fresh, `○` `OFFLINE_GREY` if not.

---

## 3. In-room signals (new)

Kept small so the rooms still read as rooms.

- **Dibs bubble:** when a person has called dibs, a small pixel speech bubble with a raised hand appears above their character (in bed or anywhere). Gentle 1 Hz bob, no blink.
- **Peer offline:** that room gets an extra darkness layer (reuse lighting overlay at +40% alpha) and a tiny "OFFLINE" plaque on the door area. Character stays where the last known state put it, but doesn't animate.
- **Conflict:** unchanged (red text + blinking lamps).

New sprites (text grids in `sprites.py`): `BUBBLE_DIBS` (11×9), `PLAQUE_OFFLINE` (text-drawn), tray icons below.

---

## 4. Tray icon

16×16 and 32×32 pixel art, generated at runtime from sprite grids (no image files to ship).

| State | Icon |
|---|---|
| Free (nobody working) | moon |
| Peer working | lit desk lamp |
| Me working | lit desk lamp, small "you" dot |
| Conflict | lamp + red corner dot |
| Offline | moon in grey |

Tooltip: same as status text, e.g. `Samee is working`. (No usage suffix — dropped.)

---

## 5. Toast copy

Short, first names, no exclamation spam.

| Alert | Title | Body |
|---|---|---|
| It's free | Claude is free | Samee just finished. |
| It's free + you had dibs | Your turn | Samee finished. You called dibs. |
| Dibs | Samee wants it next | They'll wait until you're done. |
| Conflict | You're both on it | Samee is also using Claude right now. |

---

## 6. Claude Code status line text — ⛔ DROPPED (reference only)

> Not built — the status line never runs on VS Code/desktop. `/statusline` just returns 204.

One line, plain ASCII-safe except the dot:

```
WSR · 5h 38% used (1h20m) · wk 19% · Samee: asleep
WSR · 5h 38% used (1h20m) · wk 19% · Samee: working ⚠
WSR · no limit data yet · Samee: asleep
```

- Shows **used** here (matches Claude Code's own wording), **left** in the panel.
- `⚠` only when both are working.
- Keep under ~70 chars.

---

## 7. First-run dialog (tkinter)

Plain, small, one screen. Dark background from the palette so it doesn't look foreign.

```
┌── Work•Sleep•Repeat — setup ─────────────┐
│ Who are you?     (•) Rifat   ( ) Samee   │
│ Supabase URL     [__________________]    │
│ Supabase key     [__________________]    │
│                                          │
│ [x] Connect to Claude Code (installs     │
│     hooks). A backup of your settings    │
│     is saved first.                      │
│ [x] Start with Windows                   │
│                                          │
│                                          │
│              [ Test connection ] [ Save ]│
└──────────────────────────────────────────┘
```

"Test connection" calls `wsr_get_state` and shows ✓ or the error in one line.

---

## 8. New colors (add to `config.py`)

| Name | Use | Suggested |
|---|---|---|
| `USAGE_OK` | bar > 30% left | soft green, low saturation to match night palette |
| `USAGE_WARN` | 10–30% left | warm amber (can reuse lamp-glow family) |
| `USAGE_CRIT` | < 10% left | reuse existing conflict red |
| `ONLINE_GREEN` | online dot | same as `USAGE_OK` |
| `OFFLINE_GREY` | offline text, dots, icons | muted blue-grey from the wall palette |

Pick exact hex values next to the existing palette so they sit well; don't use pure RGB primaries.
