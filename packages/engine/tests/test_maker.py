"""The maker (goal m3-the-maker): a class practice, a class assessment or a home assessment for any children of a
class, made one of three ways, against the real schema, rolled back.

Nimish, 2026-09-30: "all three types of assessments should have the ability to select multiple children with
different skill sets" — "the same skill paper for multiple children", "individual papers for each child", and
"choose the right skill and the grade level, and then choose the children and generate different questions".
"""

import json
import os
from pathlib import Path

import psycopg
import pymupdf
import pytest

from engine.assess import graph
from engine.core import db
from engine.w2_print import focus_paper, maker, shelf

WEEK = "T3W1-maker-test"
SECTION = "MAKERTEST"
BY = "educator@school.test"
EASY = [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 4}]
# says again on live the rule for which papers a sheet may be (goals/l3-a-class-paper-prints-on-live.yaml)
RULE_SAID_AGAIN = (
    db.REPO_ROOT
    / "supabase"
    / "migrations"
    / "20261108090000_a_paper_made_for_one_child_is_a_sheet_on_live.sql"
)


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def _child(conn, roll, section=SECTION, answers=(), band="G3"):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,%s) returning id",
        (tenant, roll, section, band),
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
    # every question a repeat now: the paper is made all the same, saying so (goals/l6-a-paper-is-always-made.yaml)
    again = maker.plan(conn, SECTION, picked, WEEK, "assessment", "same", ask)
    assert not again["refused"] and again["papers"][0]["areas"][0]["seen_before"] == 6


def test_a_paper_short_of_fresh_questions_is_made_with_those_seen_longest_ago(conn, kids):
    """Nimish, 2026-10-16: "I don't want teachers to have this many complications." A paper is never refused for want of
    fresh questions: those none of its children was given in the window go first, then those they were given longest
    ago, and the paper says how many it repeats. Only more questions than the level holds at all is refused."""
    picked = [kids["weak"], kids["strong"], kids["new"]]
    ids = [
        str(r["id"])
        for r in conn.execute(
            "select id from item where status = 'active' and skill_set_code = 'SUB.3D3D' and difficulty = 'Easy'"
            " order by item_key"
        )
    ]
    assert len(ids) >= 12, "the level must hold a dozen questions for this to mean anything"
    _give(
        conn, kids["weak"], "Easy", 3, None
    )  # every Easy question but the first three, given to one of the three
    conn.execute(
        "update item_exposure set created_at = now() - interval '1 day' where child_id = %s", (kids["weak"],)
    )
    conn.execute(
        "update item_exposure set created_at = now() - interval '10 days' where child_id = %s and item_id = any(%s)",
        (kids["weak"], ids[3:6]),
    )
    ask = [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 6}]
    for way in ("same", "each"):
        p = maker.plan(
            conn, SECTION, picked if way == "same" else [kids["weak"]], WEEK, "assessment", way, ask
        )
        assert not p["refused"], p["refused"]
        (area,) = p["papers"][0]["areas"]
        got = [q["id"] for q in area["questions"]]
        assert set(got) == set(ids[:6]), "the three never given first, then the three given longest ago"
        assert area["seen_before"] == 3, way
    # a home assessment draws the same way
    one = focus_paper.plan(conn, kids["weak"], WEEK, ask)
    assert one["n"] == 6 and one["areas"][0]["seen_before"] == 3
    # more questions than the level holds at all: refused, saying how many it holds
    conn.execute("update item set status = 'retired' where id = any(%s::uuid[])", (ids[10:],))
    with pytest.raises(ValueError, match="holds 10 questions at Easy; ask for 10 or fewer"):
        maker.plan(conn, SECTION, picked, WEEK, "assessment", "same", [{**ask[0], "n": 12}])


