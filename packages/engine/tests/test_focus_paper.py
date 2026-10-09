"""A child's next paper chosen from the child's own graph, against the real schema, rolled back.

The child's checked answers go in as confirmed evidence; the graph is rebuilt from them exactly as a
sign-off rebuilds it; the plan and the paper are read back from there.
"""

import json
import os
from pathlib import Path

import pytest

from engine.assess import graph, verify
from engine.assess import tags as T
from engine.assess.items import Item
from engine.core import db
from engine.w1_bank import labels
from engine.w2_print import focus_paper, shelf

WEEK = "T3W1-focus-test"


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
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


def test_the_home_paper_is_one_skill_the_weakest_random_bank_questions_at_its_level_never_seen_before(
    conn, child
):
    seen = conn.execute(
        "select id from item where status = 'active' and skill_set_code = 'SUB.3D3D' and difficulty = 'Medium'"
        " order by item_key limit 40"
    ).fetchall()
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week)"
        " select tenant_id, %s, id, 'earlier' from item where id = any(%s)",
        (child, [r["id"] for r in seen]),
    )
    p = focus_paper.plan(conn, child, WEEK)
    # one skill, never a mix: the weakest, worked on as subtraction; the practising addition waits its turn.
    # Right 2 of 8 would be Easy, but Easy has no exchange and cannot show the child's mistake: Medium can
    assert [(a["skill_set"], a["level"]) for a in p["areas"]] == [("SUB.3D3D", "Medium")]
    assert p["n"] == 12 and [len(a["questions"]) for a in p["areas"]] == [12]
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
    # the paper sits where the mistake can happen, and the questions that can show it come first
    shows = [q["shows_mistake"] for q in area["questions"]]
    assert shows[0], "a paper for a repeated mistake must be able to show it"
    assert shows == sorted(shows, reverse=True), area["questions"]


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


def _text(pdf) -> str:
    import pymupdf

    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return "".join(page.get_text() for page in doc)


def test_a_paper_is_seen_exactly_as_it_will_print_before_anyone_approves_it_and_seeing_it_writes_nothing(
    conn, child
):
    before = {t: db.counts(conn, [t])[t] for t in ("sheet_template", "sheet_instance", "item_exposure")}
    seen = focus_paper.preview(conn, child, WEEK, actor="test")
    assert seen.startswith(b"%PDF")
    assert {t: db.counts(conn, [t])[t] for t in before} == before, "seeing a paper prints nothing"
    made = focus_paper.make(conn, child, WEEK, actor="test")
    printed = _text(Path(made["pdf_path"]).read_bytes())
    assert _text(seen).replace(focus_paper.PREVIEW, made["qr"]) == printed, "only the QR differs"
    assert "Home assessment" in printed, "a paper sent home says so on the page (Nimish, 2026-09-24)"


def test_a_paper_a_teacher_asks_for_is_seen_before_it_is_approved_and_one_the_bank_cannot_fill_is_refused(
    conn, child
):
    ask = [{"skill_set": "SUB.3D3D", "level": "Medium", "n": 5}]
    seen = focus_paper.preview(conn, child, WEEK, "teacher@school.test", ask)
    made = focus_paper.make(conn, child, WEEK, "teacher@school.test", ask)
    assert _text(seen).replace(focus_paper.PREVIEW, made["qr"]) == _text(Path(made["pdf_path"]).read_bytes())
    with pytest.raises(ValueError, match="has no level 'Hard'"):
        focus_paper.preview(conn, child, WEEK, "t", [{"skill_set": "SUB.1D1D", "level": "Hard", "n": 5}])


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


def test_a_teacher_asks_for_any_skills_at_any_levels_and_how_many_and_the_engine_makes_it(conn, child):
    ask = [
        {"skill_set": "SUB.3D3D", "level": "Medium", "n": 5},
        {"skill_set": "ADD.2D2D", "level": "Hard", "n": 3},
    ]
    p = focus_paper.plan(conn, child, WEEK, ask)
    assert [(a["skill_set"], a["level"], len(a["questions"])) for a in p["areas"]] == [
        ("SUB.3D3D", "Medium", 5),
        ("ADD.2D2D", "Hard", 3),
    ]
    assert p["areas"][0]["mistake"] == "M_SMALL_FROM_LARGE", "the child's own mistake still leads its skill"
    made = focus_paper.make(conn, child, WEEK, "teacher@school.test", ask)
    again = focus_paper.make(
        conn, child, WEEK, "teacher@school.test", ask
    )  # a second custom paper is allowed
    rows = conn.execute(
        "select kind, approved_by from sheet_instance where qr_code = any(%s)", ([made["qr"], again["qr"]],)
    ).fetchall()
    assert {(r["kind"], r["approved_by"]) for r in rows} == {("custom", "teacher@school.test")}
    first = {q["id"] for a in made["areas"] for q in a["questions"]}
    assert not first & {q["id"] for a in again["areas"] for q in a["questions"]}, "never a question twice"
    home = focus_paper.make(
        conn, child, WEEK, "teacher@school.test"
    )  # custom papers do not use up the home one
    assert home["qr"] not in (made["qr"], again["qr"])


