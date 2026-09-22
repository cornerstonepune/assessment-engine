"""Tests never touch the live database (ADR 0025).

The suite used to write to the one database the live website reads; on 2026-09-21 that stalled it
for minutes at a time and once left an approval on real sheets. `conftest.py` now points every test
at `TEST_DATABASE_URL`, the local copy `bin/testdb` builds, before any test connects.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

from engine.core import db

ENGINE = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="no database here (CI)")
def test_every_test_connects_to_the_local_copy():
    url = db.dsn()
    assert urlparse(url).hostname in ("127.0.0.1", "localhost")
    assert url == os.environ["TEST_DATABASE_URL"]


def test_the_suite_refuses_to_start_when_the_test_database_is_not_on_this_machine():
    remote = "postgresql://postgres.x:pw@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_verify.py"],
        cwd=ENGINE,
        env={**os.environ, "TEST_DATABASE_URL": remote},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode != 0
    assert "refusing to run tests against a database that is not on this machine" in p.stdout + p.stderr
