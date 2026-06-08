# Ops & Release Guide

How chore-tracker gets built, versioned, and deployed. Two repos are involved:

| Repo | Role |
|------|------|
| **`fisherrjd/chore-tracker`** (this one) | Builds & publishes the Docker image to GHCR via GitHub Actions (`.github/workflows/docker-publish.yml`). |
| **`fisherrjd/ops`** | Consumes a published image tag. `svc/chore-tracker.nix` pins `image = "ghcr.io/fisherrjd/chore-tracker:<tag>"`; `hex.k8s.services.build` renders the k8s manifests. |

The ops repo **builds nothing** — it only points at an already-published tag. There is no GitLab anywhere; it's all GitHub Actions + GHCR.

---

## What the pipeline publishes

The workflow triggers on every branch push and on `v*` tag pushes. `docker/metadata-action` derives the image tags:

| You push… | Image tag(s) produced | Use for |
|-----------|-----------------------|---------|
| commit to `main` | `:main-latest` (rolling) + `:main-<sha>` (immutable) | latest dev / staging |
| any other branch `X` | `:X-b<sha>` (slashes slugified, e.g. `feat-foo-b1a2b3c`) | testing a feature branch on the cluster |
| git tag `vX.Y.Z` | `:X.Y.Z` (immutable) + `:X.Y` (moving minor pointer) | **releases — pin these in ops** |

Always pin an **immutable** tag in ops (`:0.3.0` or `:main-<sha>`), never a moving one (`:0.3`, `:main-latest`), so a redeploy is reproducible.

---

## Versioning (SemVer)

Versions are `MAJOR.MINOR.PATCH`:

- **PATCH** (`0.2.0 → 0.2.1`) — backward-compatible **bug fixes only**.
- **MINOR** (`0.2.0 → 0.3.0`) — new backward-compatible **features**.
- **MAJOR** (`0.x → 1.0.0`) — breaking changes.

We're in `0.x`, where the API is considered unstable, but we still follow the minor-for-features / patch-for-fixes convention.

**Rule: never move or reuse a published tag.** Once `vX.Y.Z` is pushed and CI has built `:X.Y.Z`, that version is frozen. If you tagged a commit too early, bump to the next version rather than force-moving the tag — two images sharing one version number causes deploys you can't reason about.

**Don't name a branch the same as a tag.** `git push origin v0.2.0` becomes ambiguous when both `refs/heads/v0.2.0` and `refs/tags/v0.2.0` exist ("src refspec matches more than one"). Branches are working/throwaway; tags are the permanent artifacts. Disambiguate with `git push origin tag v0.2.0` or `git push origin refs/tags/v0.2.0` if you ever must.

---

## Cut a release

```bash
# 1. Land the work on main (PR or merge), then:
git checkout main && git pull

# 2. Tag the main tip with the new version
git tag v0.3.0

# 3. Push ONLY the tag (the 'tag' keyword keeps it unambiguous)
git push origin tag v0.3.0
```

This fires the workflow on the tag ref and publishes `:0.3.0` and `:0.3`.

**Verify** before deploying: check the Actions run is green and the tag exists on the GHCR package page (`https://github.com/fisherrjd/chore-tracker/pkgs/container/chore-tracker`).

---

## Deploy to the cluster

In **`fisherrjd/ops`**, edit `svc/chore-tracker.nix`:

```nix
, image ? "ghcr.io/fisherrjd/chore-tracker:0.3.0"
```

Commit ops, then apply your hex/k8s manifests. The deployment pulls the new image (ensure the image actually changed tag — k8s won't re-pull an identical tag without `imagePullPolicy: Always` + a rollout restart).

---

## Test a feature branch on the cluster (no release)

1. Push the branch — CI builds `:<branch>-b<sha>`.
2. Temporarily point `svc/chore-tracker.nix` at that tag and apply.
3. When done, revert ops to the pinned release tag.

> Note: every branch push builds an image, so `*-b<sha>` images accumulate in GHCR. Set a retention/cleanup policy on the package, or narrow the `branches:` filter in the workflow if it gets noisy.

---

## App runtime notes

- **Config** lives at `/data/config.yaml` (mounted from `hostPath: /var/lib/chore-tracker`, via `CHORE_CONFIG`). The `config.yaml` baked into the image is only a default — the mounted file wins, and editing it (or using the in-app **Settings** page) does not require a redeploy.
- **Notifications** are driven by an in-process APScheduler inside the web server (not a k8s CronJob). They only fire while the pod is running, at the times in `notify_times`, in the configured `timezone` (America/Denver). With `replicas: 1` this is correct; scaling up would duplicate notifications since each replica runs its own scheduler.
- **Timezone:** the image installs OS `tzdata` (the slim base lacks it) so `zoneinfo` can resolve `America/Denver`.
- **Logs** are structured (logfmt) to stdout — view with `kubectl logs`. Key events: `app.startup`, `scheduler.jobs_scheduled`, `notify.run_start/sent/send_failed/run_complete`.
