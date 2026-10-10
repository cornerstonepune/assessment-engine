"""Every case a level lists is one its own numbers can be and its kind can draw (goals/as1-every-listed-case-draws.yaml).

Found while proving M2b: drawn alone on its level, 35 (case, level) pairs gave nothing, and a level quietly handed their
share to its other cases. Every check here reads the question as measured, never the generator."""

import json
import pathlib
import random

import pytest

from engine.assess import draw, tags, taxonomy
from engine.assess import operations as O
from engine.w1_bank import cases

ROOT = pathlib.Path(__file__).resolve().parents[3]
SETS = {s["code"]: s for s in json.loads((ROOT / "supabase/seed/skill_sets.json").read_text())["skill_sets"]}
CASES = {
    c["code"]: c
    for c in json.loads((ROOT / "supabase/seed/taxonomy_cases.json").read_text())["taxonomy_cases"]
}


def _drawn(code, level, case, n=4, seed=5):
    """[question] of one case drawn alone on its level, as the bank draws it: in every written method the level prints
    it in (ADR 0055), from the level's own matches (`cases.on_level`)."""
    check = {**SETS[code]["difficulty"][level]["check"], "cases": [case]}
    matches = cases.on_level(check, {c: row["match"] for c, row in CASES.items()})
    got = draw.level(random.Random(seed), check, matches, SETS[code]["rung_code"], n)
    return [it for _, it in got], matches[case]


def _sizes(it):
    return len(str(it.spec["a"])), len(str(it.spec["b"]))


@pytest.mark.parametrize("code", sorted(SETS))
def test_every_case_a_level_lists_draws_on_that_level(code):
    """Drawn alone, every case every level of this skill lists gives questions that are that case, as measured. A level
    that listed a case its numbers could never be drew nothing of it and quietly gave its share to the others."""
    for level, d in SETS[code]["difficulty"].items():
        for case in (d.get("check") or {}).get("cases") or []:
            drawn, match = _drawn(code, level, case)
            assert drawn, (code, level, case)
            for it in drawn:
                assert taxonomy.matches(match, it.fmt, tags.derive(it)), (code, level, case, it.spec)


@pytest.mark.parametrize("code,case", [("ADD.2D2D", "R01"), ("SUB.2D2D", "R02")])
def test_an_estimate_on_a_level_of_cases_lets_its_case_decide_the_regrouping(code, case):
    """A level made of cases names no regrouping, and the estimate read one: every draw failed on the missing rule.
    Its numbers are now any the level's sizes allow, and the case's own match keeps what it asks for."""
    drawn, _ = _drawn(code, "Advance", case, n=12)
    assert len(drawn) == 12
    op = "+" if code.startswith("ADD") else "-"
    assert all(
        it.fmt == "estimate_then_calc" and it.spec["op"] == op and _sizes(it) == (2, 2) for it in drawn
    )
    assert (
        len({it.spec["a"] % 10 + it.spec["b"] % 10 >= 10 for it in drawn}) == 2
    )  # with and without a regroup


@pytest.mark.parametrize(
    "code,case",
    [
        ("ADD.2D1D", "X03"),
        ("ADD.3D1D", "X06"),
        ("ADD.3D2D", "X03"),
        ("SUB.2D1D", "X07"),
        ("SUB.3D1D", "X07"),
        ("SUB.3D1D", "X08"),
        ("SUB.3D2D", "X07"),
        ("SUB.3D2D", "X08"),
        ("SUB.3D2D", "X09"),
    ],
)
def test_a_mistake_is_found_in_numbers_of_the_levels_two_sizes(code, case):
    """The worked answer is of the level's own two sizes, 2 digits and 1 on ADD.2D1D: both numbers were drawn the
    first number's length, so every one was refused. Its planted mistake is the case's, and its wrong answer the one
    that mistake makes of these numbers."""
    within = SETS[code]["difficulty"]["Advance"]["check"]["within"]
    want = (
        within.get("operand_1_digits") or within["digits_max"],
        within.get("operand_2_digits") or within["digits_min"],
    )
    drawn, _ = _drawn(code, "Advance", case, n=8)
    assert len(drawn) == 8
    planted = CASES[case]["match"]["planted"]
    for it in drawn:
        assert sorted(_sizes(it), reverse=True) == sorted(want, reverse=True), (code, case, it.spec)
        assert it.spec["planted"] in (planted if isinstance(planted, list) else [planted])
        assert it.spec["wrong"] != O.compute(it.spec["op"], it.spec["a"], it.spec["b"])