def test_a_question_given_before_the_window_is_fresh_again_and_one_given_inside_it_is_a_repeat(conn, kids):
    """SPEC: across weeks, a child is not given a question they saw in the last `exposure.days` days — the threshold row
    the week's assembly reads (ADR 0011 let a level hold fewer than fifty questions on that window). Neha, 2026-10-16:
    Grade 1's 13 children had been given all but 4 of Equal groups at Medium, a level of 20 questions, and one paper for
    all was refused for good, however long ago they had been given them."""
    picked = [kids["weak"], kids["strong"], kids["new"]]
    days = int(conn.execute("select value from threshold where key = 'exposure.days'").fetchone()["value"])
    _give(conn, kids["weak"], "Easy", 0, None)  # every Easy question, to one of the three
    ask = [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 6}]

    def given(ago):
        conn.execute(
            "update item_exposure set created_at = now() - make_interval(days => %s) where child_id = %s",
            (ago, kids["weak"]),
        )

    given(days + 1)  # longer ago than the window: fresh again
    p = maker.plan(conn, SECTION, picked, WEEK, "assessment", "same", ask)
    assert not p["refused"] and p["papers"][0]["areas"][0]["seen_before"] == 0
    one = focus_paper.plan(conn, kids["weak"], WEEK, ask)
    assert one["n"] == 6 and one["areas"][0]["seen_before"] == 0, (
        "a child's own paper holds to the same window"
    )

    given(days - 1)  # inside it: a repeat, taken because no fresh one is left, and counted (goals/l6)
    p = maker.plan(conn, SECTION, picked, WEEK, "assessment", "same", ask)
    assert not p["refused"] and p["papers"][0]["areas"][0]["seen_before"] == 6
    assert focus_paper.plan(conn, kids["weak"], WEEK, ask)["areas"][0]["seen_before"] == 6


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
    # Nimish, 2026-10-21: an educator who does not like the paper they printed makes another, the same week
    again = maker.make(conn, SECTION, [kids["weak"]], WEEK, "focus", "own", BY)
    week = focus_paper.approved(conn, kids["weak"], WEEK)
    assert week["qr"] == again["qrs"][0] and week["replaced"] == [made["qrs"][0]], "the newest is the week's"
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
    # three fresh, then the nine seen longest ago: made, and saying so (goals/l6-a-paper-is-always-made.yaml)
    assert not q["refused"] and q["papers"][0]["areas"][0]["seen_before"] == 9
    assert len(set(_ids(q["papers"][0]))) == 12, "never a short paper"


def test_two_lines_alike_on_one_paper_never_repeat_a_question(conn, kids):
    """Two areas alike on one paper could draw the same question twice: what was `taken` held the other children's
    papers, never the paper's own (code review, 2026-09-30; goals/p0-the-maker-makes-what-it-shows.yaml). The child
    has been given all but six of the area's questions, so two lines share those six, and a seventh is one it was
    given before (goals/l6-a-paper-is-always-made.yaml) — never one of the six again."""
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
    for way in ("each", "same"):
        (paper,) = maker.plan(conn, SECTION, [kids["new"]], WEEK, "practice", way, more)["papers"]
        assert len(_ids(paper)) == len(set(_ids(paper))) == 7, way
        assert [a["seen_before"] for a in paper["areas"]] == [0, 1], way


def test_a_class_is_planned_on_one_read_of_the_catalogue_not_one_a_child(conn, kids, monkeypatch):
    """Planning read the bank's catalogue, levels, rule and names again for every child, inside a page that must
    answer in 8 s (code review, 2026-09-30)."""
    reads, real = [], shelf._catalog
    monkeypatch.setattr(
        shelf, "_catalog", lambda c, section, every: reads.append(1) or real(c, section, every)
    )
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


def test_a_class_paper_prints_on_a_database_whose_rule_lost_the_paper_for_one_child(conn):
    """Live, 2026-10-14: Make papers for Grade 1 — a class assessment, one paper for all, equal groups at Easy — was
    refused, because live's rule for which papers a sheet may be had lost the one made for one child (the rule as
    20260926090000 wrote it, before 20260929090000 added it). Here the database is put as live had it, the paper is
    refused as it was there, the migration says the rule again, and every child's copy prints; said a second time, on
    a database that already holds it, it changes nothing."""

    def rule():
        return conn.execute(
            "select pg_get_constraintdef(oid) as d from pg_constraint where conname = 'sheet_template_source_check'"
        ).fetchone()["d"]

    held = rule()
    conn.execute("alter table sheet_template drop constraint sheet_template_source_check")
    conn.execute(
        "alter table sheet_template add constraint sheet_template_source_check"
        " check (source in ('generated', 'legacy', 'library')) not valid"  # refuses what comes, whatever is there
    )
    grade_1 = [_child(conn, str(roll), section="G1MAKER", band="G1") for roll in (1, 2, 3)]
    ask = [{"skill_set": "MUL.GROUPS", "level": "Easy", "n": 6}]
    with (
        pytest.raises(psycopg.errors.CheckViolation, match="sheet_template_source_check"),
        conn.transaction(),
    ):
        maker.make(conn, "G1MAKER", grade_1, WEEK, "assessment", "same", BY, ask)

    conn.execute(RULE_SAID_AGAIN.read_text())
    assert rule() == held, "live holds the rule the migrations hold"
    made = maker.make(conn, "G1MAKER", grade_1, WEEK, "assessment", "same", BY, ask)
    assert made["papers"] == 3 and len(set(made["qrs"])) == 3, (
        "a copy for every child picked, each its own code"
    )
    conn.execute(RULE_SAID_AGAIN.read_text())
    assert rule() == held
    names_its_child = conn.execute(
        "select count(*) as n from pg_constraint where conname = 'sheet_template_focus_is_for_a_child'"
    ).fetchone()["n"]
    assert names_its_child == 1, "a paper made for one child still names its child"


