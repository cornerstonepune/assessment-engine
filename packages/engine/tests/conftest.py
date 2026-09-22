"""Every test runs against the local copy of the database, never the live one (ADR 0025).

This runs before any test module is imported, so before anything can connect. Importing `engine.core.db`
reads the repo's `.env`; `DATABASE_URL` is then pointed at the copy `bin/testdb` builds on this Mac,
and the run stops outright if that copy is anywhere else. Subprocesses a test starts (`bin/engine
…`) inherit the same address.
"""

import os

import pytest

from engine.core import db

if os.environ.get("TEST_DATABASE_URL"):
    try:
        os.environ["DATABASE_URL"] = db.local_copy()
    except RuntimeError as refused:
        pytest.exit(str(refused), returncode=4)
elif os.environ.get("DATABASE_URL"):
    # This machine can reach a real database but names no copy: stop, rather than test on it.
    pytest.exit(
        "refusing to run tests: DATABASE_URL is set but TEST_DATABASE_URL is not — run bin/testdb "
        "and add TEST_DATABASE_URL to .env",
        returncode=4,
    )


@pytest.fixture
def every_kind_trusted(monkeypatch):
    """ADR 0032's gate out of the way: every kind of question as if the reader had earned 95% on it, so
    a test about marking or signing off measures that and not the reader's standing on the copy."""
    from engine.w3_read import profiles

    monkeypatch.setattr(
        profiles,
        "kind_trust",
        lambda conn, window=50: {f: {"n": 50, "right": 50, "trusted": True} for f in profiles.KIND_WORDS},
    )
