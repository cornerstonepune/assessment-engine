"""What F1g would close, measured before it ships (goals/f1g-approval-gates-papers.yaml, ADR 0073 decision 5).

A level whose questions are not approved is to go on no paper. Before any educator meets that refusal, the levels it
would close are named to Nimish, read from live: for every class on the roll, each level its papers may draw on today
(taught in the class, its grade's or below) whose questions the coordinator has not approved. Nothing is written.
"""

import os

import pytest

from engine.core import db
from engine.w2_print import shelf
from tests.test_cli import run

BY = "F1G Coordinator"


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def _class(conn, section, band):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1',%s,%s)", (tenant, section, band)
    )


def test_each_class_is_told_the_levels_its_papers_would_lose(conn):
    """A Grade 2 class is taught addition (the school's switch). 2-digit + 1-digit's Easy is approved, its Medium is
    not: Medium is named for the class, Easy is not. A level above the class's grade is not named — its papers never
    drew on it — nor is a skill the class has not been taught."""
    _class(conn, "F1G-TWO", "G2")
    conn.execute(
        "update skill_set set level_approved = jsonb_build_object('Easy', jsonb_build_object('by', %s::text, 'at', now()))"
        " where code = 'ADD.2D1D'",
        (BY,),
    )
    rows = [r for r in shelf.closing(conn) if r["class"] == "F1G-TWO"]
    mine = {(r["skill"], r["level"]) for r in rows}
    assert ("ADD.2D1D", "Medium") in mine and ("ADD.2D1D", "Easy") not in mine
    assert not [r for r in rows if r["skill"] == "MUL.MODELS"], (
        "not taught in the class: its papers never had it"
    )
    usable = shelf._levels(conn, "G2")
    assert all(r["level"] in usable[r["skill"]] for r in rows), "only levels the class's grade uses"
    medium = next(r for r in rows if (r["skill"], r["level"]) == ("ADD.2D1D", "Medium"))
    n = conn.execute(
        "select count(*) as n from item where skill_set_code = 'ADD.2D1D' and difficulty = 'Medium'"
        " and status = 'active'"
    ).fetchone()["n"]
    assert (medium["grade"], medium["questions"]) == ("G2", n)


def test_the_command_lists_them_and_writes_nothing():
    """`engine week unapproved`, run against live from anywhere, names what would close and changes nothing."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        before = c.execute("select count(*) as n, max(updated_at) as at from skill_set").fetchone()
    r = run("week", "unapproved")
    assert r.exit_code == 0, r.output_plain
    assert "would close" in r.output_plain
    with db.connect() as c:
        assert c.execute("select count(*) as n, max(updated_at) as at from skill_set").fetchone() == before
