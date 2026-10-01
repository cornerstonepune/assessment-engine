"""The maker (goal m3-the-maker): a class practice, a class assessment or a home assessment for any children of a
class, made one of three ways, against the real schema, rolled back.

Nimish, 2026-09-30: "all three types of assessments should have the ability to select multiple children with
different skill sets" — "the same skill paper for multiple children", "individual papers for each child", and
"choose the right skill and the grade level, and then choose the children and generate different questions".
"""

import json
import os
from pathlib import Path

import pymupdf
import pytest

from engine.assess import graph
from engine.core import db
from engine.w2_print import focus_paper, maker, shelf

WEEK = "T3W1-maker-test"
SECTION = "MAKERTEST"
BY = "educator@school.test"
EASY = [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 4}]


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def _child(conn, roll, section=SECTION, answers=()):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G3') returning id",
        (tenant, roll, section),
    ).fetchone()["id"]
    for skill, rung, right, mistakes in answers:
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, observed_at, confirmed_by) values (%s,%s,%s,%s,%s,%s,'item',now(),'test')",
            (tenant, cid, skill, rung, right, mistakes),
        )
    if answers:
        graph.rebuild(conn, str(cid))
    return str(cid)


@pytest.fixture
def kids(conn):
    """Three children of one class — one who takes the smaller digit from the larger again and again, one who gets
    2-digit + 2-digit right every time, one with nothing checked yet — and a child of another class."""
    weak = (
        [("NUM.OPS.02", "R31", False, ["M_SMALL_FROM_LARGE"])] * 4
        + [("NUM.OPS.02", "R31", False, [])] * 2
        + [("NUM.OPS.02", "R31", True, [])] * 2
    )
    return {
        "weak": _child(conn, "1", answers=weak),
        "strong": _child(conn, "2", answers=[("NUM.OPS.01", "R22", True, [])] * 10),
        "new": _child(conn, "10"),
        "elsewhere": _child(conn, "1", section="MAKEROTHER"),
    }


def _ids(paper):
    return [q["id"] for a in paper["areas"] for q in a["questions"]]


def _give(conn, child, level, skip=0, limit=None):
    """The child is given some of a level's questions before, as an earlier paper would give them."""
    rows = conn.execute(
        "select id from item where status = 'active' and skill_set_code = 'SUB.3D3D' and difficulty = %s"
        " order by item_key offset %s limit %s",
        (level, skip, limit),
    ).fetchall()
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week)"
        " select tenant_id, %s, id, 'earlier' from item where id = any(%s) on conflict do nothing",
        (child, [r["id"] for r in rows]),
    )
    return {str(r["id"]) for r in rows}


def _unseen(conn, children, level):
    return conn.execute(
        "select count(*) as n from item i where status = 'active' and skill_set_code = 'SUB.3D3D' and difficulty = %s"
        " and not exists (select 1 from item_exposure x where x.item_id = i.id and x.child_id = any(%s::uuid[]))",
        (level, children),
    ).fetchone()["n"]


def _text(pdf: bytes) -> str:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return "".join(page.get_text() for page in doc)


