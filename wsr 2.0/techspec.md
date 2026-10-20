# Work•Sleep•Repeat — Tech Spec (v2)

> Contract-first. Everything a phase builds must match the contracts here. If a phase needs to change a contract, update this file first, then code.
> Sections marked **[VERIFY IN SPIKE]** are assumptions that Phase 9 must confirm before we build on them.

---

## 1. Big picture

```
 PC (Rifat)                                                 PC (Samee)
 ┌──────────────────────────────────────┐                   ┌──────────────┐
 │ Claude Code                          │                   │   same app   │
 │  ├─ hooks ──────── POST /hook ───┐   │                   │   same setup │
 │  └─ status line ── POST /status  │   │                   └──────┬───────┘
 │                                  ▼   │                          │
 │  Work•Sleep•Repeat app                │                          │
 │   listener (127.0.0.1:47821)          │                          │
 │     → activity engine → state         │     Supabase             │
 │     → usage reports    → state        │   ┌───────────┐          │
 │   sync thread  ◄──── poll / RPC ─────────►│ wsr_*     │◄─────────┘
 │   tray + alerts                        │   │ tables +  │
 │   render loop (rooms + panel)          │   │ functions │
 └──────────────────────────────────────┘   └───────────┘
```

Two ideas hold the design together:

1. **Supabase is the contract.** Sensors (hooks, status line) and displays (rooms, tray) never talk to each other directly. They go through local state, and local state goes through Supabase.
2. **The toggle-sets-a-target rule stays.** Detection only sets `working = true/false`. The character animates toward it on its own, exactly like before.

---

## 2. Tech choices

| Area | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Existing code. |
| Rendering | PyOpenGL (unchanged) | Phases 0–8 already built. |
| Window layer | GLUT (freeglut) — **fallback: pyglet** | Only `main.py` touches GLUT, so swapping is contained. Decided in spike. **[VERIFY IN SPIKE]** |
| Tray + toasts | `pystray` + `Pillow` | Simple, `icon.notify()` gives Windows toasts. **[VERIFY IN SPIKE]** |
| Local server | stdlib `http.server.ThreadingHTTPServer` | No extra dependency. |
| Network | `requests` | Simple, sync, packages cleanly. |
| Backend | Supabase (Postgres + PostgREST RPC) | Already planned; user knows it. |
| First-run UI | `tkinter` | Ships with Python; GLUT can't do text input. |
| Autostart | `winreg` (HKCU Run key) | No admin needed. |
| Packaging | PyInstaller `--onedir --windowed` | Simplest working exe. Installer (Inno Setup) later if wanted. |

---

## 3. Module map

Flat layout, same as today. Arrows = "may import". Lower layers never import higher ones.

```
Layer 4  main.py              wires everything, owns the GLUT loop
Layer 3  tray.py  sync.py  listener.py  setup_ui.py
Layer 2  alerts.py  claude_settings.py  autostart.py  userconfig.py
Layer 1  state.py  activity.py  usage.py  clock.py
Layer 0  config.py
Render   pixel.py algorithms.py sprites.py room.py character.py lighting.py panel.py
         (render modules import config + each other as today; they read a
          StateSnapshot passed in from main.py and never import layers 1–3)
```

| Module | Job | Threads it runs on |
|---|---|---|
| `config.py` | All numbers, colors, timeouts, port. | — |
| `clock.py` | Dhaka "today", midnight split, epoch/ISO parsing. | any |
| `state.py` | `AppState` (one lock) + `snapshot()` → frozen `StateSnapshot`. | any |
| `activity.py` | Turns hook events into `working` for *this* person. Pure logic + `tick(now)`. | listener, main |
| `usage.py` | Parses status line JSON → `UsageReport`. Formats %, countdowns, "updated ago". | listener, render |
| `alerts.py` | Watches snapshots for transitions, decides which toast to fire (with dedupe). | main (1 Hz) |
| `userconfig.py` | Load/save `%APPDATA%\WorkSleepRepeat\config.json`. | main |
| `claude_settings.py` | Backup + merge/remove our hooks and status line in `~/.claude/settings.json`. | setup |
| `autostart.py` | Add/remove HKCU Run value. | setup/tray |
| `listener.py` | Local HTTP server. Single-instance lock (port bind). | own thread |
| `sync.py` | Push own status + usage, pull shared state, heartbeat, backoff, offline. | own thread |
| `tray.py` | Tray icon, menu, `notify()`. | own thread |
| `setup_ui.py` | First-run tkinter dialog. | main (before GLUT) |
| `panel.py` | **Updated**: toggle removed; usage block, dibs button, online dots. | main |

