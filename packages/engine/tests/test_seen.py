"""Before anything prints, an educator sees the paper, and asks for different questions as often as they like
(goals/preview-before-print.yaml). Nimish, 2026-10-21: "a teacher can only see the assessment when they print".

A preview, and every different draw of it, writes nothing; printing after it prints exactly the questions it showed,
or nothing at all when the paper would no longer be those questions. Against the real schema, rolled back.
"""

import os

import pytest

from engine.assess import graph
from engine.core import db
from engine.w2_print import focus_paper, maker, seen

WEEK = "T3W1-seen-test"
SECTION = "SEENTEST"
BY = "educator@school.test"
EASY = [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 4}]
# what a paper that prints writes; a preview writes none of it
WRITTEN = ("sheet_instance", "sheet_template", "item_exposure", "prescription")


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def _child(conn, roll, answers=()):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G3') returning id",
        (tenant, roll, SECTION),
    ).fetchone()["id"]
    for skill, rung, right, mistakes in answers:
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, observed_at, confirmed_by) values (%s,%s,%s,%s,%s,%s,'item',now(),'test')",
            (tenant, cid, skill, rung, right, mistakes),
        )
    graph.rebuild(conn, str(cid))
    return str(cid)


@pytest.fixture
def kids(conn):
    """One child who takes the smaller digit from the larger again and again, and one who adds 2-digit numbers right."""
    weak = [("NUM.OPS.02", "R31", False, ["M_SMALL_FROM_LARGE"])] * 4 + [("NUM.OPS.02", "R31", True, [])] * 2
    return {
        "weak": _child(conn, "1", weak),
        "strong": _child(conn, "2", [("NUM.OPS.01", "R22", True, [])] * 10),
    }


def _ids(paper):
    return [q["id"] for a in paper["areas"] for q in a["questions"]]


def _counts(conn):
    return {t: conn.execute(f"select count(*) as n from {t}").fetchone()["n"] for t in WRITTEN}


def _printed(conn, qr):
    return [
        str(i)
        for i in conn.execute(
            "select st.item_ids from sheet_instance si join sheet_template st on st.id = si.sheet_template_id"
            " where si.qr_code = %s",
            (qr,),
        ).fetchone()["item_ids"]
    ]


def test_a_preview_and_different_questions_write_no_rows(conn, kids):
    before = _counts(conn)
    weak, picked = kids["weak"], [kids["weak"], kids["strong"]]
    home, other = focus_paper.plan(conn, weak, WEEK), focus_paper.plan(conn, weak, WEEK, draw=1)
    # different questions, never a different paper: the same skill at the same level, as many questions
    assert [(a["skill_set"], a["level"], len(a["questions"])) for a in other["areas"]] == [
        (a["skill_set"], a["level"], len(a["questions"])) for a in home["areas"]
    ]
    assert _ids(other) != _ids(home) and seen.of([other]) != seen.of([home])
    assert _ids(focus_paper.plan(conn, weak, WEEK, draw=1)) == _ids(other), (
        "the same draw is the same questions"
    )
    assert _ids(focus_paper.plan(conn, weak, WEEK, EASY, draw=1)) != _ids(
        focus_paper.plan(conn, weak, WEEK, EASY)
    )
    for way in ("same", "each", "own"):
        ask = None if way == "own" else EASY
        a = maker.plan(conn, SECTION, picked, WEEK, "practice", way, ask)
        b = maker.plan(conn, SECTION, picked, WEEK, "practice", way, ask, draw=1)
        assert not a["refused"] and not b["refused"]
        assert [_ids(p) for p in a["papers"]] != [_ids(p) for p in b["papers"]], way
    assert focus_paper.preview(conn, weak, WEEK, BY, draw=1).startswith(b"%PDF")
    assert _counts(conn) == before, "no sheet, no code, no approval, no question marked seen"


def test_printing_after_a_preview_prints_exactly_the_questions_previewed(conn, kids):
    weak = kids["weak"]
    shown = focus_paper.plan(conn, weak, WEEK, draw=2)
    made = focus_paper.make(conn, weak, WEEK, BY, draw=2, seen=seen.of([shown]))
    assert _printed(conn, made["qr"]) == _ids(shown), (
        "the home assessment shown, question for question, in order"
    )
    chosen = focus_paper.plan(conn, weak, WEEK, EASY, draw=3)
    made = focus_paper.make(conn, weak, WEEK, BY, EASY, draw=3, seen=seen.of([chosen]))
    assert _printed(conn, made["qr"]) == _ids(chosen), "a paper the educator chose, as shown"


def test_a_class_batch_prints_exactly_the_papers_previewed_after_different_questions(conn, kids):
    picked = [kids["weak"], kids["strong"]]
    for way in ("same", "each"):
        shown = maker.plan(conn, SECTION, picked, WEEK, "practice", way, EASY, draw=4)
        made = maker.make(
            conn, SECTION, picked, WEEK, "practice", way, BY, EASY, draw=4, seen=seen.of(shown["papers"])
        )
        printed = {
            str(r["child_id"]): r["qr_code"]
            for r in conn.execute(
                "select qr_code, child_id from sheet_instance where qr_code = any(%s)", (made["qrs"],)
            )
        }
        for p in shown["papers"]:
            assert _printed(conn, printed[p["child_id"]]) == _ids(p), (way, p["roll_no"])


def test_a_paper_whose_questions_changed_since_they_were_seen_is_refused_and_nothing_prints(conn, kids):
    weak, picked = kids["weak"], [kids["weak"], kids["strong"]]
    shown = focus_paper.plan(conn, weak, WEEK, EASY)
    focus_paper.make(conn, weak, WEEK, BY, EASY, seen=seen.of([shown]))
    before = _counts(conn)
    # those questions are the child's now, so the same choice draws others: the page shown is not what would print
    with pytest.raises(seen.Changed):
        focus_paper.make(conn, weak, WEEK, BY, EASY, seen=seen.of([shown]))
    other = focus_paper.plan(conn, weak, WEEK, draw=5)
    with pytest.raises(seen.Changed):  # a draw shown is printed as that draw, never as a fresh one
        focus_paper.make(conn, weak, WEEK, BY, draw=6, seen=seen.of([other]))
    batch = maker.plan(conn, SECTION, picked, WEEK, "practice", "each", EASY, draw=5)
    with pytest.raises(seen.Changed):
        maker.make(
            conn, SECTION, picked, WEEK, "practice", "each", BY, EASY, draw=6, seen=seen.of(batch["papers"])
        )
    assert _counts(conn) == before, "nothing printed"
