# Ops & Release Guide

How chore-tracker gets built, versioned, and deployed. Two repos are involved:

| Repo | Role |
|------|------|
| **`fisherrjd/chore-tracker`** (this one) | Builds & publishes the Docker image to GHCR via GitHub Actions (`.github/workflows/docker-publish.yml`). |
| **`fisherrjd/ops`** | Consumes a published image tag. `svc/chore-tracker.nix` pins `image = "ghcr.io/fisherrjd/chore-tracker:<tag>"`; `hex.k8s.services.build` renders the k8s manifests. |

The ops repo **builds nothing** — it only points at an already-published tag. There is no GitLab anywhere; it's all GitHub Actions + GHCR.

---

## What the pipeline publishes

The version is read from `version` in `pyproject.toml` — the single source of truth. The workflow triggers on every branch push:

| You push… | Image tag produced | Use for |
|-----------|--------------------|---------|
| merge to `main` | `:X.Y.Z` (immutable) | **releases — pin this in ops** |
| any other branch | `:X.Y.Z-b<short-sha>` (e.g. `0.3.5-b1a2b3c`) | testing a build on the cluster before release |

On a `main` build CI also tags the merge commit `vX.Y.Z` in git, then bumps the patch in `pyproject.toml` and commits it back (`[skip ci]`), so `main` always sits on the next unreleased version. Every tag is immutable — nothing moves — so any pin in ops is reproducible by construction.

---

## Versioning (SemVer)

Versions are `MAJOR.MINOR.PATCH`:

- **PATCH** (`0.2.0 → 0.2.1`) — backward-compatible **bug fixes only**. Automatic: every merge to `main` ships the current version and bumps the patch.
- **MINOR** (`0.2.0 → 0.3.0`) — new backward-compatible **features**. Set `version` in `pyproject.toml` in the PR (e.g. `0.3.9 → 0.4.0`); CI ships it, then auto-bumps to `0.4.1`.
- **MAJOR** (`0.x → 1.0.0`) — breaking changes. Same as minor: edit `version` in the PR.

We're in `0.x`, where the API is considered unstable, but we still follow the minor-for-features / patch-for-fixes convention.

**Reusing a version is blocked, not just discouraged.** Once `:X.Y.Z` is published it's frozen, and a `main` build whose `pyproject.toml` version already exists in GHCR **fails the guard step** instead of overwriting it. If that fires, bump `version` and re-merge.

---

## Cut a release

Releases happen on merge to `main` — there is no manual `git tag` step.

1. **Patch release:** just land your work on `main` (PR or merge). Nothing else — `main` already holds the version about to ship.
2. **Minor/major release:** in your PR, bump `version` in `pyproject.toml` (e.g. `0.3.9 → 0.4.0`), then merge.

On merge, CI publishes `:X.Y.Z`, tags `vX.Y.Z` in git, and bumps the patch on `main` for next time.

**Verify** before deploying: check the Actions run is green and the tag exists on the GHCR package page (`https://github.com/fisherrjd/chore-tracker/pkgs/container/chore-tracker`). The version you just shipped is the one that *was* in `pyproject.toml` before the auto-bump — see the `chore: release vX.Y.Z` commit on `main`.

---

## Deploy to the cluster

In **`fisherrjd/ops`**, edit `svc/chore-tracker.nix`:

```nix
, image ? "ghcr.io/fisherrjd/chore-tracker:0.3.4"
```

Then, from the ops repo, preview with `hex --dryrun -t specs.nix` and apply with `hex`. The deployment pulls the new image (ensure the image actually changed tag — k8s won't re-pull an identical tag without `imagePullPolicy: Always` + a rollout restart).

---

## Test a feature branch on the cluster (no release)

1. Push the branch — CI builds `:X.Y.Z-b<short-sha>` (the in-development version with the commit appended).
2. Temporarily point `svc/chore-tracker.nix` at that tag and apply with `hex`.
3. When done, revert ops to the pinned release tag.

> Note: every branch push builds an image, so `*-b<sha>` images accumulate in GHCR. Set a retention/cleanup policy on the package, or narrow the `branches:` filter in the workflow if it gets noisy.

---

## App runtime notes

- **Config** lives at `/data/config.yaml` (mounted from `hostPath: /var/lib/chore-tracker`, via `CHORE_CONFIG`). The `config.yaml` baked into the image is only a default — the mounted file wins, and editing it (or using the in-app **Settings** page) does not require a redeploy.
- **Notifications** are driven by an in-process APScheduler inside the web server (not a k8s CronJob). They only fire while the pod is running, at the times in `notify_times`, in the configured `timezone` (America/Denver). With `replicas: 1` this is correct; scaling up would duplicate notifications since each replica runs its own scheduler.
- **Timezone:** the image installs OS `tzdata` (the slim base lacks it) so `zoneinfo` can resolve `America/Denver`.
- **Logs** are structured (logfmt) to stdout — view with `kubectl logs`. Key events: `app.startup`, `scheduler.jobs_scheduled`, `notify.run_start/sent/send_failed/run_complete`.
