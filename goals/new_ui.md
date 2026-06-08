# TODO: Mobile-First UI for Chore Tracker

Goal: a clean, snappy UI that fits perfectly on an iPhone (test against 390x844px and up). Native feel, no desktop clutter.

This app is a **rotation scheduler**, not a flat to-do list. Keep that model front of mind:

- **Rooms** each own a list of tasks (defined on `/rooms`, persisted to `config.yaml`).
- **Members** are the people in rotation (`/members`).
- The **schedule** assigns each member a room per day and rotates so every room is covered each half-cycle. The home page (`/`) shows today's assignments plus an upcoming table.
- A per-member **daily checklist** (`/checklist/{member}`) shows the tasks for *that member's room today*, with checkboxes. This is the screen people actually open each day.
- **Settings** (`/settings`) manages notification times; ntfy reminders fire on a cron.

So there are two "list" surfaces — the **schedule** (read-only rotation) and the **checklist** (tappable tasks) — and three **config** pages (rooms, members, settings) that are add/remove forms. Don't collapse these into a single flat list.

Stack: FastAPI + Jinja2 templates + one `static/style.css`. No React, no build step. Every action is currently a POST→303 redirect (`redirect()` in `chore_tracker/main.py`), so the whole UI is server-rendered.

If reloads start feeling clunky, the checklist and the add/remove forms are the first places HTMX would help (swap a row in place instead of reloading). Alpine.js can handle small client-only toggles. Both are one script tag, no build — don't add either until reloads actually bug you. The checklist already auto-submits on checkbox change (`onchange="this.form.submit()"`), so it's the obvious HTMX candidate.

---

## Design Principles

Apply these globally in `static/style.css` and `templates/base.html`, on every screen:

- **Aesthetic:** minimalist and modern. Soft ambient dark or light background, not pure black or white. Desaturated accents (slate, deep indigo, or sage green). No neon.
- **Box sizing:** set `box-sizing: border-box` globally so padded elements never overflow the screen.
- **Layout:** use flexbox or grid freely (this renders in a real browser, no engine limits). Target small screens with `@media (max-width: 480px)`.
- **No horizontal scroll:** zero horizontal overflow on `body`. Everything wraps. Watch the schedule and members/settings `<table>`s — wide tables are the most likely thing to overflow on a phone (see Schedule section below).

---

## Checklist

### 1. Layout and Viewport (global — `base.html` / `style.css`)

- [x] **Viewport meta tag:** present in `base.html`; added `viewport-fit=cover` so the safe-area insets actually resolve. Did not add `user-scalable=no`.
- [x] **Page padding:** `main.page` uses `15px` root padding on phones (`@media max-width:480px`).
- [x] **Safe area insets:** header pads `env(safe-area-inset-top)`; `body`/`.page` pad `env(safe-area-inset-bottom)`.

### 2. Header and Nav (`base.html`)

- [x] **Sticky header:** compact sticky top bar with a muted slate (`--header-bg: #2e3a35`) background; brand + four nav links live here.
- [x] **Header typography:** brand is 17px (16px on mobile).
- [x] **Mobile nav:** on phones the header drops to two tidy rows — brand, then the four links as an even, full-width tab strip (`flex:1` each). No horizontal scroll.
- [x] **Active state:** active link gets a lighter background plus an inset accent underline so it's clearly distinct on the dark bar.

### 3. Schedule — home page (`index.html`)

This is the rotation view, read-only. It is **not** where chores get added.

- [x] **Today's assignments:** each person → room is now a full-width card that is itself an `<a>` to `/checklist/{member}` (single column on phones).
- [x] **Summary indicator:** `home()` computes a `done_map`; cards show a "{done}/{total} done" pill that turns desaturated green (`.is-complete`) when the room is fully done.
- [x] **Upcoming table:** wrapped in `.table-scroll` (overflow-x within its own container, with edge fade hints). The body never scrolls sideways.
- [x] **Cycle marker:** `.cycle-dot` bumped to 7px and tinted with the accent so it stays legible.
- [x] **Notify button:** full-width `.btn-notify` on phones for an easy thumb target.
- [x] **Empty state:** the "No rooms or members" state now renders as an intentional bordered card, not a bare line.

### 4. Checklist — the daily core experience (`checklist.html`)

This is the screen to optimize hardest. Tasks come from the member's assigned room; they are **not** added or deleted here.

- [x] **Task rows:** `.check-row` is full-width and the whole row is the tap target.
- [x] **Done state:** checked tasks keep the strikethrough + muted `.is-done` look.
- [x] **Immediate feedback:** unchanged — still `onchange="this.form.submit()"`. (HTMX left for later, per the goal's guidance not to add it until reloads bug us.)
- [x] **Progress label:** promoted to a dedicated `.checklist-progress` line (room name + right-aligned, accent-when-complete count).
- [x] **Tappable targets:** rows are `min-height: 48px`, checkbox enlarged to 1.3rem, `border-radius: 8px`.
- [x] **Body font:** task rows render at 1rem (16px).
- [x] **Empty states:** both "No room assigned" and "no tasks defined" render in styled `.empty-state` cards.

### 5. Config pages — rooms / members / settings

These are the add/remove surfaces. There is **no single global "add chore" bar** — adds are contextual:

- [x] **Add forms:** `.add-task-form` / `.form-row` kept as input + button rows.
- [x] **Input font size:** both `input[type="text"]` and `input[type="time"]` set to `16px` (was `.9rem`, which let iOS zoom).
- [ ] **Sticky add bar (rooms only, optional):** left out — optional, and the goal says don't bother unless reloads bug us. Easy to add later.
- [x] **Delete pattern:** per-row `.btn-danger` and the `confirm()` dialogs are untouched.
- [x] **Members/settings tables:** both wrapped in `.table-scroll` so they pan within their container, not the body.

### 6. Visual Polish (global)

- [x] **Drop heavy borders:** no left accent bars; rows use soft bottom dividers and the `.card` paneling.
- [x] **Scroll behavior:** `body { overflow-x: hidden }` plus per-container table scroll means no sideways body scroll. The `base.html` scroll-restore script is untouched.
- [x] **Tappable targets everywhere:** `.btn` is `min-height: 44px`; `.btn-danger` is `min-height/width: 44px`.
- [x] **Flash messages:** `.flash` lives in `main.page`, so it sits below the sticky header and pushes content down rather than covering it.
