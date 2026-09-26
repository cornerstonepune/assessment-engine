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

# OpenCV links against libGL and glib at import time even without a display; the digit reader's PaddlePaddle
# against the GNU OpenMP runtime (ADR 0035).
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY engine ./engine
ENV PATH="/app/.venv/bin:$PATH" ENGINE_POOL=1 PYTHONUNBUFFERED=1
# The printed page a question-bank screen shows is drawn by Playwright, and so is a week's pack.
# Without a browser in the image both answer 500 on the server while working on a laptop.
RUN playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
# The digit reader's models (~135 MB) are fetched here, once, so the first scan does not wait on a download and a
# server that cannot reach the model host still reads. Loading them is also the proof the reader starts at all.
RUN python -c "from engine.adapters import digits; digits._load()"

EXPOSE 8000
CMD ["uvicorn", "engine.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
