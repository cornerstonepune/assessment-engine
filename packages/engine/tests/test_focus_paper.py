"""A child's next paper chosen from the child's own graph, against the real schema, rolled back.

The child's checked answers go in as confirmed evidence; the graph is rebuilt from them exactly as a
sign-off rebuilds it; the plan and the paper are read back from there.
"""

import os
from pathlib import Path

import pytest

from engine.assess import graph
from engine.core import db
from engine.w2_print import focus_paper

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

WEEK = "T3W1-focus-test"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def child(conn):
    """A Grade 3 child whose checked papers show: 3-digit − 3-digit mostly wrong, taking the smaller digit from
    the larger again and again; 2-digit + 2-digit 5 of 8; 2-digit + 1-digit all right."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1','FOCUSTEST','G3') returning id",
        (tenant,),
    ).fetchone()["id"]
    answers = (
        [("NUM.OPS.02", "R31", False, ["M_SMALL_FROM_LARGE"])] * 4
        + [("NUM.OPS.02", "R31", False, [])] * 2
        + [("NUM.OPS.02", "R31", True, [])] * 2
        + [("NUM.OPS.01", "R22", True, [])] * 5
        + [("NUM.OPS.01", "R22", False, [])] * 3
        + [("NUM.OPS.01", "R21", True, [])] * 9
    )
    for skill, rung, right, mistakes in answers:
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, observed_at, confirmed_by) values (%s,%s,%s,%s,%s,%s,'item',now(),'test')",
            (tenant, cid, skill, rung, right, mistakes),
        )
    graph.rebuild(conn, str(cid))
    return str(cid)


def test_the_paper_is_random_bank_questions_from_the_weak_areas_at_their_level_never_seen_before(conn, child):
    seen = conn.execute(
        "select id from item where status = 'active' and skill_set_code = 'SUB.3D3D' and difficulty = 'Easy'"
        " order by item_key limit 40"
    ).fetchall()
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week)"
        " select tenant_id, %s, id, 'earlier' from item where id = any(%s)",
        (child, [r["id"] for r in seen]),
    )
    p = focus_paper.plan(conn, child, WEEK)
    # the subtraction weakness is worked on as subtraction, the weakest first; the secure skill is left alone
    assert [(a["skill_set"], a["level"]) for a in p["areas"]] == [
        ("SUB.3D3D", "Easy"),
        ("ADD.2D2D", "Medium"),
    ]
    assert p["n"] == 12 and [len(a["questions"]) for a in p["areas"]] == [6, 6]
    for a in p["areas"]:
        keys = [q["item_key"] for q in a["questions"]]
        rows = conn.execute(
            "select skill_set_code, difficulty, status from item where item_key = any(%s)", (keys,)
        ).fetchall()
        assert {(r["skill_set_code"], r["difficulty"], r["status"]) for r in rows} == {
            (a["skill_set"], a["level"], "active")
        }
    ids = {q["id"] for a in p["areas"] for q in a["questions"]}
    assert not ids & {str(r["id"]) for r in seen}, "a question the child has already been given came back"
    assert focus_paper.plan(conn, child, WEEK) == p, "the page and the printed paper must be the same plan"
    other = focus_paper.plan(conn, child, "T3W2-focus-test")
    assert {q["id"] for a in other["areas"] for q in a["questions"]} != ids, "drawn at random, week by week"


def test_questions_that_can_show_the_childs_own_repeated_mistake_come_first(conn, child):
    area = focus_paper.plan(conn, child, WEEK)["areas"][0]
    assert area["mistake"] == "M_SMALL_FROM_LARGE"
    assert "the same mistake more than once" in area["why"]
    assert all(q["shows_mistake"] for q in area["questions"]), area["questions"]


def test_making_the_paper_prints_it_with_its_qr_and_the_child_is_not_given_those_questions_again(conn, child):
    made = focus_paper.make(conn, child, WEEK, actor="test")
    inst = conn.execute(
        "select si.qr_code, si.pdf_path, si.key, t.source, t.child_id from sheet_instance si"
        " join sheet_template t on t.id = si.sheet_template_id where si.qr_code = %s",
        (made["qr"],),
    ).fetchone()
    assert inst["source"] == "focus" and str(inst["child_id"]) == child
    assert made["qr"].startswith("CS") and Path(inst["pdf_path"]).exists() and inst["key"]["pages"] >= 1
    given = {q["id"] for a in made["areas"] for q in a["questions"]}
    again = focus_paper.plan(conn, child, WEEK)
    assert not given & {q["id"] for a in again["areas"] for q in a["questions"]}


def test_the_paper_is_approved_in_the_name_of_whoever_made_it_and_only_once_a_week(conn, child):
    """The engine proposes; a person's click approves and prints it (BUILD-ORDER, U2). The approval names them,
    and a second approval in the same week is refused rather than printing a second next paper."""
    made = focus_paper.make(conn, child, WEEK, actor="teacher@school.test")
    inst = conn.execute(
        "select print_status, approved_by, approved_at from sheet_instance where qr_code = %s", (made["qr"],)
    ).fetchone()
    assert inst["approved_by"] == "teacher@school.test" and inst["approved_at"] is not None
    assert inst["print_status"] == "printed"
    with pytest.raises(ValueError, match=made["qr"]):
        focus_paper.make(conn, child, WEEK, actor="teacher@school.test")
    assert focus_paper.approved(conn, child, WEEK)["qr"] == made["qr"]
    assert focus_paper.approved(conn, child, "another-week") is None
