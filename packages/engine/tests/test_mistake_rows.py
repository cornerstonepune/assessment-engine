"""A mistake's words are its row alone (goals/md3b3-divide-mistakes-and-stories.yaml, rule 1). The rows the school edits,
`supabase/seed/misconceptions.json`, hold each mistake's name and what the school does about it; the code holds only
how a mistake is made (its predictor). Until M3b3 the code carried a copy of 41 names and repair hints beside its
predictors: two said otherwise than their rows, the hints were read by a test alone, a worked answer's "why" printed the
copy, and a division's mistake had none, so its "why" would have printed a code."""

import json
import os
import pathlib
import random

import pytest

from engine.assess import diagnosis as D
from engine.assess import div_mistakes as DM
from engine.assess import misconceptions as M
from engine.assess import words as W
from engine.assess import written_methods as WM
from engine.core import db
from engine.w1_bank import mistake_guess

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROWS = json.loads((ROOT / "supabase/seed/misconceptions.json").read_text())["misconceptions"]
TABLES = {
    "+": M.TABLES["+"],
    "-": M.TABLES["-"],
    "×": M.TABLES["×"],
    "÷": DM.PREDICTORS,
    "several": M.MULTI_PREDICTORS,
    "compare": M.COMPARE_PREDICTORS,
    "answer": M.ANSWER_RULES,
}
# the operation a table's mistakes are made in, where its rows say one: several numbers added are an addition
OP = {"several": "+", "compare": "any", "answer": "any"}


def _row(code, op):
    """The row that names `code` made in `op`: the operation's own, else the one for any operation."""
    rows = [r for r in ROWS if r["code"] == code]
    return next((r for r in rows if r["op"] == op), None) or next((r for r in rows if r["op"] == "any"), None)


def test_a_mistakes_words_are_its_row_alone():
    """Every mistake the code can name is a predictor and nothing more — no name, no repair hint beside it, no list of
    names of its own — and a worked answer's "why" names no mistake: a person reads it against the mistake's row."""
    for kind, table in TABLES.items():
        for code, made in table.items():
            assert callable(made), (kind, code, made)
    assert not hasattr(WM, "NAMES") and not hasattr(M, "catalogue")
    names = {r["name"] for r in ROWS}
    for op, planted in (
        ("+", "M_NOCARRY"),
        ("-", "M_SMALL_FROM_LARGE"),
        ("×", "M_MUL_CONCAT"),
        ("+", "M_ZERO_DROPPED"),
    ):
        it = D.find_mistake(random.Random(1), "X2", "Conceptual", op=op, planted=planted)
        why = next(r for r in it.responses if r.rid == "why")
        assert "M_" not in (why.rubric or "") and not any(n in (why.rubric or "") for n in names), why.rubric


def test_every_mistake_the_code_can_name_has_its_row():
    """Every mistake a predictor makes, a worked answer plants or a story's words name has its row, for the operation it
    is made in, with a name and what the school does about it — the words every screen and report reads."""
    for kind, table in TABLES.items():
        for code in table:
            row = _row(code, OP.get(kind, kind))
            assert row and row["name"].strip() and row["repair_hint"].strip(), (kind, code)
    named = {r["code"] for r in ROWS if r["name"].strip() and r["repair_hint"].strip()}
    others = (
        set(D.PLANTABLE)
        | {t["wrong_op_as"] for t in W.templates() if t.get("wrong_op_as")}
        | {"M_REMAINDER_NOT_ROUNDED_UP"}
    )
    assert others <= named, others - named


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_jev_is_shown_the_rows_names(conn):
    """Jev's shortlist of what a wrong answer might be is shown each mistake by its row's name for the sum's operation,
    the words a person picks from — not a copy the code keeps. A row the school edits is what Jev is shown next."""
    for op in mistake_guess.SIGN:
        shown = mistake_guess.options(conn, op)
        assert shown.pop(mistake_guess.NONE)
        want = {c for c in M.TABLES[op] if not c.startswith("M_FACT")}
        assert set(shown) == want, (op, set(shown) ^ want)
        for code, name in shown.items():
            assert name == _row(code, op)["name"], (op, code, name)
    conn.execute(
        "update misconception set name = 'Leaves out a zero the answer needs' where code = 'M_ZERO_DROPPED'"
    )
    assert mistake_guess.options(conn, "+")["M_ZERO_DROPPED"] == "Leaves out a zero the answer needs"