def test_every_kind_is_made_for_the_children_picked_and_no_one_else(conn, kids):
    picked = [kids["strong"], kids["weak"]]
    for kind, words in (
        ("practice", "Class practice"),
        ("assessment", "Class assessment"),
        ("focus", "Home assessment"),
    ):
        made = maker.make(conn, SECTION, picked, WEEK, kind, "each", BY, EASY)
        rows = conn.execute(
            "select si.qr_code, si.child_id, si.kind, si.section, si.week, si.print_status, si.approved_by,"
            " si.pdf_path, si.key from sheet_instance si where si.qr_code = any(%s)",
            (made["qrs"],),
        ).fetchall()
        assert {str(r["child_id"]) for r in rows} == set(picked)
        assert {(r["kind"], r["section"], r["week"], r["print_status"], r["approved_by"]) for r in rows} == {
            (kind, SECTION, WEEK, "printed", BY)
        }, "each copy is its kind, its class and week, approved in the educator's name"
        for r in rows:
            assert f"{words}:" in _text(Path(r["pdf_path"]).read_bytes()), "the page says what the paper is"
        # the batch prints as one, in roll order
        whose = {r["qr_code"]: str(r["child_id"]) for r in rows}
        assert [whose[q] for q in made["qrs"]] == [kids["weak"], kids["strong"]], "roll 1, then roll 2"
        with pymupdf.open(stream=maker.pdf(conn, made["qrs"]), filetype="pdf") as doc:
            assert doc.page_count == sum(r["key"]["pages"] for r in rows) == made["pages"]

    others = conn.execute(
        "select count(*) as n from sheet_instance where child_id = any(%s::uuid[]) and week = %s",
        ([kids["new"], kids["elsewhere"]], WEEK),
    ).fetchone()["n"]
    assert others == 0, "a child not picked is given nothing"
    with pytest.raises(ValueError, match=f"not in {SECTION}"):
        maker.plan(conn, SECTION, [kids["weak"], kids["elsewhere"]], WEEK, "practice", "each", EASY)
    with pytest.raises(ValueError, match="class practice, a class assessment or a home assessment"):
        maker.plan(conn, SECTION, picked, WEEK, "homework", "each", EASY)
    with pytest.raises(ValueError, match="pick"):
        maker.plan(conn, SECTION, [], WEEK, "practice", "each", EASY)


def test_one_paper_for_all_puts_the_same_questions_on_every_copy_none_seen_by_any(conn, kids):
    picked = [kids["weak"], kids["strong"], kids["new"]]
    seen = _give(conn, kids["weak"], "Easy", 0, 10) | _give(conn, kids["strong"], "Easy", 10, 10)
    ask = [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 6}]
    before = db.counts(conn, ["sheet_template", "sheet_instance", "item_exposure"])
    p = maker.plan(conn, SECTION, picked, WEEK, "assessment", "same", ask)
    assert db.counts(conn, list(before)) == before, "seeing the papers makes none"
    assert not p["refused"] and [x["child_id"] for x in p["papers"]] == picked
    first = _ids(p["papers"][0])
    assert len(first) == 6 and all(_ids(x) == first for x in p["papers"]), (
        "the same questions, in the same order"
    )
    assert not set(first) & seen, "a question one of them had been given came back"

    made = maker.make(conn, SECTION, picked, WEEK, "assessment", "same", BY, ask)
    assert len(set(made["qrs"])) == 3, "every copy has its own code"
    printed = conn.execute(
        "select t.item_ids from sheet_instance si join sheet_template t on t.id = si.sheet_template_id"
        " where si.qr_code = any(%s)",
        (made["qrs"],),
    ).fetchall()
    assert {tuple(map(str, r["item_ids"])) for r in printed} == {tuple(first)}, "what prints is what was seen"

    left = _unseen(conn, picked, "Easy")
    _give(conn, kids["new"], "Easy", 0, None)  # the third child has now been given every Easy question
    assert _unseen(conn, picked, "Easy") == 0 < left
    with pytest.raises(ValueError, match="only 0 questions none of these 3 children has been given"):
        maker.plan(conn, SECTION, picked, WEEK, "assessment", "same", ask)


