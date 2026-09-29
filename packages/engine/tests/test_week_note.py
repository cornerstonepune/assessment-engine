"""N4 — the week's declaration (goals/n4-week-declaration.yaml, `w2_print/week_note.py`). Jev is stood in for; the
database is the local copy, rolled back."""

import os
import uuid

import pytest

from engine.adapters import jev
from engine.core import db
from engine.w2_print import week_note

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _saying(yes):
    """Jev, stood in: the probability of yes it gives each skill set it is asked about (0.05 for any not named)."""
    asked = []

    def ask(conn, purpose, state, asks):
        asked.append((purpose, state, set(asks)))
        return {"yes": {code: yes.get(code, 0.05) for code in asks}}

    return ask, asked


def test_a_note_in_the_educators_words_proposes_the_grades_skill_sets_it_covered(conn):
    """Nimish: "deep dive into Jev and … figure out all the use cases that we can integrate". The note is Jev's to
    read; which skill sets are the grade's is code's: a Grade 2 class is asked only about Grade 2's skill sets and the
    reasoning ones for Grade 2 and up; what Jev is at least `week.skill_yes_above` sure of comes ticked."""
    ask, asked = _saying({"SUB.2D2D": 0.97, "WORD.1_2STEP": 0.62, "SUB.2D1D": 0.37})
    got = week_note.propose(
        conn, "G2", "Borrowing in subtraction, 2-digit minus 2-digit, and a few story sums.", ask
    )
    purpose, state, codes = asked[0]
    assert purpose == "week_skills" and state == {"educator_note": got and state["educator_note"]}
    assert "SUB.2D2D" in codes and "REASON.FIND_MISTAKE" in codes, (
        "the grade's own and the G2+ reasoning sets"
    )
    assert not any(c.startswith(("ADD.3D", "SUB.3D", "MUL")) for c in codes), "never another grade's"
    rows = got["skill_sets"]
    assert [r["code"] for r in rows][:3] == ["SUB.2D2D", "WORD.1_2STEP", "SUB.2D1D"], "most likely first"
    assert {r["code"] for r in rows if r["ticked"]} == {"SUB.2D2D", "WORD.1_2STEP"}
    assert got["why"] == ""


def test_with_jev_unreachable_nothing_is_ticked_and_the_educator_ticks_themselves(conn):
    def down(*a):
        raise jev.JevError("no TYPESAFE_API_KEY in the engine's environment")

    got = week_note.propose(conn, "G2", "Column addition this week.", down)
    assert got["skill_sets"] and not any(r["ticked"] for r in got["skill_sets"])
    assert all(r["yes"] is None for r in got["skill_sets"]) and "TYPESAFE_API_KEY" in got["why"]


def test_what_the_educator_confirms_is_kept_and_the_latest_for_a_week_stands(conn):
    """Nimish: "Let's not start building a new engine right now." — the declaration feeds the papers the engine
    already makes: it is the week's skill sets, confirmed by a person, nothing more."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    section = f"T{uuid.uuid4().hex[:5]}"
    conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1',%s,'G2')", (tenant, section)
    )
    week_note.confirm(conn, section, "2026-W40", "subtraction", ["SUB.2D2D"], "neha", [{"code": "SUB.2D2D"}])
    week_note.confirm(
        conn, section, "2026-W40", "subtraction and story sums", ["SUB.2D2D", "WORD.1_2STEP"], "neha"
    )
    now = week_note.current(conn, section, "2026-W40")
    assert (now["skill_sets"], now["note"]) == (["SUB.2D2D", "WORD.1_2STEP"], "subtraction and story sums")
    with pytest.raises(ValueError, match="not skill sets of G2"):
        week_note.confirm(conn, section, "2026-W40", "", ["ADD.3D3D"], "neha")
    with pytest.raises(ValueError, match="no class"):
        week_note.confirm(conn, "NOSUCH", "2026-W40", "", ["SUB.2D2D"], "neha")


def test_the_eval_counts_precision_recall_and_exact_sets_against_the_gold(conn):
    gold = [
        {"band": "G2", "note": "a", "skill_sets": ["SUB.2D2D"]},
        {"band": "G2", "note": "b", "skill_sets": ["ADD.2D2D", "WORD.1_2STEP"]},
    ]
    ask, _ = _saying({"SUB.2D2D": 0.9, "ADD.2D2D": 0.8})
    got = week_note.evaluate(conn, ask, gold)
    assert (got["n"], got["exact"], got["precision"], got["recall"]) == (2, 0, 0.5, 0.667)
    assert got["misses"][0]["want"] == ["SUB.2D2D"] and got["misses"][0]["got"] == ["ADD.2D2D", "SUB.2D2D"]


def test_an_eval_jev_cannot_answer_says_so_and_does_not_score_zero(conn):
    """Before, a note Jev could not be asked about was scored as nothing ticked: the eval said 0/24 and passed."""

    def down(*a):
        raise jev.JevError("no TYPESAFE_API_KEY in the engine's environment: Jev cannot be asked")

    got = week_note.evaluate(conn, down, [{"band": "G2", "note": "a", "skill_sets": ["SUB.2D2D"]}])
    assert (got["n"], got["unanswered"]) == (1, 1) and "TYPESAFE_API_KEY" in got["error"]
