"""Division is an operation wherever one is named (goals/md0b-division-is-an-operation.yaml).

Before this, ÷ was nowhere: `compute` raised KeyError on it, the skill reader and the old-paper pattern did not see
it, a mistake row could not name it, and eleven kinds of question handed it made a subtraction — several printing "+".
"""

import json
import os
import random

import pytest

from engine.assess import bands, draw_native, equation, verify
from engine.assess import items as I
from engine.assess import misconceptions as M
from engine.assess import operations as O
from engine.assess import skills as S
from engine.assess import words as W
from engine.core import db, mistake_names
from engine.w3_read import legacy

SEED = db.REPO_ROOT / "supabase" / "seed"


# ---------------------------------------------------------------------------------------------- the arithmetic


def test_division_is_computed_exactly_and_a_remainder_is_its_own_answer():
    """84 ÷ 4 is 21. 85 ÷ 4 is 21 remainder 1: two answers, so asked for one it refuses rather than round down."""
    assert O.compute("÷", 84, 4) == 21
    assert O.divide(85, 4) == (21, 1) and O.divide(84, 4) == (21, 0)
    with pytest.raises(ValueError, match="21 r 1"):
        O.compute("÷", 85, 4)
    with pytest.raises(ValueError, match="by 0"):
        O.divide(5, 0)
    assert O.chain("÷", [100, 5, 2]) == 10 and O.chain("-", [8000, 25, 40]) == 7935
    assert M.compute is O.compute, "one owner of what an operation computes"
    # an exact division's one answer is its quotient's box, keyed by the mistakes M3 names (worked by hand: stopped
    # before the 4, 8 ÷ 4; 4 taken away once; × in place of ÷); one with two answers gives none here, never a crash
    assert M.predict("÷", 84, 4) == {"M_DIV_BRING_DOWN_MISSED": 2, "M_DIV_SUBTRACTED": 80, "M_WRONG_OP": 336}
    assert M.predict("÷", 85, 4) == {}
    assert M.applicable([("÷", 84, 4), ("+", 47, 28)]) == sorted(
        {*M.applicable([("+", 47, 28)]), "M_DIV_BRING_DOWN_MISSED", "M_DIV_SUBTRACTED", "M_WRONG_OP"}
    )


def test_every_way_division_is_written_is_one_operation():
    """A model writes /, a book writes ÷, a child may write :. Each is one operation, as x and * are ×."""
    assert {O.sign(s) for s in ("÷", "/", ":")} == {"÷"}
    assert {O.sign(s) for s in ("×", "x", "X", "*")} == {"×"}
    assert {O.sign(s) for s in ("-", "−", "–")} == {"-"}
    assert O.sign("?") is None
    assert verify.normalise({"op": "/"})["op"] == "÷"
    assert mistake_names._op("/") == "÷" and mistake_names._op("÷") == "÷"
    assert S.operations("bare", {"text": "84 ÷ 4 = □"}) == ["÷"]
    assert S.operations("bare", {"text": "□ ÷ 4 = 21"}) == ["÷"]
    assert legacy.parse_expr("144 ÷ 12 =") == ("÷", 144, 12)
    assert legacy.parse_expr("84 / 4 =") is None, "on an old paper, as printed: a / may be a fraction"
    for (
        printed
    ) in O.PRINTED_SIGNS:  # the old-paper pattern and the equation read the one list of printed signs
        assert (legacy.parse_expr(f"84 {printed} 4 =") or ("",))[0] == O.sign(printed), printed


def test_the_verifier_checks_a_division_and_names_its_shape():
    rule = {"op": "÷", "digits": [2, 1], "regroups": [0]}
    c = {"format": "bare_sum", "op": "÷", "a": 84, "b": 4, "answer": 21}
    assert verify.problems(c, rule) == []
    assert verify.problems({**c, "answer": 20}, rule) == ["answer 20 != 21"]
    assert any("21 r 1" in p for p in verify.problems({**c, "a": 85}, rule)), (
        "a remainder is said, not a crash"
    )
    assert verify._template("÷", 84, 4) == "DIV.2D1D"


# ---------------------------------------------------------------------------------------------- the rows


