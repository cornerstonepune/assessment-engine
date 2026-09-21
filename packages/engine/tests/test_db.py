"""REPO_ROOT must not crash the whole engine at import time when the file layout is shallower
than the monorepo's own — which is exactly the Docker image's layout (Dockerfile copies only
`engine/`, so this file lands at /app/engine/db.py with nothing four levels above it). This broke
the very first container start: every route imports `engine.db` transitively, so an IndexError
here took down the whole process before a single request could be served."""

from pathlib import Path

from engine.db import _repo_root_for


def test_the_monorepo_layout_finds_the_real_repo_root():
    # .../assessment-engine/packages/engine/engine/db.py -> .../assessment-engine
    fake = Path("/Users/x/cornerstone/assessment-engine/packages/engine/engine/db.py")
    assert _repo_root_for(fake) == Path("/Users/x/cornerstone/assessment-engine")


def test_the_containers_shallow_layout_does_not_raise():
    # Dockerfile: COPY engine ./engine -> /app/engine/db.py, nothing four levels up
    fake = Path("/app/engine/db.py")
    assert _repo_root_for(fake) == Path("/app")  # a harmless fallback, not a crash


def test_an_even_shallower_layout_still_does_not_raise():
    fake = Path("/db.py")
    assert _repo_root_for(fake) == Path("/")
