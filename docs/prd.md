# Work•Sleep•Repeat — PRD (v2: daily-use Windows app)

> Supersedes the lab-era PRD. Phases 0–8 (graphics, animation, lighting, panel) are done and stay as they are. This PRD covers turning the lab project into a tool Rifat and Samee run every day.

---

## 1. Problem

Rifat and Samee share one Claude account. Today, to know if the other person is using it, one of them has to message and wait for a reply. They forget, they clash, and sometimes both are working at once and burn through the shared usage limits without knowing.

## 2. Goal

A small Windows app, installed on both PCs, that shows **without anyone touching it**:

1. Whether each person is using Claude Code right now.
2. How much of the shared **5-hour** and **weekly** limits is left, and when they reset.
3. Who used how much of the current limits.

It syncs in real time between the two PCs and lives in the system tray.

## 3. Users

- **Now:** two people, two Windows PCs, one shared Claude account (Pro/Max).
- **Later (not in this scope):** anyone sharing an account or resource. Nothing in v2 should block this, but nothing is built for it yet.

## 4. Scope

### In scope (v2)

| # | Feature | Why |
|---|---|---|
| F1 | **Auto-detect Claude Code use** via Claude Code hooks. No manual toggle. | The toggle was the weakest part. People forget. |
| F2 | **Real-time sync** between the two PCs via Supabase. | Core of the product. |
| ~~F3~~ | ~~Usage limits (5h / weekly % + countdowns)~~ — **DROPPED 2026-10-20.** Source is the terminal-only status line; user is VS Code + desktop. See tracker. | — |
| ~~F4~~ | ~~Usage split per person~~ — **DROPPED** with F3. | — |
| F5 | **"It's free" notification** when the other person stops working. | Removes the need to watch the app. |
| F6 | **Call dibs**: a button that says "I want it next". Shown to the other person without interrupting. | Replaces "are you done yet?" messages. |
| ~~F7~~ | ~~Limit alerts (80/95/75%)~~ — **DROPPED** with F3. | — |
| F8 | **Conflict alert** when both are working at once. | Existed on-screen; now also a toast. |
| F9 | **Online/offline heartbeat**: shows when the other PC is off or disconnected. | So "asleep" isn't confused with "PC off". |
| F10 | **Tray app**: lives in the system tray; clicking opens the rooms window; closing the window hides it. | Always-on without clutter. |
| F11 | **Start with Windows** (on by default, can be turned off). | Always-on without effort. |
| F12 | **Persistent "time worked today"**: survives restarts, resets at midnight Asia/Dhaka. | Was already planned; now matters for daily use. |
| F13 | **First-run setup**: pick who you are, and the app installs its hooks into Claude Code settings safely. | No manual JSON editing. |
| F14 | **Packaged build**: a folder/exe that runs without installing Python. | Samee shouldn't need a dev setup. |

### Out of scope (v2)

- History / charts over days or weeks (explicitly dropped).
- Detecting claude.ai web chat or the mobile app. (Possible later with a browser extension.)
- More than two users.
- Mac / Linux.
- Accounts, logins, or public distribution.
- Sound cues, day/night window, extra walking frames (polish backlog).

## 5. Requirements

### Functional

- **FR1** A Claude Code prompt on either PC turns that person's character to "working" within **3 s** on both PCs.
- **FR2** After the person stops (idle timeout, default **10 min** with no Claude Code activity, or all sessions ended), the character goes back to bed within **3 s** of the rule firing.
- **FR3** A long autonomous Claude Code run (Claude working for many minutes after one prompt) counts as working the whole time.
- **FR4** A crashed Claude Code session never leaves someone "working" forever (safety cap, default **30 min** without any event).
- ~~**FR5** Usage bars…~~ — dropped with F3.
- ~~**FR6** Reset-passed bar…~~ — dropped with F3.
- **FR7** If Supabase is unreachable, the app keeps running, shows "offline", and catches up when the network returns.
- **FR8** Installing hooks never destroys existing Claude Code settings: back up first, merge, and never touch other hooks or keys.
- **FR9** Every alert can be turned off in the tray menu.

### Non-functional

- **NFR1** Hooks must never slow Claude Code down noticeably: hook command finishes in < 1 s even if the app is closed.
- **NFR2** Network code never runs on the render thread. The window never freezes.
- **NFR3** Idle CPU (window hidden) under ~2%.
- **NFR4** Keep the modular architecture and the rule "low modules never import high ones".
- **NFR5** All tunable numbers live in `config.py`.

## 6. Success criteria

- Rifat and Samee run it for **7 days straight** without messaging "are you on it?".
- No crash or stuck status during those 7 days (or each one found is fixed and logged in `tracker.md`).

## 7. Known limits (accepted)

- Detection sees Claude Code in VS Code and the desktop Code tab (confirmed in Phase 9). Terminal CLI not installed here; claude.ai web chat isn't detected.
- Usage limits (5h/weekly) are NOT shown — the only source is the terminal status line, which never runs on this setup. See tracker 2026-10-20; may return via a browser extension later.
- Security is "two trusted friends" level (shared Supabase key). Must be redone before anyone else uses it.

## 8. Open questions

- **OQ1 (answered, Phase 9):** Hooks fire in VS Code and the desktop Code tab — both confirmed. Terminal not tested (no CLI). The status line does *not* fire in these GUI surfaces, which is why usage was dropped.
- **OQ2 (answered, Phase 9):** GLUT could not hide on close (X quits the process). Window layer moves to **pyglet** in Phase 10.
