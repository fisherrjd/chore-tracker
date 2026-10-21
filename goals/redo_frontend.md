# Migrate chore-tracker frontend: Jinja2 → Vue 3 + shadcn-vue (TypeScript)

## Context

The chore-tracker UI is today a set of server-rendered Jinja2 templates
(`templates/*.html`) with one monolithic hand-written stylesheet
(`static/style.css`, ~610 lines) and ~44 lines of inline vanilla JS. Every
interaction is a POST→303-redirect→GET round trip, with flash messages passed as
`?msg=&kind=` query params. The goal is a modern client-side app: **Vue 3 +
shadcn-vue + TypeScript + Vite + Tailwind**, talking to FastAPI as a JSON API.

Confirmed decisions:
- **Toolchain:** **Bun** manages the frontend (install, dev server, Vite build,
  shadcn-vue CLI) — added to the Nix dev shell as a single `bun` package. No
  separate Node install.
- **Serving:** one container. A Bun build stage compiles the SPA to `dist/`;
  FastAPI serves it (static assets + a catch-all that returns `index.html` for
  SPA routes) and exposes `/api/*`. Deployment stays single-replica, config stays
  a mounted `config.yaml` — `OPS.md`/CI flow unchanged.
- **Cutover:** full replacement. Add the JSON API, build all 5 pages, switch
  FastAPI to serve the SPA, then delete `templates/` and the HTML/form routes.
  Jinja and Vue never ship together.
- **Design:** adopt shadcn-vue's default (neutral) theme — a visual refresh, not
  a port of the sage-green look.

### Hard constraints (must not break)
- **Deep link:** ntfy notifications set `Click` →
  `{dashboard_url}/checklist/{member}` (`chore_tracker/notifier.py:28`). The Vue
  router **must** keep `/checklist/{member}` as a client route (history mode), and
  the catch-all must serve `index.html` for it. `notifier.py` needs no change.
- **Single source of truth for config** stays `config.yaml` via `load_config`/
  `save_config`; every request still re-reads from disk. No business-logic
  rewrite — the API layer wraps existing functions.
- **Python test suite must not require a frontend build** — serving the SPA must
  degrade gracefully when `dist/` is absent (dev/test).

## Approach (4 phases)

### Phase 1 — Add the JSON API (additive, backend only)

Add `/api/*` routes in `chore_tracker/main.py` that wrap the existing helpers
(`load_config`, `save_config`, `config_to_dict`, `get_schedule`,
`get_assignment`, `get_day_index`, `get_done`, `set_done`, `notify_today`). Reuse
the `_save_notify_times`, `_todays_room` helpers already there. Replace the
redirect/flash convention with proper HTTP status + JSON bodies (`{"detail": …}`
on 400/404/409) — the SPA renders these as toasts.

Proposed surface (mirrors current pages 1:1):

| Method | Path | Wraps / returns |
|---|---|---|
| GET | `/api/home` | today's assignments + per-person `{done,total}` + 14-day schedule + `half_cycle` + `notify_times` (the `home()` context, as JSON) |
| GET | `/api/schedule` | **exists** — keep; optionally add `day_index` |
| GET | `/api/rooms` | `[{name, tasks}]` |
| POST | `/api/rooms` | body `{name}`; 409 if exists/empty |
| DELETE | `/api/rooms/{name}` | remove room |
| POST | `/api/rooms/{name}/tasks` | body `{task}`; 404/409 on bad room/dup |
| DELETE | `/api/rooms/{name}/tasks/{task}` | remove task |
| GET | `/api/members` | `{members:[{name,topic,ntfy_url}], ntfy_base_url}` |
| POST | `/api/members` | body `{name}` |
| DELETE | `/api/members/{name}` | remove member |
| GET | `/api/settings` | `{notify_times, timezone}` |
| POST | `/api/settings/notify-times` | body `{time}`; 400 on bad HH:MM |
| DELETE | `/api/settings/notify-times/{time}` | remove time |
| GET | `/api/checklist/{member}` | `{member, room_name, tasks, done:[]}`; 404 unknown member |
| POST | `/api/checklist/{member}` | body `{tasks:[]}`; records only valid tasks |
| POST | `/api/notify/today` | `{sent:[], failed:[]}` |

Use Pydantic request/response models so FastAPI emits an OpenAPI schema the
frontend types can be derived from (or mirrored by hand).

### Phase 2 — Scaffold the Vue app

New `frontend/` directory at repo root:
```
frontend/
  package.json  tsconfig*.json  vite.config.ts  tailwind.config / index.css
  components.json            # shadcn-vue config
  index.html
  src/
    main.ts  App.vue
    router.ts               # vue-router, history mode
    lib/api.ts              # typed fetch client (one place for /api calls + errors)
    types.ts                # Room, Member, AppConfig, ScheduleDay … mirror config.py
    components/ui/*          # shadcn-vue generated (button, card, table, input,
                            #   checkbox, dialog, sonner/toast …)
    views/
      HomeView.vue          # today cards + 14-day table + "Send notifications"
      RoomsView.vue         # rooms + tasks CRUD
      MembersView.vue       # members + ntfy links CRUD
      SettingsView.vue      # notify-times CRUD
      ChecklistView.vue     # /checklist/:member  (auto-save on toggle)
```
- **Stack:** Vue 3 `<script setup>` + TS, Vite, Tailwind, shadcn-vue (Reka UI),
  vue-router. No Pinia — the app is small; per-view `ref` + composables suffice.
