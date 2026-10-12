"""What a mistake counts against when a question carries more than one operation, and a story that halves
(goals/md4d2b2-what-a-slip-charges.yaml, `assess/skills.py`, assumption A11).

A slip counts against the operation it happens in (ADR 0023, A11). Measured 2026-10-12 on the bank: in a question that
carries two operations, a mistake belonging to one of them was charged to the question's first skill instead; and the
story that halves ("Two numbers add up to 90 …") never counted on Division. The rules and the vocabulary are the seed's.
"""

import json
import pathlib

from engine.assess import skills

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed"
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
RULES = {k.split(".", 1)[1]: v for k, v in CONFIG.items() if k.startswith("skills.")}
VOCAB = {
    (m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code"))
    for m in json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
}
ADD, SUB, MUL, DIV = "NUM.OPS.01", "NUM.OPS.02", "NUM.OPS.03", "NUM.OPS.04"


def _charged(fmt, spec, stem, rung, code):
    used = skills.used(fmt, spec, stem, rung, RULES)
    return skills.charges(fmt, spec, stem, used, [code], VOCAB, RULES)[code]


def test_a_story_that_halves_counts_on_division():
    """ "Two numbers add up to 90. One of them is 20 more than the other. What is the smaller number?" is 90 − 20, then
    halved: its template says `divide: 2`, and the halving is a division the child carries out."""
    stem = "Two numbers add up to 90. One of them is 20 more than the other. What is the smaller number?"
    spec = {"a": 90, "b": 20, "structure": "CONSTRAINT", "ops": ["-"]}
    assert skills.operations("word_2step", spec, stem) == ["-", "÷"]
    assert DIV in skills.used("word_2step", spec, stem, ["NUM.PRB.02"], RULES)


def test_a_times_table_slip_checking_a_division_counts_against_multiplication():
    """ "Check 42 ÷ 3 = 11 by multiplying": the child multiplies, and a row of the times table out is a multiplication
    slip. It counted against Division."""
    spec = {"a": 42, "b": 3, "op": "÷", "ops": ["÷", "×"], "check": "×"}
    rung = ["NUM.OPS.04", "NUM.PRB.03"]
    assert _charged("inverse_check", spec, "Check 42 ÷ 3 = 11 by multiplying.", rung, "M_MUL_ROW_OUT") == MUL


def test_a_division_slip_in_a_fact_family_counts_against_division():
    """ "3 × 11 = 33. Use it to finish these facts.": the ÷ facts are divisions, and a slip in one is Division's. It
    counted against the fact family's own skill."""
    spec = {"a": 3, "b": 11, "op": "×", "ops": ["×", "÷"]}
    stem = "3 × 11 = 33. Use it to finish these facts."
    assert _charged("fact_family", spec, stem, ["NUM.OPS.05"], "M_DIV_SUBTRACTED") == DIV


def test_a_mistake_whose_row_names_its_skill_is_charged_there_in_a_two_step_story():
    """The bar model's "leaves the smaller one's part out" names Word problems on its own row; in the story that adds and
    then divides it counted against Division, the story's first skill."""
    stem = "Asha and Ravi have 60 marbles in all. Ravi has 2 times as many as Asha. How many marbles does Asha have?"
    spec = {"a": 60, "b": 2, "structure": "BAR_MODEL_TIMES_AS_MANY", "ops": ["+", "÷"]}
    assert _charged("word_2step", spec, stem, ["NUM.OPS.04"], "M_BAR_PART_MISSED") == "NUM.PRB.02"


def test_what_did_not_change_still_holds():
    """A mistake of the question's one operation is that operation's; choosing the wrong operation in a story is the word
    problem's (the table); a slip of an operation the question does not carry is the question's own skill's."""
    assert (
        _charged("bare_sum", {"a": 42, "b": 6, "op": "×"}, "42 × 6 =", ["NUM.OPS.03"], "M_MUL_ROW_OUT") == MUL
    )
    stem = "Asha and Ravi have 60 marbles in all. Ravi has 2 times as many as Asha. How many marbles does Asha have?"
    spec = {"a": 60, "b": 2, "structure": "BAR_MODEL_TIMES_AS_MANY", "ops": ["+", "÷"]}
    assert _charged("word_2step", spec, stem, ["NUM.OPS.04"], "M_WRONG_OP") == "NUM.PRB.02"
    assert (
        _charged("bare_sum", {"a": 31, "b": 2, "op": "÷"}, "31 ÷ 2 =", ["NUM.OPS.04"], "M_MUL_ROW_OUT") == DIV
    )


def test_choosing_the_wrong_operation_in_an_equation_is_the_equations_and_the_table_says_so():
    """Choosing + for − in "□ − 17 = 25", or × for ÷ in a fact family, is a slip in reading the equation, the kind's own
    skill (Mental maths & missing-number equations). It landed there only because nothing named it; the table names it,
    so the person who approves the table approves this too (A11)."""
    table = RULES["charges_by_kind"]
    assert table["equation"]["M_WRONG_OP"] == table["fact_family"]["M_WRONG_OP"] == "NUM.OPS.05"
    spec = {"a": 3, "b": 11, "op": "×", "ops": ["×", "÷"]}
    stem = "3 × 11 = 33. Use it to finish these facts."
    assert _charged("fact_family", spec, stem, ["NUM.OPS.05"], "M_WRONG_OP") == "NUM.OPS.05"