---

## 4. Detection (Claude Code hooks)

### 4.1 Events we subscribe to

| Hook event | Meaning for us |
|---|---|
| `SessionStart` | Session exists. Counts as activity. |
| `UserPromptSubmit` | Turn started → `turn_active = true`. |
| `PostToolUse` (matcher `*`) | Keep-alive during long autonomous runs. |
| `Notification` | Keep-alive (e.g. Claude waiting for permission). |
| `Stop` | Turn finished → `turn_active = false`. |
| `SessionEnd` | Session gone. |

Every hook payload arrives as JSON on stdin and includes at least `session_id` and `hook_event_name`. **[VERIFY IN SPIKE: log real payloads on Windows.]**

### 4.2 Hook command

Same command for every event. Pipes the JSON to the app and always exits 0 so it can never block Claude Code (exit code 2 would block).

```bash
curl -s -m 1 -X POST --data-binary @- http://127.0.0.1:47821/hook >/dev/null 2>&1 || true
```

**[VERIFY IN SPIKE]** which shell Claude Code uses for hooks on Windows (Git Bash expected), that `curl` is on PATH, and that the command returns in < 1 s when the app is closed.

### 4.3 Settings we write into `~/.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart":     [{ "hooks": [{ "type": "command", "command": "<HOOK_CMD>" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "<HOOK_CMD>" }] }],
    "PostToolUse":      [{ "matcher": "*", "hooks": [{ "type": "command", "command": "<HOOK_CMD>" }] }],
    "Notification":     [{ "hooks": [{ "type": "command", "command": "<HOOK_CMD>" }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "<HOOK_CMD>" }] }],
    "SessionEnd":       [{ "hooks": [{ "type": "command", "command": "<HOOK_CMD>" }] }]
  },
  "statusLine": { "type": "command", "command": "<STATUS_CMD>" }
}
```

Merge rules (`claude_settings.py`):

- Always write a timestamped backup first: `settings.json.wsr-backup-YYYYMMDD-HHMMSS`.
- Our entries are identified by the substring `127.0.0.1:47821`. Install = append our entry to each event's list if not already present. Uninstall = remove only entries containing that substring.
- Never touch other hooks or keys.
- If a `statusLine` already exists and isn't ours: **do not replace**. Report it back to the setup UI, which asks the user.
- Invalid JSON in the existing file → abort, change nothing, show the error.

### 4.4 Activity engine (`activity.py`)

Per session: `{ turn_active: bool, last_event: float }`.

| Event | Effect |
|---|---|
| `SessionStart` | create session, `last_event = now` |
| `UserPromptSubmit` | create if missing, `turn_active = true`, `last_event = now` |
| `PostToolUse`, `Notification` | create if missing, `last_event = now` |
| `Stop` | `turn_active = false`, `last_event = now` |
| `SessionEnd` | delete session |

`tick(now)` runs every second:

```
drop sessions where now - last_event > TURN_STALE_CAP        # crashed sessions
working = any(
    (s.turn_active) or (now - s.last_event < IDLE_TIMEOUT)
    for s in sessions)