def test_a_request_the_bank_cannot_fill_is_refused_in_words_never_padded(conn, child):
    with pytest.raises(ValueError, match="has no level 'Hard'"):
        focus_paper.plan(conn, child, WEEK, [{"skill_set": "SUB.1D1D", "level": "Hard", "n": 5}])
    with pytest.raises(ValueError, match="1 to 40 questions"):
        focus_paper.plan(conn, child, WEEK, [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 0}])
    with pytest.raises(ValueError, match="no skill set"):
        focus_paper.plan(conn, child, WEEK, [{"skill_set": "NOPE", "level": "Easy", "n": 5}])
    left = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = 'SUB.3D3D' and difficulty = 'Easy'"
    ).fetchone()["n"]
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week) select tenant_id, %s, id, 'earlier' from item"
        " where status = 'active' and skill_set_code = 'SUB.3D3D' and difficulty = 'Easy' order by item_key limit %s",
        (child, left - 3),
    )
    with pytest.raises(ValueError, match="only 3 questions this child has not seen"):
        focus_paper.plan(conn, child, WEEK, [{"skill_set": "SUB.3D3D", "level": "Easy", "n": 5}])


def test_a_child_who_lags_nowhere_is_stretched_on_their_strongest_skill(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'2','FOCUSTEST','G2') returning id",
        (tenant,),
    ).fetchone()["id"]
    for _ in range(10):
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, observed_at, confirmed_by) values (%s,%s,'NUM.OPS.01','R22',true,'{}','item',now(),'test')",
            (tenant, cid),
        )
    graph.rebuild(conn, str(cid))
    p = focus_paper.plan(conn, str(cid), WEEK)
    assert [(a["skill_set"], a["level"]) for a in p["areas"]] == [("ADD.2D2D", "Advance")]
    assert "ready to move up" in p["areas"][0]["why"] or "a step up" in p["areas"][0]["why"]


def test_a_skill_the_school_does_not_teach_yet_is_never_on_a_paper(conn, child):
    """Nimish, 2026-09-23: "I'm surprised we haven't even started teaching multiplication"."""
    conn.execute("update topic set taught = false where code = 'ADDSUB'")
    assert focus_paper.plan(conn, child, WEEK)["areas"] == []
    with pytest.raises(ValueError, match="no skill set"):
        focus_paper.plan(conn, child, WEEK, [{"skill_set": "MUL.2D1D", "level": "Easy", "n": 3}])


def test_each_level_belongs_to_one_grade_and_a_child_meets_only_their_own_grade_or_below(conn):
    """`skill_set.level_band`: a level named there belongs to that grade, any other to the skill's own."""
    s = conn.execute(
        "select s.code, r.band from skill_set s join rung r on r.code = s.rung_code"
        " where r.band = 'G2' and s.difficulty ? 'Easy' and s.difficulty ? 'Hard' limit 1"
    ).fetchone()
    if not s:
        pytest.skip("needs a Grade 2 skill with Easy and Hard on the copy")
    conn.execute(
        'update skill_set set level_band = \'{"Easy": "G1", "Medium": "G1"}\' where code = %s', (s["code"],)
    )
    g1, g2 = shelf._levels(conn, "G1")[s["code"]], shelf._levels(conn, "G2")[s["code"]]
    assert "Easy" in g1 and "Hard" not in g1 and "Advance" not in g1
    assert {"Easy", "Hard"} <= set(g2), "a Grade 2 child may still be given the levels Grade 1 teaches"
    assert shelf._levels(conn)[s["code"]] == tuple(
        conn.execute("select difficulty from skill_set where code = %s", (s["code"],)).fetchone()[
            "difficulty"
        ]
    )


