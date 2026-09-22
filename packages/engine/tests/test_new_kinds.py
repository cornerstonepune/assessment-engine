"""The kinds of question the taxonomy needed and the bank did not have (step 8g).

For every one: it is made from a level's rule, it is the taxonomy case it exists for (measured, not
assumed), it prints, a right answer is marked right by the marker papers go through, and every wrong
answer it predicts names a mistake in the vocabulary — the one the marker will return.
"""

import json
import pathlib
import random

import pytest

from engine import legacy
from engine.assess import bands, diagnosis, tags, taxonomy, words
from engine.assess.pick import Sheet
from engine.assess.render import render_item

ROOT = pathlib.Path(__file__).resolve().parents[3]
CASES = {
    c["code"]: c
    for c in json.loads((ROOT / "supabase/seed/taxonomy_cases.json").read_text())["taxonomy_cases"]
}
VOCAB = {
    m["code"] for m in json.loads((ROOT / "supabase/seed/misconceptions.json").read_text())["misconceptions"]
}

KINDS = [
    ("E01", "equation", {"shape": "MISSING_SIGN"}),
    ("E02", "equation", {"shape": "MISSING_SIGNS"}),
    ("E07", "equation", {"shape": "BALANCE_SAME_OP"}),
    ("E08", "equation", {"shape": "BALANCE_TWO_OPS"}),
    ("E09", "equation", {"shape": "SAME_BOTH_SIDES"}),
    ("E10", "equation", {"shape": "TRUE_FALSE"}),
    ("E11", "equation", {"shape": "COMPARE"}),
    ("E03", "fact_family", {"shape": "FROM_ADDITION"}),
    ("E04", "fact_family", {"shape": "FROM_SUBTRACTION"}),
    ("E05", "inverse_check", {"op": "+"}),
    ("E06", "inverse_check", {"op": "-"}),
    ("R04", "choose_estimate", {}),
    ("R05", "possible_answer", {}),
    ("R06", "odd_even", {}),
    ("K08", "break_apart", {}),
    ("R03", "estimate_then_calc", {"op": "+", "digits": [3, 3], "regroups": [1, 2], "round_to": 100}),
    ("R07", "estimate_then_calc", {"op": "+", "digits": [3, 3], "regroups": [1, 2], "shape": "JUDGED"}),
    ("M12", "missing_digit", {"op": "+", "width": 2, "missing_count": 1, "regroups": [1]}),
    ("M15", "missing_digit", {"op": "+", "width": 3, "missing_count": 1, "missing_place": "HUNDREDS"}),
    ("M16", "missing_digit", {"op": "+", "width": 2, "missing_count": 1, "missing_in": "RESULT"}),
    ("M17", "missing_digit", {"op": "+", "width": 2, "missing_count": 2, "missing_in": "FIRST+SECOND"}),
    (
        "M18",
        "missing_digit",
        {"op": "+", "width": 3, "missing_count": 3, "missing_in": "FIRST+SECOND+RESULT"},
    ),
    ("M19", "missing_digit", {"op": "+", "width": 2, "shape": "SAME_LETTER"}),
    ("M20", "missing_digit", {"op": "+", "width": 2, "shape": "INEQUALITY"}),
    ("M36", "missing_digit", {"op": "-", "width": 3, "missing_count": 1, "regroups": [1, 2]}),
    ("M39", "missing_digit", {"op": "-", "width": 2, "shape": "INEQUALITY"}),
    ("W03", "word_1step", {"digits_max": 2, "structure": "JOIN_START"}),
    ("W05", "word_1step", {"digits_max": 2, "structure": "SEPARATE_CHANGE"}),
    ("W10", "word_1step", {"digits_max": 2, "structure": "COMPARE_LARGER"}),
    ("W11", "word_1step", {"digits_max": 2, "structure": "COMPARE_SMALLER"}),
    ("W21", "word_2step", {"digits_max": 2, "structure": "ADD_ADD"}),
    ("W27", "word_2step", {"digits_max": 3, "structure": "ADD_SUB"}),
    ("W28", "word_2step", {"digits_max": 2, "structure": "UNKNOWN_FIRST"}),
    ("W29", "word_2step", {"digits_max": 2, "structure": "CONSTRAINT"}),
    ("W25", "word_2step", {"digits_max": 2, "structure": "EXTRA_INFORMATION"}),
]


def make(fmt, rule, seed=1, tries=300):
    rng = random.Random(seed)
    for _ in range(tries):
        try:
            return bands.native_item(fmt, rule, rng, "R16", "Conceptual")
        except RuntimeError:
            continue
    raise AssertionError(f"{fmt} {rule}: no question in {tries} draws")


