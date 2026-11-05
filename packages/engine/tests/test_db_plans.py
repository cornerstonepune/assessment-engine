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


def test_the_websites_role_never_compiles_a_query(conn):
    """A page's queries take milliseconds; compiling one to machine code first takes hundreds (JIT, worth it only for
    long reports). Postgres compiles whatever it guesses is costly, and a function that returns rows is guessed at 100
    or 1,000 of them — `jsonb_array_elements`, which a migration cannot correct as it corrected `pii.read_child`. A
    skill's page counted its mistakes in a query guessed at 8,730,000 rows for 3,530: 366 ms of compiling for 40 ms of
    work on a laptop, 4 s on CI's runner, and the page's heading missed its 5 s (PR #213's browser job on 3135c85).
    So the website's own role does not compile at all (migration 20261117090000)."""
    settings = conn.execute(
        "select coalesce(array_agg(x), '{}') as s from pg_db_role_setting d, unnest(d.setconfig) x"
        " where d.setrole = 'app_web'::regrole and d.setdatabase = 0"
    ).fetchone()["s"]
    assert "jit=off" in settings, settings


def _plan_analyzed(conn, query):
    return conn.execute(f"explain (analyze, format json) {query}").fetchone()["QUERY PLAN"][0]["Plan"]


def _rows_read(plan, relation):
    """Rows the plan took from `relation`, summed over every node that scans it."""
    own = plan["Actual Rows"] * plan["Actual Loops"] if plan.get("Relation Name") == relation else 0
    return own + sum(_rows_read(p, relation) for p in plan.get("Plans", []))


def test_a_classs_answers_are_read_from_its_own_children_not_from_every_answer_in_the_school(conn):
    """`answer_placed` groups the evidence by child. Asked for a class as `child_id in (select …)`, Postgres cannot
    reach below the grouping, so it grouped every answer in the school before keeping the class's: the skill page of a
    class of 40 took 1.1 s in CI (PR #353, run 41684713465) for a query that, asked as `child_id = any(array(select
    …))`, reads the class's rows only. These hold the shape the website's loaders use (`lib/queries-results.ts`)."""
    tenant = conn.execute("select id from tenant limit 1").fetchone()["id"]
    rung = conn.execute("select rung_code from skill where rung_code is not null limit 1").fetchone()[
        "rung_code"
    ]
    skill = conn.execute("select code from registry_skill limit 1").fetchone()["code"]
    for section, answers in (("PLAN-A", 3), ("PLAN-B", 600)):
        child = conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s, '1', %s, 'G2') returning id",
            (tenant, section),
        ).fetchone()["id"]
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
            " confirmed_by) select %s, %s, %s, %s, true, 'item', now(), 'plan test' from generate_series(1, %s)",
            (tenant, child, skill, rung, answers),
        )
    conn.execute("analyze evidence_event")
    conn.execute(
        "set local enable_seqscan = off"
    )  # the question is what the query can reach, not what a tiny table costs
    asked = (
        "select a.child_id from answer_placed a where a.confirmed_by is not null and a.child_id"
        " {} (select id from child where active and section = 'PLAN-A'{})"
    )
    narrowed = _plan_analyzed(conn, asked.format("= any(array", ")"))
    assert _rows_read(narrowed, "evidence_event") <= 3, "only the class's own three answers are read"
    widened = _plan_analyzed(conn, asked.format("in", ""))
    assert _rows_read(widened, "evidence_event") >= 603, (
        "the old shape reads them all (this is what the test guards)"
    )


def test_the_websites_class_loaders_ask_for_answers_by_equality():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[3] / "apps/web/lib/queries-results.ts").read_text()
    assert "answers(sql`a.child_id in (" not in source, (
        "a.child_id = any(array(select …)) reaches below the view's grouping"
    )