def test_the_engine_keeps_a_class_to_its_grade_and_the_educator_may_go_above_it(conn):
    """F1e (goals/f1e-the-grade-plan.yaml), as L7 leaves it (ADR 0081). Each level has a grade; what the engine chooses
    by itself keeps a class to its own grade's levels and those below. 2-digit + 1-digit is Grade 2's, its Easy Grade
    1's: Grade 1's levels hold Easy alone. A paper the educator builds takes the level she chose, whichever way it is
    made."""
    assert shelf._levels(conn, "G1")["ADD.2D1D"] == ("Easy",), "the engine's own choice keeps to the grade"
    grade_1 = [_child(conn, str(roll), section="G1PLAN", band="G1") for roll in (1, 2)]
    medium = [{"skill_set": "ADD.2D1D", "level": "Medium", "n": 4}]
    for way in ("same", "each"):
        made = maker.plan(conn, "G1PLAN", grade_1, WEEK, "assessment", way, medium)
        assert not made["refused"] and len(made["papers"]) == 2, (way, made["refused"])
        assert all(a["level"] == "Medium" for p in made["papers"] for a in p["areas"])


def test_an_educator_may_choose_a_skill_of_a_higher_grade_or_one_the_class_was_not_taught(conn):
    """L7 (goals/l7-a-line-is-topic-skill-level-number.yaml). Achal, through Nimish, 2026-10-16: "Didn't we add two-digit
    by two-digit multiplication yesterday? … even multiples and factors are not visible." A Grade 3 class, with neither
    switched on as taught: 2-digit × 2-digit is Grade 4 at every level, multiples Grade 4 at Hard. One paper for all
    takes both, from two topics; so does a paper for one child. The class's own list of what it was taught, which the
    engine's own choices read, is unchanged."""
    kids = [_child(conn, str(roll), section="L7-G3", band="G3") for roll in (1, 2)]
    conn.execute("update skill_set set taught = false where code in ('MUL.2D2D', 'MD.MULTIPLES')")
    ask = [
        {"skill_set": "MUL.2D2D", "level": "Medium", "n": 3},
        {"skill_set": "MD.MULTIPLES", "level": "Hard", "n": 3},
    ]
    for way in ("same", "each"):
        made = maker.plan(conn, "L7-G3", kids, WEEK, "assessment", way, ask)
        assert not made["refused"] and len(made["papers"]) == 2, (way, made["refused"])
        got = {(a["skill_set"], a["level"], len(a["questions"])) for a in made["papers"][0]["areas"]}
        assert got == {("MUL.2D2D", "Medium", 3), ("MD.MULTIPLES", "Hard", 3)}, got
    assert focus_paper.plan(conn, str(kids[0]), WEEK, ask)["n"] == 6, "a paper for one child, the same"
    taught = {c["code"] for c in shelf.catalog(conn, "L7-G3")}
    assert not taught & {"MUL.2D2D", "MD.MULTIPLES"}, "what the class was taught is still its own"
    with pytest.raises(ValueError, match="no skill set"):
        maker.plan(
            conn,
            "L7-G3",
            kids,
            WEEK,
            "assessment",
            "same",
            [{"skill_set": "NO.SUCH", "level": "Easy", "n": 3}],
        )
    with pytest.raises(ValueError, match=r"MD\.MULTIPLES has no level 'Sideways'"):
        maker.plan(
            conn,
            "L7-G3",
            kids,
            WEEK,
            "assessment",
            "same",
            [{"skill_set": "MD.MULTIPLES", "level": "Sideways", "n": 3}],
        )