def _marks_right(it):
    for r in it.responses:
        if r.kind == "text":
            continue
        status, _, _ = legacy.mark(
            {"kind": "bare"}, vars(r), {"child_answer": str(r.answer), "answer_state": "answered"}
        )
        assert status == "correct", (it.fmt, r.rid, r.answer)


def _names_its_mistakes(it):
    for r in it.responses:
        for code, wrong in (r.misconceptions or {}).items():
            assert code in VOCAB, f"{code} is not a named mistake"
            status, codes, _ = legacy.mark(
                {"kind": "bare"}, vars(r), {"child_answer": str(wrong), "answer_state": "answered"}
            )
            assert status == "wrong" and code in codes, (it.fmt, r.rid, code, wrong, codes)


def _prints(it):
    html = render_item(Sheet("CS000000", "G3", "Medium", 1, "test", [it]), it, 1)
    assert f'data-item="{it.item_id}"' in html
    for r in it.responses:
        assert f'data-r="{r.rid}"' in html, (it.fmt, r.rid)


@pytest.mark.parametrize("case,fmt,rule", KINDS, ids=[k[0] for k in KINDS])
def test_new_kind_is_its_case_prints_and_marks(case, fmt, rule):
    from engine.assess import draw

    drawn = draw.level(random.Random(11), {**rule, "cases": [case]}, {case: CASES[case]["match"]}, "R16", 5)
    assert len(drawn) == 5, f"{case}: the level's rule made {len(drawn)} of 5"
    for _, it in drawn:
        assert it.fmt == fmt and taxonomy.matches(CASES[case]["match"], it.fmt, tags.derive(it)), (
            case,
            it.spec,
            it.stem,
        )
        _prints(it)
        _marks_right(it)
        _names_its_mistakes(it)


@pytest.mark.parametrize("fmt,rule", [(f, r) for _, f, r in KINDS][:12])
def test_a_generator_asked_directly_still_makes_its_kind(fmt, rule):
    assert make(fmt, rule).fmt == fmt


@pytest.mark.parametrize("code", sorted(diagnosis.PLANTABLE))
def test_every_plantable_mistake_is_planted_found_and_named(code):
    it = diagnosis.find_mistake(random.Random(7), "X2", "Conceptual", op="+", digits=2, planted=code)
    assert it.spec["planted"] == code
    ans = next(r for r in it.responses if r.rid == "ans")
    assert int(ans.answer) != int(it.spec["wrong"]), "the worked answer shown is not the right one"
    assert code in VOCAB
    _prints(it)
    _marks_right(it)


def test_every_error_the_taxonomy_lists_can_be_planted():
    listed = {
        c
        for code, case in CASES.items()
        if code.startswith("X")
        for c in (
            case["match"]["planted"]
            if isinstance(case["match"]["planted"], list)
            else [case["match"]["planted"]]
        )
    }
    assert listed - {"M_ZERO_NOT_NINE"} <= diagnosis.PLANTABLE, listed - diagnosis.PLANTABLE


def test_a_missing_digit_question_has_exactly_one_answer():
    from engine.assess import missing_digits as MD

    for seed in range(20):
        it = MD.one(random.Random(seed), "R15", "Conceptual", {"op": "+", "width": 3, "missing_count": 2})
        masks = {"FIRST": it.spec["a"], "SECOND": it.spec["b"], "RESULT": it.spec["c"]}
        assert len(MD._solutions("+", masks)) == 1


def test_every_story_shape_the_taxonomy_lists_has_a_template_and_old_sentences_find_theirs():
    shapes = {
        case["match"]["structure"]
        for code, case in CASES.items()
        if code.startswith("W") and "structure" in case["match"]
    }
    have = {t["structure"] for t in words.templates()}
    assert {s for s in shapes if isinstance(s, str)} <= have
    old = "A bus has 45 seats. 18 of them are taken. How many seats are empty?"
    assert words.structure_of(old) == "PPW_PART"


def test_a_budget_level_gets_the_budget_it_asks_for():
    rng = random.Random(3)
    easy = [words.word_budget(rng, "R14", "Application", 2, (1000, 3000)) for _ in range(10)]
    assert all(len(it.spec["costs"]) == 2 and 1000 <= it.spec["budget"] <= 3000 for it in easy)
    hard = words.word_budget(rng, "R14", "Application", 4, (8000, 15000), one_cost_is_a_product=True)
    assert len(hard.spec["costs"]) == 4 and hard.spec["costs"][3] == hard.spec["children"] * hard.spec["each"]
