# Chore Tracker

## What it is

A household chore tracker for one home. It rotates rooms among members day by
day, shows who cleans what today, gives each person a tick-off checklist, and
sends reminders through [ntfy](https://ntfy.sh). It also keeps shopping lists
(with optional item photos). The web app is a Vue single-page app served by the
same FastAPI process that provides the JSON API.

## Run it

Needs Python 3.13+ and Bun. The repo's Nix + direnv dev shell provides both.

```bash
# build the frontend once (the server serves frontend/dist/)
cd frontend && bun install --frozen-lockfile && bun run build && cd ..

# run the server on http://0.0.0.0:3030 (CHORE_PORT changes the port)
python main.py

# or run it the way the factory does
CHORE_CONFIG=/tmp/chore/config.yaml CHORE_NOTIFY=off \
  uvicorn chore_tracker.main:app --host 127.0.0.1 --port 3030
```

For frontend work, `cd frontend && bun run dev` starts Vite on port 3031 and
proxies `/api` to the backend on 3030 (`VITE_BACKEND` points it elsewhere).

Tests: `pytest`. Frontend acceptance tests: `cd frontend && bun run test:acceptance`.

Docker image and deploy steps are in [OPS.md](../OPS.md).

## Use it

- **Home (`/`)**: today's room for each member with a progress count, the
  14-day schedule, a "notify" button that sends today's reminders now, and the
  Full house clean button. A full clean splits every room between members for
  that day (balanced by task count) and notifies them; ending it returns to the
  normal rotation. It expires by itself the next day.
- **Lists (`/lists`)**: shopping lists such as "Groceries". Add items, mark them
  bought, clear bought items, and attach, replace or remove one photo per item
  (JPEG, PNG, WebP or GIF, up to 10 MB).
- **Rooms (`/rooms`)**: add and remove rooms and their tasks.
- **Members (`/members`)**: add and remove members. Each member has an ntfy
  topic (their lower-cased name) under the configured ntfy server.
- **Settings (`/settings`)**: add and remove daily notification times
  (`HH:MM`, in the configured timezone).
- **Checklist (`/checklist/<member>`)**: that member's rooms for today with
  their tasks; ticks save automatically. Reminder notifications link here.

The rotation needs the number of rooms to divide evenly by the number of
members. Checklist ticks are kept in memory only and reset when the server
restarts.

The full HTTP API is described in [openapi.json](../openapi.json).

## Configuration

Environment variables:

| Variable | Meaning | Default |
|---|---|---|
| `CHORE_CONFIG` | Path of the YAML config | `config.yaml` in `CHORE_BASE` |
| `CHORE_BASE` | Project root (where `frontend/dist` is) | current directory |
| `CHORE_LISTS` | Path of the shopping-lists YAML | `lists.yaml` beside the config |
| `CHORE_PHOTOS` | Directory for item photos | `list-photos/` beside the lists file |
| `CHORE_PORT` | Port for `python main.py` | `3030` |
| `CHORE_NOTIFY` | `off` disables the scheduler and all ntfy pushes | unset (notifications on) |

The config file (`config.yaml` in the repo is a working example) holds
`start_date`, `timezone` (default `America/Denver`), `ntfy_base_url` (default
`https://ntfy.sh`), `dashboard_url` (used for notification links),
`notify_times`, `members` and `rooms` (each with `tasks`). If the file does not
exist the app starts with no rooms or members; the UI and API write it as you
make changes.