def test_division_has_a_skill_a_mistake_row_and_a_case():
    """Division is the registry's NUM.OPS.04; a taxonomy case may be about multiplying or dividing."""
    config = {r["key"]: r["value"] for r in json.loads((SEED / "config.json").read_text())["config"]}
    by_operation = config["skills.by_operation"]
    assert by_operation["÷"] == "NUM.OPS.04" and by_operation["×"] == "NUM.OPS.03"
    rules = {"by_kind": {}, "by_symbol": {}, "by_operation": by_operation, "by_method": {}}
    assert S.used("bare", {"text": "84 ÷ 4 = □"}, "", [], rules) == ["NUM.OPS.04"]
    dims = {d["name"]: d for d in json.loads((SEED / "case_dimensions.json").read_text())["case_dimensions"]}
    assert set(dims["operation"]["allowed"]) == {"ADD", "SUB", "MUL", "DIV"}
    assert O.NAMES == {"+": "ADD", "-": "SUB", "×": "MUL", "÷": "DIV"}


def test_a_mistake_row_may_be_about_division():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()
        conn.execute(
            "insert into misconception (tenant_id, code, op, name, description, repair_hint, detectable_by, source,"
            " skill_from) values (%s, 'M_TEST_DIV', '÷', 'a division mistake', 'd', 'r', 'answer_lookup', 'test',"
            " 'operation')",
            (tenant["id"],),
        )
        names = mistake_names.names(conn)
        assert names("M_TEST_DIV", "/") == "a division mistake"
        assert names("M_TEST_DIV", skill="NUM.OPS.04") == "a division mistake", "Division's skill is its op"
        conn.rollback()


def test_an_old_papers_division_is_a_sum_that_counts_on_division():
    """G4-BASE16 prints "144 ÷ 12 =". Read as a sum it is computed and counts on Division, not on its rung's first skill."""
    paper = {"code": "P", "items": [{"n": 8, "expr": "144 ÷ 12 =", "question": "144 ÷ 12 =", "rung": "M1"}]}
    where = (
        [],
        {},
        {"M1": ["NUM.OPS.03"]},
        {"+": "NUM.OPS.01", "-": "NUM.OPS.02", "×": "NUM.OPS.03", "÷": "NUM.OPS.04"},
    )
    row = legacy._template_item(paper, paper["items"][0], where)
    assert (row["spec"]["op"], row["spec"]["a"], row["spec"]["b"], row["spec"]["answer"]) == (
        "÷",
        144,
        12,
        12,
    )
    assert row["skill"] == "NUM.OPS.04" and row["rung"] == "M1"
    real = json.loads((SEED / "papers" / "G4-BASE16.json").read_text())
    eight = next(it for it in real["items"] if it["n"] == 8)
    spec = legacy._template_item(real, eight, where)["spec"]
    assert (spec["op"], spec["a"], spec["b"], spec["answer"]) == ("÷", 144, 12, 12), (
        "the paper itself, not a made-up one"
    )
    times = {"code": "P", "items": [{"n": 9, "expr": "12 × 4 =", "question": "12 × 4 =", "rung": "M1"}]}
    assert legacy._template_item(times, times["items"][0], where)["skill"] == "NUM.OPS.03"
    left = {"code": "P", "items": [{"n": 10, "expr": "85 ÷ 4 =", "question": "85 ÷ 4 =", "rung": "M1"}]}
    with pytest.raises(ValueError, match="21 r 1"):
        legacy._template_item(left, left["items"][0], where)
    keyed = {"code": "P", "items": [{**left["items"][0], "answer": "21 r 1"}]}
    assert legacy._template_item(keyed, keyed["items"][0], where)["spec"]["answer"] == "21 r 1", (
        "its own key first"
    )


def test_an_equation_with_times_and_divide_is_solved_in_the_order_taught():
    """× and ÷ before + and −, left to right; a side that does not come out whole is not right."""
    assert equation.right("12 × {1a} = 48", {"1a": "4"}) == {"1a": True}
    assert equation.right("{2a} ÷ 4 = 21", {"2a": "84"}) == {"2a": True}
    assert equation.right("{2a} ÷ 4 = 21", {"2a": "85"}) == {"2a": False}
    assert equation.right("2 + 3 × {x} = 14", {"x": "4"}) == {"x": True}, "3 × 4 first, then 2"
    assert equation.right("20 - 12 ÷ {x} = 17", {"x": "4"}) == {"x": True}
    assert equation.right("638 = 600 + {5a} + {5b}", {"5a": "19", "5b": "19"}) == {"5a": True, "5b": True}
    with pytest.raises(ValueError, match="not a whole number"):
        equation.check("6 ÷ 4 = {a}")