def test_each_childs_own_is_their_next_step_and_an_educator_can_change_one_child(conn, kids):
    picked = [kids["weak"], kids["strong"], kids["new"]]
    p = maker.plan(conn, SECTION, picked, WEEK, "focus", "own")
    by = {x["child_id"]: x for x in p["papers"]}
    for c in (kids["weak"], kids["strong"]):
        own = focus_paper.plan(conn, c, WEEK)
        assert _ids(by[c]) == [q["id"] for a in own["areas"] for q in a["questions"]], "their own next paper"
        assert by[c]["chosen"] == "graph"
    assert [(a["skill_set"], a["level"]) for a in by[kids["weak"]]["areas"]] == [("SUB.3D3D", "Medium")]
    assert [a["skill_set"] for a in by[kids["strong"]]["areas"]] == ["ADD.2D2D"], (
        "a step up where they are strong"
    )
    assert [r["child_id"] for r in p["refused"]] == [kids["new"]]
    assert p["refused"][0]["why"] == maker.NO_STEP

    change = {
        kids["strong"]: [{"skill_set": "ADD.2D2D", "level": "Easy", "n": 5}],
        kids["new"]: [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 5}],
    }
    q = maker.plan(conn, SECTION, picked, WEEK, "focus", "own", changed=change)
    by = {x["child_id"]: x for x in q["papers"]}
    assert not q["refused"] and list(by) == picked
    assert [(a["skill_set"], a["level"], len(a["questions"])) for a in by[kids["strong"]]["areas"]] == [
        ("ADD.2D2D", "Easy", 5)
    ]
    assert by[kids["strong"]]["chosen"] == by[kids["new"]]["chosen"] == "educator"
    assert by[kids["weak"]]["chosen"] == "graph", "a change for one child leaves the others their own"
    assert [(a["skill_set"], a["level"]) for a in by[kids["weak"]]["areas"]] == [("SUB.3D3D", "Medium")]

    made = maker.make(conn, SECTION, picked, WEEK, "focus", "own", BY, changed=change)
    labels = [_text(maker.pdf(conn, [qr])) for qr in made["qrs"]]
    assert "chosen from their own checked papers" in labels[0] and "chosen by their educator" in labels[1]
    again = maker.plan(conn, SECTION, [kids["weak"]], WEEK, "focus", "own")
    assert again["papers"] == [] and made["qrs"][0] in again["refused"][0]["why"], (
        "one home assessment a week"
    )
    with pytest.raises(ValueError, match="each child's own"):
        maker.plan(conn, SECTION, picked, WEEK, "practice", "each", EASY, changed=change)


def test_the_same_skill_and_level_gives_each_child_different_questions_none_shared(conn, kids):
    picked = [kids["weak"], kids["strong"], kids["new"]]
    seen = _give(conn, kids["weak"], "Medium", 0, 30)
    ask = [{"skill_set": "SUB.3D3D", "level": "Medium", "n": 12}]
    p = maker.plan(conn, SECTION, picked, WEEK, "practice", "each", ask)
    assert not p["refused"] and [x["child_id"] for x in p["papers"]] == picked
    drawn = [set(_ids(x)) for x in p["papers"]]
    assert [len(d) for d in drawn] == [12, 12, 12]
    assert not (drawn[0] & drawn[1] or drawn[0] & drawn[2] or drawn[1] & drawn[2]), (
        "no two children share one"
    )
    assert not drawn[0] & seen, "never a question the child was given before"
    rows = conn.execute(
        "select distinct skill_set_code, difficulty from item where id = any(%s::uuid[])",
        (list(set().union(*drawn)),),
    ).fetchall()
    assert [(r["skill_set_code"], r["difficulty"]) for r in rows] == [("SUB.3D3D", "Medium")]
    shows = [q["shows_mistake"] for q in p["papers"][0]["areas"][0]["questions"]]
    assert shows[0] and shows == sorted(shows, reverse=True), "the child's own repeated mistake still leads"
    assert maker.plan(conn, SECTION, picked, WEEK, "practice", "each", ask) == p, "the page shows what prints"

    _give(conn, kids["new"], "Medium", 0, _unseen(conn, [kids["new"]], "Medium") - 3)
    assert _unseen(conn, [kids["new"]], "Medium") == 3
    q = maker.plan(conn, SECTION, [kids["new"]], WEEK, "practice", "each", ask)
    assert [r["roll_no"] for r in q["refused"]] == ["10"], "the child the bank cannot fill is named"
    assert "only 3 questions this child has not seen" in q["refused"][0]["why"]
    before = db.counts(conn, ["sheet_instance"])
    with pytest.raises(ValueError, match="roll 10: only"):
        maker.make(conn, SECTION, picked, WEEK, "practice", "each", BY, ask)
    assert db.counts(conn, ["sheet_instance"]) == before, (
        "one child refused, none printed, never a short paper"
    )


