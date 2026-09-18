# The engine as a service (ADR 0008). Multi-stage: uv resolves and installs into a venv in the
# builder stage; the runtime stage copies only that venv and the source, so the final image
# carries no compiler toolchain and no uv cache.
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/
WORKDIR /app

# Dependencies first, so an unchanged pyproject.toml/uv.lock reuses this layer on every
# source-only rebuild — the network-heavy step happens once, not on every `docker build`.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY engine ./engine
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

# opencv-python-headless still links against these at import time even without a display.
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY engine ./engine
ENV PATH="/app/.venv/bin:$PATH" ENGINE_POOL=1 PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "engine.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
