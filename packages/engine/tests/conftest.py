"""Every test runs against the local copy of the database, never the live one (ADR 0025).

This runs before any test module is imported, so before anything can connect. Importing `engine.core.db`
reads the repo's `.env`; `DATABASE_URL` is then pointed at the copy `bin/testdb` builds on this Mac,
and the run stops outright if that copy is anywhere else. Subprocesses a test starts (`bin/engine
…`) inherit the same address.
"""

import os
import sys
import types
from pathlib import Path

import pytest

from engine.core import db

# `spylls` (the en_GB dictionary an English sample is spelt against) installs a stray package called `tests` into
# site-packages, which would stand in for this folder, so `from tests.rows import …` finds no `rows`. This folder is
# `tests`, named here before any test module is imported.
sys.modules["tests"] = types.ModuleType("tests")
sys.modules["tests"].__path__ = [str(Path(__file__).parent)]

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
    a test about marking or signing off measures that and not the reader's standing on the copy. The spot-check
    (step 4) is set to none: its sample is keyed on ids a test makes afresh each run, so 15% of it would pick a
    different answer to hold every time — its own test sets the rate it measures."""
    from engine.w3_read import marking, profiles

    monkeypatch.setattr(
        profiles,
        "kind_trust",
        lambda conn: {f: {"n": 50, "right": 50, "trusted": True, "to_trust": 0} for f in profiles.KIND_WORDS},
    )
    monkeypatch.setattr(marking, "spot_rate", lambda conn: 0.0)


def _row_counts() -> dict | None:
    """{table: its row count} for every table of the test database, or None when no test database is in use."""
    if not os.environ.get("DATABASE_URL"):
        return None
    with db.connect(db.dsn()) as c:
        tables = [
            f"{r['schemaname']}.{r['tablename']}"
            for r in c.execute(
                "select schemaname, tablename from pg_tables where schemaname in ('public', 'pii')"
                " order by 1, 2"
            )
        ]
        sql = " union all ".join(f"select '{t}' as t, count(*) as n from {t}" for t in tables)
        return {r["t"]: r["n"] for r in c.execute(sql)}


@pytest.fixture(scope="module")
def forgets_what_it_commits():
    """For a module whose tests run commands, or open connections of their own, that commit rows (M0-04c): at the end
    of the module every row made since it began is deleted, in every table that stamps `created_at`, with the
    append-only triggers and foreign keys off for that transaction (`session_replication_role`; the tests' role may).
    Names the work it undoes, so that a module opts in and the check below still fails for one that does not. A table
    that does not stamp `created_at` is not reached, and the check says so."""
    with db.connect(db.dsn()) as c:
        since = c.execute("select clock_timestamp() as t").fetchone()["t"]
    yield
    with db.connect(db.dsn()) as c:
        c.execute("set local session_replication_role = replica")
        for r in c.execute(
            "select col.table_schema as s, col.table_name as t from information_schema.columns col"
            " join information_schema.tables x on x.table_schema = col.table_schema and x.table_name = col.table_name"
            " where col.column_name = 'created_at' and col.table_schema in ('public', 'pii')"
            " and x.table_type = 'BASE TABLE'"
        ).fetchall():
            c.execute(f'delete from {r["s"]}."{r["t"]}" where created_at >= %s', (since,))
        c.commit()


@pytest.fixture(autouse=True, scope="module")
def a_module_leaves_no_committed_row(request):
    """A test runs in a transaction it rolls back, so it leaves the database as it found it (M0-04c). A module that
    commits a row, whether the test or a command it starts does it, leaves it for every module that runs after it on
    that database: on 2026-11-04 an item with no skill set, left by an earlier shard, failed seven tests of another.
    The row counts of every table are taken before the module and after it, and any difference fails the module's
    last test. `ISOLATION_REPORT=<file>` appends what each module left to that file instead, to measure."""
    before = _row_counts()
    yield
    after = _row_counts()
    if before is None or after is None:
        return
    left = {t: after[t] - before.get(t, 0) for t in after if after[t] != before.get(t, 0)}
    if not left:
        return
    if report := os.environ.get("ISOLATION_REPORT"):
        import json

        with open(report, "a") as f:
            f.write(json.dumps({"module": request.module.__name__, "left": left}) + "\n")
        return
    pytest.fail(
        f"{request.module.__name__} left committed rows (table: rows added): {left}. A test must roll back "
        "what it writes (`conn.rollback()` in its fixture), or clean up what a command it starts commits.",
        pytrace=False,
    )