def test_two_lines_alike_on_one_paper_never_repeat_a_question(conn, kids):
    """Two areas alike on one paper could draw the same question twice: what was `taken` held the other children's
    papers, never the paper's own (code review, 2026-09-30; goals/p0-the-maker-makes-what-it-shows.yaml). The child
    has been given all but six of the area's questions, so two lines share those six, or the second is refused."""
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week) select i.tenant_id, %s, i.id, 'seen'"
        " from item i where i.status = 'active' and i.skill_set_code = 'SUB.3D3D' and i.difficulty = 'Easy'"
        " order by i.item_key offset 6",
        (kids["new"],),
    )
    line = {"skill_set": "SUB.3D3D", "level": "Easy"}
    halves, more = [{**line, "n": 3}, {**line, "n": 3}], [{**line, "n": 6}, {**line, "n": 1}]
    for way in ("each", "same"):
        (paper,) = maker.plan(conn, SECTION, [kids["new"]], WEEK, "practice", way, halves)["papers"]
        assert len(_ids(paper)) == len(set(_ids(paper))) == 6, way
    p = maker.plan(conn, SECTION, [kids["new"]], WEEK, "practice", "each", more)
    assert p["papers"] == [] and "no line above on this paper holds" in p["refused"][0]["why"]
    with pytest.raises(ValueError, match="no line above on this paper holds"):
        maker.plan(conn, SECTION, [kids["new"]], WEEK, "practice", "same", more)


def test_a_class_is_planned_on_one_read_of_the_catalogue_not_one_a_child(conn, kids, monkeypatch):
    """Planning read the bank's catalogue, levels, rule and names again for every child, inside a page that must
    answer in 8 s (code review, 2026-09-30)."""
    reads, real = [], shelf._catalog
    monkeypatch.setattr(shelf, "_catalog", lambda c: reads.append(1) or real(c))
    maker.plan(conn, SECTION, [kids["weak"], kids["strong"]], WEEK, "focus", "own")
    assert len(reads) == 1


def test_a_changed_childs_paper_is_as_long_as_the_home_paper_row_says(conn, kids):
    """The website asked for 12 questions for a changed child, a number of its own; a home paper's length is the
    `assemble.items_per_sheet` row, and a change without a length takes it (code review, 2026-09-30)."""
    conn.execute("update config set value = '10'::jsonb where key = 'assemble.items_per_sheet'")
    change = {kids["new"]: [{"skill_set": "SUB.3D3D", "level": "Easy"}]}
    p = maker.plan(conn, SECTION, [kids["new"]], WEEK, "focus", "own", changed=change)
    assert [x["n"] for x in p["papers"]] == [10]


def test_a_made_paper_keeps_how_it_was_chosen_and_what_it_works_on_for_its_own_page(conn, kids):
    """Every maker paper was stored as a home paper's, so its page said "chosen from this child's own checked
    papers" of a class practice an educator chose (code review, 2026-09-30)."""
    made = maker.make(conn, SECTION, [kids["weak"]], WEEK, "practice", "each", BY, EASY)
    key = conn.execute("select key from sheet_instance where qr_code = %s", (made["qrs"][0],)).fetchone()[
        "key"
    ]
    key = key if isinstance(key, dict) else json.loads(key)
    name = conn.execute("select name from skill_set where code = 'SUB.3D3D'").fetchone()["name"]
    assert key["how"] == "chosen by their educator"
    assert key["areas"] == [{"name": name, "level": "Easy"}]