```

Config: `IDLE_TIMEOUT = 600 s`, `TURN_STALE_CAP = 1800 s`. Unknown event names are ignored. Malformed JSON is ignored (logged once).

`working` goes into `AppState.me.working`. When it changes, `since` is set and the status is queued for push.

### 4.5 Dev mode

`--dev` keeps keys `1` / `2`. They inject fake `UserPromptSubmit` / `SessionEnd` events for a fake session, into the *same* activity engine. No other manual control exists (the toggle is gone).

---

## 5. Usage limits (Claude Code status line)

### 5.1 Source

Claude Code pipes JSON to the status line command on each render. For Pro/Max it includes:

```json
"rate_limits": {
  "five_hour": { "used_percentage": 42.0, "resets_at": 1759160000 },
  "seven_day": { "used_percentage": 15.0, "resets_at": 1759600000 }
}
```

Facts to design around:
- Appears only after the first API response in a session.
- Each window can be missing independently. The whole object has gone missing in some versions before.
- `resets_at` is documented as Unix seconds; some reports show ISO strings. `clock.parse_ts()` accepts both.
- It is push-only: numbers only update while someone uses Claude Code.

**[VERIFY IN SPIKE]** that it's present on the account's plan and on Windows.

### 5.2 Status line command

The app's reply *is* the status line text, so one command does both jobs:

```bash
curl -s -m 1 -X POST --data-binary @- http://127.0.0.1:47821/statusline 2>/dev/null || true
```

The app returns one short line, e.g. `WSR · 5h 42% (resets 1h20m) · wk 15%`. If the app is closed, the status line is just empty.

### 5.3 Local handling

- Parse → `UsageReport{ five_pct, five_reset, week_pct, week_reset, observed_at }`. Missing windows = `None`.
- Status line fires often. Only queue a push to Supabase if a value changed, or 60 s passed since the last push.
- Never subscribe to the credentials file or any undocumented endpoint.

---

## 6. Supabase

### 6.1 Tables

```sql
create table wsr_status (
  user_id        text primary key,            -- 'rifat' | 'samee'
  display_name   text not null,
  working        boolean not null default false,
  since          timestamptz,
  today_seconds  integer not null default 0,
  today_date     date,                         -- Asia/Dhaka date for today_seconds
  wants_next     boolean not null default false,
  wants_next_at  timestamptz,
  last_heartbeat timestamptz,
  app_version    text,
  updated_at     timestamptz not null default now()
);

create table wsr_usage (
  id                  int primary key default 1 check (id = 1),  -- single row
  five_hour_pct       numeric,
  five_hour_resets_at timestamptz,
  seven_day_pct       numeric,
  seven_day_resets_at timestamptz,
  reported_by         text,
  reported_at         timestamptz
);
insert into wsr_usage (id) values (1);

create table wsr_usage_share (
  window_kind text not null,          -- 'five_hour' | 'seven_day'
  resets_at   timestamptz not null,   -- identifies the window
  user_id     text not null,
  points      numeric not null default 0,
  primary key (window_kind, resets_at, user_id)
);

insert into wsr_status (user_id, display_name) values ('rifat','Rifat'), ('samee','Samee');
```

### 6.2 Functions (all client calls go through these)

```sql
-- Update my own status. Server sets heartbeat time (no clock skew).
create or replace function wsr_update_status(p_user text, p_fields jsonb)
returns void language plpgsql security definer set search_path = public as $$
begin
  update wsr_status set
    working       = coalesce((p_fields->>'working')::boolean, working),
    since         = case when p_fields ? 'since' then (p_fields->>'since')::timestamptz else since end,
    today_seconds = coalesce((p_fields->>'today_seconds')::int, today_seconds),
    today_date    = coalesce((p_fields->>'today_date')::date, today_date),
    wants_next    = coalesce((p_fields->>'wants_next')::boolean, wants_next),
    wants_next_at = case when p_fields ? 'wants_next_at' then (p_fields->>'wants_next_at')::timestamptz else wants_next_at end,
    app_version   = coalesce(p_fields->>'app_version', app_version),
    last_heartbeat = now(),
    updated_at     = now()
  where user_id = p_user;
end $$;

-- Report usage. Newest report wins; increases are credited to the reporter.
create or replace function wsr_report_usage(
  p_user text, p_observed_at timestamptz,
  p_five_pct numeric, p_five_reset timestamptz,
  p_week_pct numeric, p_week_reset timestamptz)