def _box_sizes(within, where):
    """The digits a number at these places can have on a level: its own place's; else the longest or the shortest,
    or, where only the longest is named (ADD.4D), anything up to it."""
    place = {"FIRST_OPERAND": "operand_1_digits", "SECOND_OPERAND": "operand_2_digits"}
    if "digits_max" in within:
        top = within["digits_max"]
        return {top, within["digits_min"]} if "digits_min" in within else set(range(1, top + 1))
    return {within[place[w]] for w in where if place.get(w) in within}


def test_a_missing_number_is_listed_only_where_its_box_fits():
    """A missing number's box is a number of the level's: a 1-digit box on ADD.2D2D, whose numbers are 2 digits, is no
    question it can hold. M01 to M05, M24 and M25 left the 20 levels they could never be, and stay on those they fit."""
    held = 0
    for code, s in SETS.items():
        for level, d in s["difficulty"].items():
            check = d.get("check") or {}
            for case in check.get("cases") or []:
                match = CASES[case]["match"]
                for alt in match if isinstance(match, list) else [match]:
                    if alt.get("fmt") != "missing_number" or "unknown_digits" not in alt:
                        continue
                    where = alt["unknown_position"]
                    sizes = _box_sizes(
                        check.get("within") or {}, where if isinstance(where, list) else [where]
                    )
                    assert not sizes or alt["unknown_digits"] in sizes, (code, level, case, sizes)
                    held += bool(sizes)
    assert held  # the rule read real levels


def test_subtracting_from_1000_is_the_4_digit_skills():
    """1000 − 476 and 1000 − 999 start at 1000: SUB.4D's numbers, never SUB.3D3D's, whose are 3 digits by 3."""
    for level in ("Hard", "Advance"):
        assert {"SZ6", "SZ9"} <= set(SETS["SUB.4D"]["difficulty"][level]["check"]["cases"]), level
        assert not {"SZ6", "SZ9"} & set(SETS["SUB.3D3D"]["difficulty"][level]["check"]["cases"]), level
    for case in ("SZ6", "SZ9"):
        drawn, _ = _drawn("SUB.4D", "Hard", case, n=6)
        assert len(drawn) == 6 and all(len(str(it.spec["a"])) == 4 for it in drawn), case


def test_a_story_is_drawn_by_a_kind_whose_templates_hold_its_shape():
    """W25 (a number to leave out) lists the one-step kind, which reads such a story, and the two-step kind; only the
    two-step's templates hold that shape. Half its draws asked the one-step kind and failed unseen, and once that
    failure was raised a fresh bank stopped at WORD.1_2STEP. Every draw is now made, by the kind that can."""
    drawn, _ = _drawn("WORD.1_2STEP", "Advance", "W25", n=12)
    assert len(drawn) == 12 and {it.fmt for it in drawn} == {"word_2step"}


def test_a_rule_a_kind_cannot_read_fails_aloud():
    """Only numbers that did not fit are an unlucky draw (a `RuntimeError`, which the drawer tries again). A rule the
    kind cannot read is a defect, and it is raised: the estimate's missing `regroups` was swallowed 6,000 times a level."""
    check = {"cases": ["R01"]}
    unreadable = {
        "R01": {
            "taxonomy": "ADD_SUB",
            "fmt": "estimate_then_calc",
            "operand_1_digits": 2,
            "operand_2_digits": 2,
        }
    }
    with pytest.raises(KeyError):  # an estimate whose case names no operation: its kind reads `op`
        draw.level(random.Random(1), check, unreadable, "R22", 1)
