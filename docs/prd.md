# Work•Sleep•Repeat — Product Requirements

## 1. Problem

Rifat and Samee share one Pro AI account. When one person is using it, the other has to message and ask, "Are you working right now?" Then they adjust their time around each other. This is slow and easy to forget, and it leads to both using the account at once.

## 2. Solution

A small desktop app built with Python OpenGL. It shows two pixel-art bedrooms, one per person.

- **Not using the account:** the character sleeps in bed. The desk lamp and monitor are off.
- **Using the account:** the person flips a toggle. Their character gets up, walks to the desk, sits, and starts typing. The monitor and lamp turn on.
- **Real time:** both friends run the app. When one flips the toggle, the other sees it within a couple of seconds.

A glance at the screen answers "is the other person working?" with no messages needed.

## 3. Users

| User | Need |
|---|---|
| Rifat | Know if Samee is using the account before starting |
| Samee | Same, the other way around |
| Course teacher | See real CG techniques used to solve a real problem |

## 4. Course context

This is the **Computer Graphics Sessional final project, "Bridge to the Real World"** at Leading University, CSE.

| Requirement | How we meet it |
|---|---|
| Real-world problem | Shared account scheduling between two people |
| Python OpenGL (PyOpenGL + GLUT) | The whole app |
| At least 4 CG techniques | We use all 5 (section 7) |
| Mandatory Bangla comment style | Every function and important block |
| Live code change in viva | All values in `config.py`, modular files |
| Part 1: Problem discovery | Section 8 |
| Part 3: Reflection | Collected in `tracker.md` (stuck points, lessons, discoveries) |

**Career track:** Track C (interactive scene / animation). It can also be argued as Track A, because it's a real-time sync UI.

## 5. Goals

1. Show each person's status clearly with animation, no text reading needed.
2. Sync status between two computers within about 2 seconds.
3. Use all 5 required CG techniques in a way that makes sense, not forced.
4. Be easy to explain and modify live in a 6-minute viva.

## 6. Non-goals (v1)

- More than two users
- Login or accounts (a simple config setting says who you are)
- Mobile or web versions
- Sound
- Detailed decoration (plants, posters, and books stay minimal)
- Automatically detecting AI usage (the toggle is manual)

## 7. CG techniques used

| Technique | Where | Real-world connection |
|---|---|---|
| Line and shape drawing | All furniture, characters, outlines, light rays (own Bresenham/DDA) | Google Maps, vector graphics |
| 2D transformations | Walking (translation), mirrored room (reflection), walk bob and sit squash (scaling) | Game engines, animation |
| Color fill | Messy blanket and rug interiors (own boundary/flood fill), glow circles (own scanline circle fill) | Photoshop paint bucket |
| Line clipping | Lamp light rays clipped to the room with own Cohen-Sutherland, so light never crosses the divider | GPU rendering pipeline |
| Bezier curves | The character's walking path from bed to desk (own cubic Bezier) | Font design, car modelling, animation paths |

**Rule:** the algorithms in the table are written by hand in `algorithms.py`, not taken from a library. The viva will ask about them.

## 8. Part 1: Problem discovery answers

1. **Career track:** Track C: game / graphics industry or freelancing.
2. **Project idea:** a real-time pixel-art status board for a shared AI account. It is shown as two bedrooms where characters sleep or work.
3. **CG concepts:** the 5 techniques in section 7.
4. **Two real-world systems using similar techniques:**
   - **Gather.town:** a 2D pixel-art virtual office. Avatars move around rooms and show who is present. It uses sprite drawing, transformations, and real-time sync.
   - **Slack / Discord presence:** status indicators (online, busy, away) solve the same "is the other person busy?" problem, synced in real time across devices.

## 9. User stories

| # | As a… | I want to… | So that… |
|---|---|---|---|
| U1 | user | flip a toggle when I start using the account | my friend knows I'm working |
| U2 | user | see my friend's character asleep or at the desk | I know if the account is free |
| U3 | user | see the change animate | the status change is obvious and fun |
| U4 | user | see how long each of us worked today | we can share time fairly |
| U5 | user | get a clear warning if we're both working | we stop clashing |
| U6 | user | keep using the app offline with keys | a bad connection doesn't break the demo |
| U7 | presenter | open a debug view | I can show the Bezier curve and clipping in the viva |

## 10. Functional requirements

| ID | Requirement |
|---|---|
| F1 | Draw two mirrored rooms as described in `design.md` |
| F2 | Each character has states: `IN_BED`, `WALKING_TO_DESK`, `SITTING`, `WORKING`, `WALKING_TO_BED` |
| F3 | Toggle on → full animation to desk. Toggle off → full animation back to bed |
| F4 | Toggling during an animation reverses it smoothly from where the character is |
| F5 | Monitor and lamp turn on only after the character sits. They turn off before the character stands |
| F6 | Blanket is neat when someone is in bed, messy otherwise |
| F7 | Panel shows icon, status, toggle, and two time cards |
| F8 | Clicking the toggle changes only **your own** status (set with `--me`) |
| F9 | Keys `1` and `2` toggle Samee and Rifat locally (offline / demo mode) |
| F10 | Time counter: today's total per person, live while working, resets at midnight (Asia/Dhaka) |
| F11 | Sync: your status goes to Supabase when you toggle. The app reads both statuses every ~1.5 s |
| F12 | Conflict: both working → warning text and blinking red lamps |
| F13 | Key `D` shows the debug overlay, `ESC` quits |

## 11. Non-functional requirements

| ID | Requirement |
|---|---|
| N1 | Smooth animation, target 60 fps, minimum 30 |
| N2 | Network calls never freeze the window |
| N3 | Remote changes appear within about 3 s |
| N4 | Works without the internet in local mode |
| N5 | Every visual number and color lives in `config.py` |
| N6 | Every function has the mandatory Bangla comment block |
| N7 | Runs on Windows with Python 3.10+ |

## 12. Success criteria

- Both states match the mockup closely.
- Two laptops show the same state after a toggle.
- The presenter can answer "what happens if I delete this line?" for any line in `algorithms.py`, `character.py`, and `lighting.py`.
- A live change (color, speed, curve point) takes under 30 seconds.

## 13. Risks

| Risk | Plan |
|---|---|
| freeglut missing on Windows | Fix in Phase 1 before anything else |
| Too slow drawing thousands of quads in Python | Cache the static room in a display list (see techspec) |
| No internet in the viva room | Local mode with keys `1` and `2` |
| Can't explain code written by Claude Code | After each phase, review and explain it back (see plan.md) |
| Anyone with the Supabase key could change status | Acceptable for a two-person prototype. Mention it as the "weakest part" if asked |
