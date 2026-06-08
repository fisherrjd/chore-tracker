FROM python:3.13-slim

# tzdata: the slim image ships no IANA tz database, which `zoneinfo` needs to
# resolve the configured timezone (e.g. America/Denver) for "today".
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# Pull uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (cached layer — only reruns when lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY chore_tracker/ ./chore_tracker/
COPY templates/     ./templates/
COPY static/        ./static/
COPY main.py        ./

# Bake in a default config — override at runtime by mounting your own:
#   -v ./config.yaml:/app/config.yaml
COPY config.yaml ./

# Run as non-root
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 3030

CMD ["python", "main.py"]
