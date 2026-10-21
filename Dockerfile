# Stage 1 — build the Vue SPA
FROM oven/bun:1 AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/bun.lock* ./
RUN bun install --frozen-lockfile
COPY frontend/ .
RUN bun run build

# Stage 2 — Python app
FROM python:3.13-slim

# tzdata: slim image has no IANA tz database, needed by zoneinfo for the
# configured timezone (e.g. America/Denver).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies (cached layer — only reruns when lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application code
COPY chore_tracker/ ./chore_tracker/
COPY main.py ./

# Bake in a default config — override at runtime:
#   -v ./config.yaml:/app/config.yaml
COPY config.yaml ./

# Built SPA from the first stage
COPY --from=frontend-build /build/dist ./frontend/dist/

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 3030

CMD ["python", "main.py"]
