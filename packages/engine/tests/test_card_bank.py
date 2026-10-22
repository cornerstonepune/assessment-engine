"""A kind of question in the bank (goals/sf1-a-kind-of-question-is-a-row.yaml, ADR 0075): Achal's three Grade 2 skills
as rows, each level filled to its target or to every different question it can make, every stored question checked
against its kind as it now stands, and each printed, read and marked as any other question."""

import json
import os
import random
import re

import pytest

from engine.assess import cards, render
from engine.assess.pick import Sheet
from engine.core import db
from engine.w1_bank import bank, cases, inventory, kinds, refill
from engine.w3_read import marking

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

ACHAL = ("MUL.THREE", "NUM.SEQUENCE", "MUL.NTH")
TOPIC = {"MUL.THREE": "MUL", "MUL.NTH": "FACTORS", "NUM.SEQUENCE": "NUMSENSE"}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_achals_skills_are_grade_2_rows_with_their_kinds(conn):
    """The three skills are rows: every level Grade 2's, every kind a level names a `question_format` row of that
    skill, each skill in its topic. The engine's code names none of their kinds — a kind is a row, not code."""
    rows = {
        r["code"]: r
        for r in conn.execute(
            "select code, difficulty, level_band from skill where code = any(%s)", (list(ACHAL),)
        ).fetchall()
    }
    assert sorted(rows) == sorted(ACHAL)
    held = kinds.of(conn)
    for code, r in rows.items():
        assert r["level_band"] == {level: "G2" for level in r["difficulty"]}, code
        for level, band in r["difficulty"].items():
            check = band["check"]
            assert check["format"] == "card", (code, level)
            for k in check["cards"]:
                assert held[k]["skill_set"] == code, (code, level, k)
        topic = conn.execute("select topic_code from skill where code = %s", (code,)).fetchone()
        assert topic["topic_code"] == TOPIC[code], code
    source = (db.REPO_ROOT / "packages/engine/engine/assess/cards.py").read_text()
    assert not re.search(r"MUL3|SEQ\.|MULT\.", source), "the card engine names a kind"


def test_a_level_is_filled_to_its_target_or_all_it_can_make_and_says_which(conn):
    """Asked for 100, three numbers of 2 to 5 with a product up to 30 give all 26 they can make and say so; Medium gives
    100 of its 172. The level's target, as refill reads it, is the smaller of its own and what it can make."""
    counts, items = bank.fill_native(conn, "MUL.THREE", "Easy", 100, dry_run=True)
    assert len(items) == 26 and counts["can_make"] == 26, counts
    assert len({it.item_id for it in items}) == 26
    counts, items = bank.fill_native(conn, "MUL.THREE", "Medium", 100, dry_run=True)
    assert len(items) == 100 and counts["can_make"] == 172, counts
    target = {(r["code"], r["difficulty"]): r for r in inventory.coverage(conn)}
    assert target[("MUL.THREE", "Easy")]["target"] == 26
    assert target[("MUL.THREE", "Easy")]["can_make"] == 26
    assert target[("MUL.THREE", "Medium")]["target"] == 100


def test_a_question_in_the_bank_is_checked_against_its_kind(conn):
    """Stored questions are read against their kind and level as they now stand: one whose answer was changed by hand,
    and one whose level's rule was narrowed past its numbers, are named by the check refill retires by."""
    bank.fill_native(conn, "MUL.THREE", "Easy", 6)
    rows = conn.execute(
        "select id, item_key, spec from item where skill_set_code = 'MUL.THREE' and difficulty = 'Easy'"
        " and status = 'active' order by item_key"
    ).fetchall()
    assert len(rows) >= 6
    assert not [r for r in cases.outside_their_level(conn) if r["skill_set_code"] == "MUL.THREE"]
    conn.execute(
        "update item set responses = jsonb_set(responses, '{0,answer}', '\"1\"') where id = %s",
        (rows[0]["id"],),
    )
    big = max(
        rows, key=lambda r: r["spec"]["numbers"]["a"] * r["spec"]["numbers"]["b"] * r["spec"]["numbers"]["c"]
    )
    top = big["spec"]["numbers"]["a"] * big["spec"]["numbers"]["b"] * big["spec"]["numbers"]["c"]
    conn.execute(
        "update skill set difficulty = jsonb_set(difficulty, '{Easy,check,answer_within}', %s::jsonb)"
        " where code = 'MUL.THREE'",
        (json.dumps([8, top - 1]),),
    )
    named = {
        r["item_key"]: r["why"] for r in cases.outside_their_level(conn) if r["skill_set_code"] == "MUL.THREE"
    }
    assert rows[0]["item_key"] in named and big["item_key"] in named, named
    assert refill.retire_outside(conn)[("MUL.THREE", "Easy")] >= 2, (
        "refill retires what its kind no longer holds"
    )


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def _stored(r):
    return {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}


def test_a_kinds_question_is_printed_read_and_marked(conn, tmp_path):
    """A kind's question prints as its sentence with its boxes where the □ stands, or a list as groups of boxes, two
    more than it holds; marked, its right answer is right, a named wrong answer names its mistake, and an empty answer
    is blank — three signals, never one."""
    held = kinds.of(conn)
    level = kinds.resolve(
        conn,
        conn.execute(
            "select difficulty -> 'Medium' -> 'check' as c from skill where code = 'MUL.NTH'"
        ).fetchone()["c"],
    )
    rng = random.Random(3)
    nth = cards.draw(held["MULT.NTH"], level, rng, "R41", "Conceptual")
    first = cards.draw(held["MULT.FIRST5"], level, rng, "R41", "Conceptual")
    key = render.render_sheet(Sheet("CS00CA4D", "G2", "Medium", 1, "W1", [nth, first]), tmp_path)
    boxes = {g["item"] for g in key["geometry"] if g["kind"] == "digit"}
    assert {nth.item_id, first.item_id} <= boxes
    html = next(tmp_path.rglob("*.html")).read_text()
    assert cards.sentence(nth).split("□")[0].strip() in html
    groups = {
        g["resp"].split("#")[1]
        for g in key["geometry"]
        if g["item"] == first.item_id and g["kind"] == "digit"
    }
    assert len(groups) == 5 + 2
    for it in (nth, first):
        (r,) = it.responses
        assert marking.mark(it.spec, _stored(r), _wrote(r.answer))[0] == "correct"
        code, wrong = next(iter(r.misconceptions.items()))
        assert marking.mark(it.spec, _stored(r), _wrote(str(wrong)))[:2] == ("wrong", [code])
        assert marking.mark(it.spec, _stored(r), {"answer_state": "blank"})[0] == "blank"