returns void language plpgsql security definer set search_path = public as $$
declare cur wsr_usage;
begin
  select * into cur from wsr_usage where id = 1 for update;
  if cur.reported_at is not null and p_observed_at <= cur.reported_at then
    return;                                            -- stale report
  end if;

  perform wsr_credit('five_hour', p_user, cur.five_hour_pct, cur.five_hour_resets_at, p_five_pct, p_five_reset);
  perform wsr_credit('seven_day', p_user, cur.seven_day_pct, cur.seven_day_resets_at, p_week_pct, p_week_reset);

  update wsr_usage set
    five_hour_pct       = coalesce(p_five_pct, five_hour_pct),
    five_hour_resets_at = coalesce(p_five_reset, five_hour_resets_at),
    seven_day_pct       = coalesce(p_week_pct, seven_day_pct),
    seven_day_resets_at = coalesce(p_week_reset, seven_day_resets_at),
    reported_by = p_user, reported_at = p_observed_at
  where id = 1;
end $$;

-- Helper: credit the increase within the same window to the reporter.
create or replace function wsr_credit(
  p_kind text, p_user text,
  old_pct numeric, old_reset timestamptz, new_pct numeric, new_reset timestamptz)
returns void language plpgsql security definer set search_path = public as $$
declare delta numeric;
begin
  if new_pct is null or new_reset is null then return; end if;
  if old_reset is not null and abs(extract(epoch from new_reset - old_reset)) <= 120 then
    delta := new_pct - coalesce(old_pct, 0);           -- same window
    new_reset := old_reset;                            -- keep one key per window
  else
    delta := new_pct;                                  -- new window: all of it so far
  end if;
  if delta <= 0 then return; end if;
  insert into wsr_usage_share (window_kind, resets_at, user_id, points)
  values (p_kind, new_reset, p_user, delta)
  on conflict (window_kind, resets_at, user_id)
  do update set points = wsr_usage_share.points + excluded.points;
end $$;

-- One call returns everything the app needs.
create or replace function wsr_get_state()
returns jsonb language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'server_now', now(),
    'status', (select jsonb_agg(to_jsonb(s)) from wsr_status s),
    'usage',  (select to_jsonb(u) from wsr_usage u where id = 1),
    'shares', (select coalesce(jsonb_agg(to_jsonb(sh)), '[]'::jsonb)
               from wsr_usage_share sh
               join wsr_usage u on u.id = 1
               where (sh.window_kind = 'five_hour' and sh.resets_at = u.five_hour_resets_at)
                  or (sh.window_kind = 'seven_day' and sh.resets_at = u.seven_day_resets_at))
  );
$$;
```

### 6.3 Access (two-friends level)

- RLS on for all three tables, no table policies for `anon` → direct table access blocked.
- `grant execute` on `wsr_update_status`, `wsr_report_usage`, `wsr_get_state` to `anon`. `revoke execute on wsr_credit from public, anon` (internal helper only). Functions run as `security definer` so they can read/write past RLS.
- The anon key is shared. Anyone with it can change status. Accepted for v2; redo before wider use (see PRD §7).

### 6.4 Sync thread (`sync.py`)

```
loop every POLL_INTERVAL (2 s):
    if time jumped > 30 s since last loop (PC slept): force immediate reconnect + full re-push
    flush outbox (latest-wins per kind: status, usage)
    every HEARTBEAT_INTERVAL (20 s): wsr_update_status(me, {}) if nothing else was sent
    state = rpc wsr_get_state()
    apply to AppState under lock (peer status, usage, shares, server_now offset)
on error:
    consecutive_failures += 1
    if consecutive_failures >= 2: AppState.online = False
    back off: 2 → 4 → 8 → 16 → 30 s (cap), keep outbox
on success: failures = 0, online = True, back to 2 s
```

- HTTP timeout 5 s. `requests.Session` reused.
- Peer is **offline** if `server_now - peer.last_heartbeat > PEER_OFFLINE_AFTER (60 s)`. Uses server time on both sides.
- On startup: read own row. If `today_date` is today (Dhaka), resume `today_seconds`; otherwise start at 0.

### 6.5 Time worked today

- While `working`, add elapsed time to `today_seconds` locally each tick.
- Push on every working change and every 60 s while working.
- Midnight Asia/Dhaka: `clock.py` splits. Seconds before midnight are dropped (no history), counter restarts at 0 with the new `today_date`.

---

## 7. Local state contract (`state.py`)

```python
@dataclass(frozen=True)
class PersonView:
    user_id: str; name: str
    working: bool; since: datetime | None
    today_seconds: int
    wants_next: bool
    online: bool                 # heartbeat fresh (always True for me)

