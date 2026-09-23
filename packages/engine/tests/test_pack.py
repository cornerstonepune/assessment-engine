"""The week's pack (BUILD-ORDER U4): the engine makes a class's papers, a teacher approves them, and only
then do they print — as one PDF, in handout order, spares last. Against the real schema, rolled back."""

import os

import pymupdf
import pytest

from engine.core import db
from engine.w2_print import assemble, pack, prescribe

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET, SECTION, WEEK = "SUB.2D2D", "PACKTEST", "U4-W1"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def made(conn, tmp_path):
    """Three children in a section of their own, rolls given out of order, their week made and rendered."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    for roll in ("10", "2", "1"):
        conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G2')",
            (tenant, roll, SECTION),
        )
    prescribe.for_class(conn, SECTION, WEEK, SET)
    built = assemble.for_week(conn, SECTION, WEEK)
    assemble.render(conn, built, tmp_path / "made", WEEK, "a test")
    return built


def _pages(pdf):
    with pymupdf.open(pdf) as doc:
        return doc.page_count


def test_a_pack_prints_only_once_a_teacher_has_approved_it(conn, made, tmp_path):
    with pytest.raises(PermissionError, match="wait for a teacher"):
        pack.pdf(conn, SECTION, WEEK, "practice", tmp_path)
    with pytest.raises(ValueError, match="name a person"):
        pack.approve(conn, SECTION, WEEK, "practice", "")

    out = pack.approve(conn, SECTION, WEEK, "practice", "Ms Educator")
    assert out["named"] == 3 and out["spares"] == len(made["spares"])
    assert (
        pack.approve(conn, SECTION, WEEK, "practice", "someone else")["sheets"] == 0
    )  # a second tap moves nothing

    pdf = pack.pdf(conn, SECTION, WEEK, "practice", tmp_path)
    papers = pack.papers(conn, SECTION, WEEK, "practice")
    assert {p["approved_by"] for p in papers} == {"Ms Educator"}
    assert _pages(pdf) == sum(_pages(p["pdf_path"]) for p in papers)


def test_the_pack_is_in_handout_order_and_the_spares_come_last(conn, made):
    papers = pack.papers(conn, SECTION, WEEK, "practice")
    assert [p["roll_no"] for p in papers if p["child_id"]] == ["1", "2", "10"]
    assert len(papers) == 3 + len(made["spares"])
    assert all(p["child_id"] is None for p in papers[3:])


def test_a_pack_with_no_papers_says_so(conn, tmp_path):
    with pytest.raises(LookupError, match="no papers"):
        pack.pdf(conn, SECTION, "NO-SUCH-WEEK", "practice", tmp_path)
