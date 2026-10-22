"""A consent and data register (goals/c6-consent-and-data-register.yaml, slice C6).

BUILD-ORDER, the locked scope of 22 Oct: "a consent and data register: what is kept about a child, why, how long, who
sees it, in a parent's words". The register is `data_register`, written from the seed; a parent's answer is `consent`.
"""

import json
import os

import psycopg
import pytest

from engine.core import db
from tests.rows import a_child, tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SEED = json.loads((db.REPO_ROOT / "supabase/seed/data_register.json").read_text())["data_register"]
# Tables of a child's own that carry no child_id column: they reach the child through a paper.
THROUGH_A_PAPER = {"public.child", "public.capture", "public.item_result"}
# Words a parent should not have to read in their own register.
JARGON = ("evidence", "rung", "skill_", "table", "row", "database", "pii", "uuid", "ocr", "model", "child_id")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _consent(conn, child, decision="given"):
    return conn.execute(
        "insert into consent (tenant_id, child_id, decision, given_by, how, recorded_by)"
        " values (%s, %s, %s, 'mother', 'a signed form', 'the coordinator') returning *",
        (tenant(conn), child, decision),
    ).fetchone()


def test_every_table_that_holds_a_childs_data_is_in_the_register(conn):
    """What is kept about a child: every table with a child's id, and those reached through a paper, is in an entry,
    and every table an entry names exists."""
    holding = {
        r["t"]
        for r in conn.execute(
            "select c.table_schema || '.' || c.table_name as t from information_schema.columns c"
            " join information_schema.tables t using (table_schema, table_name)"
            " where c.column_name = 'child_id' and t.table_type = 'BASE TABLE' and c.table_schema in ('public', 'pii')"
        ).fetchall()
    } | THROUGH_A_PAPER
    named = {t for r in conn.execute("select tables from data_register").fetchall() for t in r["tables"]}
    assert holding - named == set(), "a table holds a child's data and the register does not say so"
    existing = {
        r["t"]
        for r in conn.execute(
            "select table_schema || '.' || table_name as t from information_schema.tables"
            " where table_schema in ('public', 'pii')"
        ).fetchall()
    }
    assert named - existing == set()


def test_each_entry_says_what_why_how_long_and_who_sees_it_in_a_parents_words(conn):
    rows = conn.execute(
        "select code, what, why, how_long, who_sees from data_register order by ord"
    ).fetchall()
    assert [r["code"] for r in rows] == [e["code"] for e in SEED]
    for r in rows:
        for field in ("what", "why", "how_long", "who_sees"):
            words = r[field]
            assert words.strip() and words == next(e[field] for e in SEED if e["code"] == r["code"])
            assert not [j for j in JARGON if j in words.lower()], (r["code"], field, words)


def test_a_parents_consent_is_recorded_against_the_register_as_it_stood(conn):
    """Given, then withdrawn: two rows, the latest the child's answer; each names the register it answered, and a
    register changed since reads as changed. A consent is never edited, and holds no name."""
    child = a_child(conn)
    given = _consent(conn, child)
    assert given["register"]
    now = db.one(conn, "select decision, register_unchanged from consent_now where child_id = %s", (child,))
    assert dict(now) == {"decision": "given", "register_unchanged": True}
    _consent(conn, child, "withdrawn")
    assert (
        db.one(conn, "select decision from consent_now where child_id = %s", (child,))["decision"]
        == "withdrawn"
    )
    conn.execute("update data_register set why = why || ' (changed)' where code = 'name'")
    assert not db.one(conn, "select register_unchanged as u from consent_now where child_id = %s", (child,))[
        "u"
    ]
    with pytest.raises(psycopg.Error), conn.transaction():
        conn.execute("update consent set decision = 'given' where child_id = %s", (child,))
    columns = {r["column_name"] for r in conn.execute(
        "select column_name from information_schema.columns where table_name = 'consent'").fetchall()}  # fmt: skip
    assert not columns & {"name", "first_name", "last_name", "parent_name"}


def test_a_consent_needs_its_answer_who_gave_it_how_and_who_recorded_it(conn):
    child = a_child(conn)
    for bad in (
        "insert into consent (tenant_id, child_id, decision, given_by, how, recorded_by)"
        " values (%s, %s, 'maybe', 'mother', 'a form', 'the coordinator')",
        "insert into consent (tenant_id, child_id, decision, given_by, how, recorded_by)"
        " values (%s, %s, 'given', ' ', 'a form', 'the coordinator')",
        "insert into consent (tenant_id, child_id, decision, given_by, how, recorded_by)"
        " values (%s, %s, 'given', 'mother', 'a form', '')",
    ):
        with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
            conn.execute(bad, (tenant(conn), child))
