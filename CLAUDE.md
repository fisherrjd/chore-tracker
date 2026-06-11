# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-household chore tracker: a FastAPI + Jinja2 server that rotates rooms
among members on a daily round-robin and pushes [ntfy](https://ntfy.sh)
notifications with each person's assigned room and task list. Deployed as a
single-replica container on k8s (see `OPS.md`).

## Commands

The dev shell is provided by Nix + direnv (`.envrc` → `use nix`), which puts a
Python with all dependencies on `PATH`. Do **not** invoke `uv` to run, test, or
boot the app — the Nix-provided environment already has everything.

```bash
pytest                       # full suite (config in pyproject.toml: -q, testpaths=tests)
pytest tests/test_web.py     # one file
pytest tests/test_scheduler.py::test_name   # one test
python main.py               # run locally on http://0.0.0.0:3030 (reload=True)
```

There is no linter/formatter configured in this repo.

## Architecture

Request/notification flow centers on `chore_tracker/main.py` (the FastAPI app +
routes + APScheduler wiring). The supporting modules are deliberately small and
single-purpose:

- **`scheduler.py`** — pure rotation math, no I/O. `get_assignment(day_index,
  rooms, people)` is the core: a round-robin that requires
  `len(rooms) % len(people) == 0`. Over `n_rooms` days each person cleans every
  room once; every `n_rooms // n_people` days ("half cycle") all rooms are
  covered. Day index is `(today - start_date).days`.
- **`config.py`** — Pydantic `AppConfig` loaded from / saved to YAML. `today`
  and `tzinfo` are computed from the configured `timezone`, **not** the server
  clock, so "today" tracks the household's wall clock (UTC server, Denver
  household). `save_config` writes atomically via a `.tmp` + `replace`.
- **`notifier.py`** — builds and POSTs ntfy messages. Each member's topic is
  `name.lower()` appended to `ntfy_base_url`; the notification's `Click` header
  deep-links to that member's checklist on `dashboard_url`.
- **`checks.py`** — in-memory, process-local checklist state keyed by day_index.
  Intentionally **not** persisted: a restart clears it, and writing any day drops
  all other days, so completion never lingers past the current day.
- **`logging_config.py`** — logfmt formatter to stdout. App code emits
  structured events via `log.info("event.name", extra={...})`; new log lines
  should follow that `event.name` + `extra=` convention so `kubectl logs` stays
  parseable.

### Two state stores, by design

1. **Config (durable)** — rooms, members, notify times. Edited through the web
   UI, persisted to `config.yaml`. In production this is a mounted file at
   `/data/config.yaml` (env `CHORE_CONFIG`); the baked-in `config.yaml` is only a
   default. Every request re-reads config from disk via `load_config`.
2. **Checklist completion (ephemeral)** — `checks._state`, in-process, daily.

### Scheduling

Notifications fire from an in-process `AsyncIOScheduler`, not a k8s CronJob, so
they only run while the pod is up. `_reschedule()` rebuilds all cron jobs from
`notify_times` and is called both on startup and whenever notify times change in
Settings. This works **only at replicas: 1** — scaling out would duplicate every
notification, since each replica runs its own scheduler.

## Conventions & gotchas

- **Path resolution:** `CHORE_BASE` (templates/static root) and `CHORE_CONFIG`
  are read at *import time* in `main.py`. Tests set both in `tests/conftest.py`
  before importing the app and point at a throwaway temp config — never the real
  `config.yaml`.
- **Tests skip the lifespan:** the `client` fixture builds `TestClient(app)`
  without a `with` block on purpose, so the background scheduler never starts.
- **Routes are POST-redirect-GET:** mutations redirect (303) back to the page
  with `?msg=&kind=` query params for flash messages; the `redirect()` helper in
  `main.py` builds these.
- **Config back-compat:** `AppConfig` migrates the legacy single `notify_time`
  string to `notify_times`, and normalizes/dedupes/sorts times — preserve this
  when touching the model.
- **Python 3.13** required (`requires-python`).

## Releases & deploy

Full process is in `OPS.md`. The version lives in `pyproject.toml` (the single
source of truth) and CI (`.github/workflows/docker-publish.yml`) is
pyproject-driven, not tag-driven:

- **Merge to `main`** → publishes `ghcr.io/fisherrjd/chore-tracker:X.Y.Z`
  (immutable), tags `vX.Y.Z` in git, then bumps the patch in `pyproject.toml` and
  commits it back (`[skip ci]`). So `main` always sits on the *next* unreleased
  version, and the just-shipped version is the one in the `chore: release vX.Y.Z`
  commit.
- **Push any other branch** → publishes `:X.Y.Z-b<short-sha>` for cluster testing.

Patch releases are automatic on merge; for a minor/major, bump `version` in
`pyproject.toml` in the PR before merging. A `main` build whose version already
exists in GHCR **fails a guard step** rather than overwriting it — bump and
re-merge. Deploy by pinning the immutable `:X.Y.Z` in `fisherrjd/ops`
(`svc/chore-tracker.nix`) and applying with `hex` (`hex --dryrun -t specs.nix`,
then `hex`).