def test_every_paper_made_for_a_child_prints_as_a_home_assessment_and_says_who_chose_it():
    """Nimish, 2026-09-27: "The home assessment part reads as 'home assessment.'" A paper an educator chooses for a
    child instead of the proposed one is a different home assessment, not a "Practice" sheet."""
    areas = ["Subtracting 2-digit numbers", "Adding 3-digit numbers"]
    for kind in ("focus", "custom"):
        title, label = focus_paper.heading(kind, areas, "Asha")
        assert title == "Home assessment: Subtracting 2-digit numbers · Adding 3-digit numbers"
        assert label.startswith("Asha · Home assessment, ")
    assert focus_paper.heading("focus", areas, "Asha")[1].endswith("chosen from their own checked papers")
    assert focus_paper.heading("custom", areas, "Asha")[1].endswith("chosen by their educator")
    assert focus_paper.heading("focus", areas, None)[1].startswith("Home assessment · Home assessment")


SEED = Path(__file__).resolve().parents[3] / "supabase/seed"
SETS = json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
RUNG_BAND = {r["code"]: r["band"] for r in json.loads((SEED / "rungs.json").read_text())["rungs"]}
CASE_MATCH = {
    c["code"]: c["match"] for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]
}
# What Grade 1's educator taught to the end of September (Nimish, 2026-10-06), as levels of the bank's skills.
GRADE_1 = {
    "ADD.1D1D": {"Easy", "Medium", "Advance"},
    "SUB.1D1D": {"Easy", "Medium", "Advance"},
    "ADD.2D1D": {"Easy"},
    "ADD.2D2D": {"Easy"},
    "SUB.2D1D": {"Easy"},
    "SUB.2D2D": {"Easy"},
    "DATA.TALLY": {"Easy", "Medium", "Advance"},
    "MUL.GROUPS": {"Easy", "Medium", "Advance"},
}


def _levels_holding(a, op, b):
    """{(skill set, level): the grade it is taught in} for every level of the seed whose own rule holds a + b (or
    a − b), written in a line or in columns."""
    held = {}
    for fmt in ("bare_sum", "column_grid"):
        tags = T.derive(Item("", "", "", [], "", fmt, False, "", {"a": a, "b": b, "op": op}, []))
        for s in SETS:
            for d, level in s["difficulty"].items():
                check = level.get("check") or {}
                if check.get("cases") and not verify.dimension_problems(tags, check, fmt, CASE_MATCH):
                    held[(s["code"], d)] = s.get("level_band", {}).get(d) or RUNG_BAND[s["rung_code"]]
    return held


def test_grade_1_is_exactly_what_its_educator_taught_to_september(conn):
    """Nimish, 2026-10-06: "Ensure that this is the entire thing that's mapped to what has been taught in grade 1."
    Her list: 1-digit + and − 1-digit; 2-digit + and − a 1-digit or 2-digit number with no exchange; tally marks;
    multiplication begun as repeated addition. A Grade 1 child's paper draws from these levels and nothing else."""
    taught = {c["code"] for c in shelf.catalog(conn)}
    grade_1 = {
        code: set(levels) for code, levels in shelf._levels(conn, "G1").items() if code in taught and levels
    }
    assert grade_1 == GRADE_1


def test_no_question_at_a_grade_1_level_needs_an_exchange(conn):
    """ "Addition and subtraction 2 digit without borrowing": every question the bank holds at a Grade 1 level of a
    2-digit skill is measured again from its own numbers, and not one needs an exchange."""
    rows = conn.execute(
        "select i.fmt, i.stem, i.spec, s.rung_code from item i join skill_set s on s.code = i.skill_set_code"
        " join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code"
        " where i.status = 'active' and i.skill_set_code like any (array['ADD.2D%', 'SUB.2D%'])"
        " and coalesce(s.level_band ->> i.difficulty, r.band) = 'G1'"
    ).fetchall()
    assert rows, "the bank holds Grade 1's 2-digit questions"
    assert [r["spec"] for r in rows if labels.tags_of(r).get("regroup_columns")] == []


@pytest.mark.parametrize("a,op,b", [(46, "+", 12), (25, "-", 13), (28, "-", 8)])
def test_the_educators_examples_are_grade_1_questions(a, op, b):
    """ "2 digit with 2 digit and with single digit: 46+12 ... 25-13 28-8": each is a question of a level Grade 1 is
    taught."""
    assert "G1" in _levels_holding(a, op, b).values()


def test_45_plus_8_needs_an_exchange_so_grade_1_waits_for_the_educator():
    """ "45+8": 5 + 8 = 13 makes a ten — an exchange, against her own "without borrowing". It is a question of
    2-digit + 1-digit's Medium level (a carry into the tens), which stays Grade 2 until she says Grade 1 is taught
    it; then that level moves to Grade 1 on the skill's page (BUILD-ORDER, inserted 2026-10-06)."""
    held = _levels_holding(45, "+", 8)
    assert held.get(("ADD.2D1D", "Medium")) == "G2"
    assert "G1" not in held.values()