# ---------------------------------------------------------------------------------------------- the kinds


def test_a_story_whose_answer_multiplies_is_refused_never_added():
    """A story's answer is read as signed numbers; a × in it was added, silently."""
    with pytest.raises(O.CannotMake, match="a×b"):
        W.evaluate("a×b", {"a": 6, "b": 4, "c": 0})
    assert W.evaluate("a-b+c", {"a": 9, "b": 4, "c": 2}) == 7


# Every kind whose rule names an operation, and the rule it needs beyond `op`: each makes + and − only, and since
# M2b four of them × too (goals/md2b-times-advance.yaml, `tests/test_mul_advance.py`), and since M2d1 the number line,
# as equal jumps from 0 (goals/md2d1-multiplication-models.yaml); none makes ÷ yet.
PLUS_OR_MINUS = {
    "number_line_jumps": {"hi": 50},
    "estimate_then_calc": {"digits": [2, 2], "regroups": [0, 1]},
    "find_mistake": {"digits": [2]},
    "missing_digit": {"width": 2},
    "inverse_check": {"digits_max": 2},
    "choose_estimate": {"digits_max": 2},
    "possible_answer": {"digits_max": 2},
    "odd_even": {"digits_max": 2},
    "break_apart": {"digits_max": 2},
    "word_1step": {"digits_max": 2},
}


TIMES_TOO = {"estimate_then_calc", "find_mistake", "missing_digit", "word_1step", "number_line_jumps"}


@pytest.mark.parametrize(
    "fmt, op",
    [(f, o) for f in sorted(PLUS_OR_MINUS) for o in ("×", "÷") if not (o == "×" and f in TIMES_TOO)],
)
def test_a_kind_handed_an_operation_it_cannot_make_refuses_in_a_sentence(fmt, op):
    """Handed × or ÷, a kind that makes + and − said nothing and made a subtraction — several printing "+"."""
    make = bands.NATIVE_GENERATORS[fmt]
    with pytest.raises(O.CannotMake) as said:
        make(random.Random(5), "R1", "Procedural", {"op": op, **PLUS_OR_MINUS[fmt]})
    assert fmt in str(said.value) and op in str(said.value), str(said.value)
    assert isinstance(said.value, ValueError) and not isinstance(said.value, RuntimeError), (
        "a refusal is not a draw to try again (the bank retries a RuntimeError)"
    )


def test_a_refusal_is_heard_wherever_a_kind_is_asked():
    """The case drawer and a level's mistake list caught every ValueError as "these numbers did not fit": a kind
    refusing ÷ became zero questions after thousands of tries, or an empty list of mistakes, and nobody was told."""
    with pytest.raises(O.CannotMake, match="find_mistake"):
        bands.codes({"format": "find_mistake", "op": "÷"})
    with pytest.raises(O.CannotMake, match="find_mistake"):
        draw_native.native(random.Random(1), {"fmt": "find_mistake"}, {"op": "÷", "digits": [2]}, "R1", 0)
    # a rule may list the operations a level mixes; that list is not one operation, and is drawn from, not read as one
    assert O.sign(["+", "-"]) is None and O.sign(5) is None
    assert bands.NATIVE_GENERATORS["word_1step"](
        random.Random(2), "R8", "Application", {"op": ["+", "-"]}
    ).fmt


def test_a_sum_written_with_a_printed_minus_is_a_subtraction_throughout():
    """`bare_sum` sampled by the folded sign and marked by the raw one: "−" made a subtraction with no mistakes."""
    it = I.bare_sum(random.Random(3), "R0", "Procedural", "−", 2, 2, {1})
    assert it.spec["op"] == "-" and it.responses[0].misconceptions, "a subtraction, with its named mistakes"
    assert int(it.responses[0].answer) == it.spec["a"] - it.spec["b"]
    assert M.predict("−", 52, 17) == M.predict("-", 52, 17) != {}
