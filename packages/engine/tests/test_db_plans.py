"""A page's query is planned as what it reads.

Postgres guesses that a function returning a table returns 1,000 rows unless the function says otherwise.
`pii.read_child` returns one row, a child's name, and every page that lists children reads it once per child. The
Children page's query was guessed at 24,000 rows for 24 children, cost 653,786, so Postgres compiled it to machine
code (JIT) before running it: 2,057 ms of compiling for 25 ms of work on a laptop, and past the page's 8 s on CI's
runner, where `/growth` said "This page could not load" (main's browser job on 3d07f66, 2026-10-15). Migration
20261116090000 says the one row; these hold it.
"""

import pytest

from engine.core import db


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _plan(conn, query):
    return conn.execute(f"explain (format json) {query}").fetchone()["QUERY PLAN"][0]["Plan"]


def test_a_function_that_returns_one_row_says_so(conn):
    rows = {
        r["sig"]: r["prorows"]
        for r in conn.execute(
            "select oid::regprocedure::text as sig, prorows from pg_proc"
            " where oid in ('pii.read_child(uuid,text)'::regprocedure, 'public.next_difficulty(uuid,text)'::regprocedure)"
        ).fetchall()
    }
    assert rows == {"pii.read_child(uuid,text)": 1, "next_difficulty(uuid,text)": 1}


def test_every_childs_name_is_planned_as_one_row_a_child_and_never_compiled(conn):
    """Listing the roll with each name is planned at the roll's own size, and cheaply enough that Postgres runs it
    rather than compiling it first."""
    roll = _plan(conn, "select c.id from child c where c.active")
    named = _plan(
        conn, "select p.first_name from child c, lateral pii.read_child(c.id, 'a plan') p where c.active"
    )
    assert named["Plan Rows"] == roll["Plan Rows"], "one name a child"
    jit_above = float(conn.execute("select current_setting('jit_above_cost') as v").fetchone()["v"])
    assert named["Total Cost"] < jit_above