- **Routes:** `/`, `/rooms`, `/members`, `/settings`, `/checklist/:member`
  (history mode). Nav mirrors current `base.html` header.
- **Flash → toast:** replace `?msg=&kind=` with shadcn-vue toasts driven by API
  success/error.
- **Checklist:** `v-model` checkboxes, debounced POST to
  `/api/checklist/:member` (replaces the `onchange="form.submit()"` hack).
- **Dev proxy:** `vite.config.ts` proxies `/api` → `http://localhost:3030` so
  `bun run dev` (5173) + `python main.py` (3030) run side by side.
- **shadcn-vue setup:** `bunx shadcn-vue@latest init`, then add components with
  `bunx shadcn-vue@latest add <component>`.
- **Build output:** Vite `build.outDir` → a dir FastAPI serves (e.g.
  `frontend/dist`).

### Phase 3 — FastAPI serves the SPA

In `chore_tracker/main.py`:
- Mount built assets: `app.mount("/assets", StaticFiles(directory=DIST/"assets"))`.
- Add a **catch-all** `GET /{full_path:path}` (registered last, after all `/api`
  routes) that returns `FileResponse(DIST/"index.html")` — this resolves
  `/checklist/{member}` and every other SPA route.
- **Graceful degradation:** if `DIST/index.html` is missing (no build, e.g. test
  env), return 404/plain message instead of erroring, so the Python suite and bare
  `python main.py` still work without a build.
- Remove the old `templates` Jinja2 wiring and the `/static` mount once Phase 4
  deletes those assets.

### Phase 4 — Delete the old frontend

- Delete `templates/` (all 6 `.html`) and `static/style.css`.
- Remove the HTML-rendering + `Form(...)` routes from `main.py` (`home`,
  `rooms_page`, `add_room`, `delete_room`, `add_task`, `delete_task`,
  `members_page`, `add_member`, `delete_member`, `settings_page`,
  `add_notify_time`, `delete_notify_time`, `checklist`, `update_checklist`,
  `send_today`) — superseded by `/api/*`. Drop the `redirect()` helper,
  `Jinja2Templates`, and the now-unused `Form` import.

## Supporting changes

- **`Dockerfile`** → multi-stage:
  1. `oven/bun:1`: `COPY frontend/`, `bun install --frozen-lockfile`,
     `bun run build` → `dist`.
  2. existing `python:3.13-slim`: `COPY --from=build … dist`; **drop** the
     `templates/` and `static/` COPY lines. CMD unchanged.
  CI (`.github/workflows/docker-publish.yml`) is pyproject-version-driven and
  builds the Dockerfile — no workflow edit needed; just verify the build.
- **`default.nix`** → add `bun` to the dev-shell `tools` so
  `bun install`/`bun run dev` work in the Nix shell. (CLAUDE.md's "no `uv`" rule
  is about the Python app; Bun is the new frontend toolchain.)
- **Tests** (`tests/`): `test_web.py` exercises the HTML/form routes and will
  break under full replacement — rewrite it against `/api/*` JSON. Keep
  `test_scheduler.py`, `test_config.py`, etc. as-is. `tests/conftest.py`
  (sets `CHORE_BASE`/`CHORE_CONFIG`) is unaffected; the catch-all must tolerate a
  missing `dist/` so `client` fixture GETs don't fail. Frontend unit tests
  (vitest) optional — keep light or defer.
- **`.dockerignore` / `.gitignore`**: ignore `frontend/node_modules`,
  `frontend/dist`; commit `frontend/bun.lock` for reproducible installs.
- **`CLAUDE.md`**: update the architecture/commands sections (new `frontend/`,
  `bun` commands, API-based routes) after the migration lands.

## Critical files

- `chore_tracker/main.py` — add `/api/*`, add SPA serving, later delete HTML routes.
- `chore_tracker/config.py` — read-only reference for the TS `types.ts` (`Member`,
  `Room`, `AppConfig`); no change expected.
- `chore_tracker/notifier.py:28` — **don't break** the `/checklist/{member}`
  deep link; no change.
- `Dockerfile`, `default.nix`, `tests/test_web.py` — see above.
- `frontend/**` — all new.
- `templates/**`, `static/style.css` — deleted in Phase 4.

## Verification

1. **Backend API (no build needed):** rewritten `pytest tests/test_web.py` green;
   full `pytest` green. Manually `python main.py` and `curl` a few endpoints
   (`GET /api/home`, `POST /api/rooms`, `POST /api/checklist/{member}`).
2. **Frontend dev:** in `frontend/`, `bun run dev`; with `python main.py` running,
   click through all 5 pages — add/delete a room+task, add/delete a member, add/
   delete a notify time, toggle checklist items (auto-save), "Send notifications".
   Confirm toasts replace flash messages.
3. **Deep link:** navigate directly to `/checklist/<member>` (the ntfy `Click`
   target) and confirm the SPA renders it via history-mode routing.
4. **Production parity:** `docker build .` (exercises the Bun build stage), run the
   image, hit `/` and `/checklist/<member>` — both served from the built SPA;
   `/api/*` returns JSON; static assets load from `/assets`.
5. **Deploy unchanged:** confirm the single-container, replicas:1, mounted
   `config.yaml` model still holds (no CI/OPS edits required).