@dataclass(frozen=True)
class UsageView:
    five_pct: float | None; five_reset: datetime | None
    week_pct: float | None; week_reset: datetime | None
    reported_by: str | None; reported_at: datetime | None
    five_share: dict[str, float]   # user_id -> points
    week_share: dict[str, float]

@dataclass(frozen=True)
class StateSnapshot:
    me: PersonView; peer: PersonView
    usage: UsageView
    connected: bool              # Supabase reachable
    now: datetime
```

The render loop calls `state.snapshot()` once per frame and passes it to `character`, `panel` and `lighting`. Render code never holds the lock.

---

## 8. Local HTTP API (`listener.py`)

Bound to `127.0.0.1:47821` only. Port bind doubles as the single-instance lock.

| Method + path | Body | Reply | Notes |
|---|---|---|---|
| `POST /hook` | hook JSON | `204` | → `activity.handle(event)` |
| `POST /statusline` | status line JSON | `200 text/plain` one line | → `usage` report + reply text |
| `GET /health` | — | `200 ok` | used by spike + tests |
| `POST /show` | — | `204` | second instance asks the first to open its window |

Rules: reply fast (< 50 ms), never block on network, body limit 256 KB, ignore anything not from 127.0.0.1.

If the port is taken at startup: send `POST /show` to it and exit.

---

## 9. Tray + alerts

Tray menu:
- Open rooms
- Call dibs / Cancel dibs
- Alerts ▸ It's free · Dibs · Limits · Conflict (each on/off)
- Start with Windows (on/off)
- Claude Code integration ▸ Reinstall hooks · Remove hooks
- Quit

Tray icon: moon (both asleep), sun-ish (peer working), red dot overlay (conflict), grey (offline).

`alerts.py` compares the previous and current snapshot once per second:

| Alert | Fires when | Dedupe |
|---|---|---|
| It's free | peer.working true → false | once per transition |
| Dibs | peer.wants_next false → true | once per transition |
| Dibs cleared | I stop working while peer has dibs → remind peer's app (peer sees "It's free" anyway) | — |
| Limit 5h | five_pct crosses 80, 95 | once per threshold per window |
| Limit week | week_pct crosses 75 | once per window |
| Conflict | both working, lasting > 30 s | once per overlap |

Dibs auto-clears when the person who called it starts working, or after `DIBS_EXPIRE (2 h)`.

---

## 10. User config (`%APPDATA%\WorkSleepRepeat\config.json`)

```json
{
  "me": "rifat",
  "supabase_url": "https://xxxx.supabase.co",
  "supabase_anon_key": "…",
  "alerts": { "free": true, "dibs": true, "limits": true, "conflict": true },
  "autostart": true,
  "hooks_installed": true
}
```

Dev runs can still use `.env` (`SUPABASE_URL`, `SUPABASE_KEY`) and `--me`. The config file wins if both exist, `--me` wins over both.

---

## 11. Command line

```
WorkSleepRepeat.exe [--me rifat|samee] [--tray] [--offline] [--dev] [--setup]
  --tray     start hidden in tray (used by autostart)
  --offline  no Supabase; local only
  --dev      keys 1/2 inject fake events, FPS in debug view only
  --setup    force the first-run dialog
  --port N   dev only: listen on another port (run two copies on one PC)
  --idle N   dev only: override IDLE_TIMEOUT in seconds for manual tests
```

---

## 12. Error handling summary

| Failure | Behaviour |
|---|---|
| Supabase down / no wifi | panel shows "offline", own detection still works, outbox kept, backoff |
| PC slept | time jump detected → reconnect + re-push |
| Bad JSON from hook/status line | ignored, logged once per kind |
| `rate_limits` missing | usage bars keep last shared values with "updated X ago" |
| Reset time passed | bar shows "reset" |
| Claude Code crashed mid-turn | `TURN_STALE_CAP` drops the session |
| settings.json invalid | setup aborts, nothing written, error shown |
| Port 47821 busy (another app) | show a clear error in tray + log; spike to pick a different port if it ever happens |

Logs: `%APPDATA%\WorkSleepRepeat\wsr.log`, rotating, 1 MB × 3.
