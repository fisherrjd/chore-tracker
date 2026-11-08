# AGENTS.md

## What this is

A single-household chore tracker: a FastAPI JSON API server that rotates rooms among members on a daily round-robin and pushes [ntfy](https://ntfy.sh) notifications. The frontend is a Vue 3 SPA on Jade's theme (`@fisherrjd/ui`) served by FastAPI. Deployed as a single-replica container on k8s (see `OPS.md`).

## Commands

The dev shell is provided by Nix + direnv (`.envrc` → `use nix`), which puts Python and Bun on `PATH`. Do **not** invoke `uv` to run, test, or boot the Python app — the Nix-provided environment already has everything.

```bash
# Python / backend
pytest                       # full suite (config in pyproject.toml: -q, testpaths=tests)
pytest tests/test_web.py     # one file
pytest tests/test_scheduler.py::test_name   # one test
python main.py               # run backend on http://0.0.0.0:3030 (reload=True; CHORE_PORT to move it)

# Frontend (from frontend/)
bun install                  # install / sync deps
bun run dev                  # Vite dev server on :3031, proxies /api → :3030 (VITE_BACKEND to move it)
bun run build                # production build → frontend/dist/
ui-update                    # devshell: pull the latest @fisherrjd/ui, typecheck; commit frontend/bun.lock
```

There is no linter/formatter configured in this repo.

## Architecture

### Backend (`chore_tracker/`)

Request/notification flow centers on `chore_tracker/main.py` (FastAPI app + `/api/*` routes + APScheduler wiring). The supporting modules are deliberately small and single-purpose:

- **`scheduler.py`** — pure rotation math, no I/O. `get_assignment(day_index, rooms, people)` is the core: a round-robin that requires `len(rooms) % len(people) == 0`. Day index is `(today - start_date).days`.
- **`config.py`** — Pydantic `AppConfig` loaded from / saved to YAML. `today` and `tzinfo` are computed from the configured `timezone`, **not** the server clock. `save_config` writes atomically via a `.tmp` + `replace`. `dashboard_url` is used by `notifier.py` for the `Click` deep-link header.
- **`notifier.py`** — builds and POSTs ntfy messages. Each member's topic is `name.lower()` appended to `ntfy_base_url`; the notification's `Click` header deep-links to `{dashboard_url}/checklist/{member}`.
- **`checks.py`** — in-memory, process-local checklist state keyed by day_index. Intentionally **not** persisted.
- **`lists.py`** — household shopping lists (named lists like "Costco" or "Target", each holding items with a `done` flag), persisted to their own YAML file (`lists.yaml` beside the config, or `CHORE_LISTS`). Pure load/save + small Pydantic models; the `/api/lists` routes in `main.py` do the mutations.
- **`photos.py`** — pure helpers for list-item photos: `sniff` (magic-byte type check, no Pillow), `save`/`remove` (atomic write, `<uuid4hex>.<ext>` names), `NAME_RE`, `MAX_BYTES` (10 MB). Files live in `PHOTOS_DIR` (`CHORE_PHOTOS`, default `list-photos/` beside `lists.yaml`), created on first upload.
- **`logging_config.py`** — logfmt formatter to stdout. App code emits structured events via `log.info("event.name", extra={...})`.

### Frontend (`frontend/`)

Vue 3 SPA: `<script setup>` + TypeScript, Vite, Tailwind CSS v4, vue-router (history mode), built on
Jade's theme: `@fisherrjd/ui` (the npm package, version in `frontend/package.json`, resolved in `bun.lock`) supplies the app frame
(`AppShell`, `PageHeader`), the shadcn-vue primitives, the empty/error/confirm states and the theme.
The look is the `ui({ … })` call in `vite.config.ts` (lagoon palette, block style, Cascadia Code,
pinned light). Use theme tokens (`text-success`, `bg-warning`, …), never Tailwind palette colors.

```
frontend/
  package.json            bun deps (@fisherrjd/ui from npm)
  vite.config.ts          Vite + @tailwindcss/vite + ui() theme + /api proxy
  tsconfig*.json
  src/
    main.ts  App.vue      App.vue = AppShell + nav
    router.ts             vue-router, history mode; /styleguide is dev-only
    lib/api.ts            typed fetch client (all /api/* calls)
    lib/photo.ts          shrinkPhoto (canvas re-encode only if >900 KB or >1280 px) + uploadPhoto
    lib/utils.ts          cn() (from @fisherrjd/ui) + uid()
    types.ts              TS types mirroring the backend models
    assets/index.css      tailwind + @fisherrjd/ui/styles.css (+ app-only CSS)
    components/           domain patterns from app-template (checklist, forms, …)
    views/
      HomeView.vue        today cards + 14-day schedule + notify button
      ListsView.vue       shopping lists: items, bought toggles, clear bought, item photos (thumbnail, viewer dialog, attach-on-add)
      RoomsView.vue       rooms + tasks CRUD
      MembersView.vue     members CRUD + ntfy links
      SettingsView.vue    notify-times CRUD
      ChecklistView.vue   /checklist/:member (debounced auto-save)
```

`/styleguide` (the theme lab) exists only under `bun run dev`; builds never include it.

### JSON API (`/api/*`)

All mutations accept JSON bodies and return JSON. Errors use `{"detail": "..."}` with appropriate HTTP status.

| Method | Path | Description |
|---|---|---|
| GET | `/api/home` | today's assignments + done_map + 14-day schedule |
| GET | `/api/schedule` | 14-day schedule |
| GET/POST | `/api/rooms` | list rooms / add room |
| DELETE | `/api/rooms/{name}` | remove room |
| POST | `/api/rooms/{room}/tasks` | add task |
| DELETE | `/api/rooms/{room}/tasks/{task}` | remove task |
| GET/POST | `/api/members` | list / add member |
| DELETE | `/api/members/{name}` | remove member |
| GET | `/api/settings` | notify_times + timezone |
| POST | `/api/settings/notify-times` | add notify time |
| DELETE | `/api/settings/notify-times/{time}` | remove notify time |
| GET | `/api/checklist/{member}` | today's checklist + done list |
| POST | `/api/checklist/{member}` | record completed tasks |
| POST | `/api/notify/today` | fire notifications now |
| GET/POST | `/api/lists` | shopping lists / add list |
| DELETE | `/api/lists/{name}` | remove list |
| POST | `/api/lists/{list}/items` | add item (re-adding a bought one puts it back) |
| PUT | `/api/lists/{list}/items` | set an item's bought state (`{item, done}`) |
| DELETE | `/api/lists/{list}/items/{item}` | remove item |
| POST | `/api/lists/{list}/clear` | drop bought items |
| PUT | `/api/lists/{list}/photo` | multipart `item`+`file`: set/replace the item's photo (404 list, 404 item, 413, 415) |
| DELETE | `/api/lists/{list}/photo/{item}` | remove the item's photo |
| GET | `/api/photos/{name}` | serve a photo (immutable cache; strict name regex, else 404 JSON) |

List JSON items are `{name, done, image_url}`; `image_url` is `/api/photos/<file>` or null. Removing an item, clearing bought items or removing a list deletes their photo files.

### Three state stores, by design

1. **Config (durable)** — rooms, members, notify times. Persisted to `config.yaml`. In production this is a mounted file at `/data/config.yaml` (env `CHORE_CONFIG`).
2. **Checklist completion (ephemeral)** — `checks._state`, in-process, daily.
3. **Shopping lists (durable, not config)** — `lists.yaml` beside the config
   file by default (override with env `CHORE_LISTS`). Kept separate so
   shopping churn never rewrites `config.yaml`. A missing file seeds one empty
   "Groceries" list in memory; an existing empty file stays empty. Every
   request re-reads it via `load_lists`; writes are atomic like config.

### SPA serving

FastAPI serves the built SPA:
- `/assets/*` → `frontend/dist/assets/` (conditional mount, skipped if absent)
- `/{full_path:path}` catch-all → `frontend/dist/index.html` (404 gracefully if not built)

Vue Router handles client-side routing for `/`, `/rooms`, `/members`, `/settings`, `/checklist/:member`. The `/checklist/{member}` route is the ntfy notification deep-link target.

### Scheduling

Notifications fire from an in-process `AsyncIOScheduler`. Works **only at replicas: 1**.

**`CHORE_NOTIFY=off`** turns notifications off entirely: the scheduler is not started and `_reschedule` adds no jobs (so the notify-time routes still work but schedule nothing), and `notify_today` logs `notify.disabled` and POSTs nothing. `/api/notify/today` still answers `{"sent": [], "failed": []}`. Unset or any other value keeps the normal behaviour. The env var is checked at call time (`notifier.notify_disabled()`).

## Decisions

- One photo per item, uploaded (not a pasted URL), settable on add and later (add/replace/remove). A photo is a reference shot for shoppers; replacing is simpler than a gallery.
- File inputs are `<input type="file" accept="image/*">` with **no** `capture`, so phones get camera/gallery and computers a file dialog.
- The browser shrinks big photos (<~900 KB) so the default 1 MB ingress limit works; the server accepts up to 10 MB.

## Conventions & gotchas

- **Photo routes:** `GET /api/photos/{name:path}` must stay `:path` so traversal attempts 404 here instead of falling to the SPA catch-all. Validate order on upload: list, item, size, type.
- **Frontend multipart:** `lib/api.ts` must not set a JSON Content-Type for `FormData`. A non-JSON 413 (ingress) becomes "Photo is too big for the server".
- **Buttons in forms:** every non-submit button in `ListsView.vue` needs `type="button"`; the viewer dialog renders outside any `<form>`.
- **Acceptance tests:** `cd frontend && bun run test:acceptance` (Playwright from Nix, linked into `node_modules` by `scripts/acceptance.sh`; not a dep, tests live in `frontend/tests/acceptance/`).

- **Path resolution:** `CHORE_BASE` and `CHORE_CONFIG` are read at *import time* in `main.py`. Tests set both in `tests/conftest.py` before importing the app.
- **Tests skip the lifespan:** the `client` fixture builds `TestClient(app)` without a `with` block so the scheduler never starts during tests.
- **SPA in tests:** `tests/conftest.py` points `CHORE_BASE` at a temp dir with a stub `frontend/dist/index.html`, so the catch-all is tested without a frontend build. All API tests use `/api/*` routes explicitly.
- **Test photos:** `fresh_state` also wipes `PHOTOS_DIR`; tests generate tiny images themselves.
- **Test helpers (`tests/helpers.py`):** `default_config()` seeds a known-good config (2 members: Alice/Bob, 4 rooms, `America/Denver` timezone, today as `start_date` so `day_index = 0`). `write_config()` writes a raw dict to the temp config file. Both are called by the `autouse` `fresh_state` fixture — every test starts from this baseline.
- **`goals/`** — planning/design markdown files, not code.
- **Config back-compat:** `AppConfig` migrates the legacy single `notify_time` string to `notify_times`.
- **Python 3.13** required (`requires-python`).

## Releases & deploy

Full process is in `OPS.md`. The version lives in `pyproject.toml` (single source of truth). CI (`.github/workflows/docker-publish.yml`) is pyproject-version-driven. **Merge to `main`** → publishes `ghcr.io/fisherrjd/chore-tracker:X.Y.Z`, tags git, bumps patch. Patch releases are automatic; for minor/major, bump `version` in `pyproject.toml` before merging.

The Dockerfile is multi-stage: Bun builds the SPA to `frontend/dist/`; Python stage copies it in. CMD unchanged.

## Factory

`factory.toml` at the repo root is the recipe for jade's software factory (factory.jade.rip). The factory reads it from `main` only, never from a PR branch, so changes to it take effect once merged. Its checks, each run with `bash -c` from the repo root, are:

1. `cd frontend && bun install --frozen-lockfile`
2. `cd frontend && bun run build` (typechecks too)
3. `pytest`

Serving for acceptance tests and PR previews both set `CHORE_NOTIFY=off`, so they never send real ntfy pushes. The served app runs on an initially missing `CHORE_CONFIG` file (no rooms or members); the preview uses the image's baked `config.yaml`.
