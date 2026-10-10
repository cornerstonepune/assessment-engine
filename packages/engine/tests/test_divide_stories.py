"""Stories that divide with something left over (goals/md3b3-divide-mistakes-and-stories.yaml): on DIV.2D1D the full
boxes (B14, the remainder dropped), the rickshaws needed (B15, one more for those left), how many are left over (B16),
or both (B17). Every answer is worked here from the division itself and what the story does with its remainder, every
mistake from the named mistakes' own predictors; never read back from the code under test."""

import dataclasses
import functools
import json
import pathlib
import random
import re

from engine.assess import div_mistakes as DM
from engine.assess import draw, render, tags, taxonomy
from engine.assess import words as W
from engine.assess.pick import Sheet
from engine.checks import scenarios
from engine.w1_bank import cases

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase/seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
ROWS = json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
SKILL = "DIV.2D1D"
USE = {"B14": "ROUND_DOWN", "B15": "ROUND_UP", "B16": "REMAINDER_ASKED", "B17": "BOTH_ASKED"}
NOT_UP = "M_REMAINDER_NOT_ROUNDED_UP"


def _check():
    return SETS[SKILL]["difficulty"]["Advance"]["check"]


def _matches(check):
    return cases.on_level(check, {c: row["match"] for c, row in CASES.items()})


@functools.cache
def _drawn(case, n=24, seed=5):
    """`n` stories of one case on DIV.2D1D's own numbers, as the bank draws them."""
    check = {**_check(), "cases": [case]}
    return [
        it for _, it in draw.level(random.Random(seed), check, _matches(check), SETS[SKILL]["rung_code"], n)
    ]


def _want(use, a, b):
    """What the story asks, worked from the division: (the answer's box, the remainder's box or None)."""
    q, r = divmod(a, b)
    return {
        "ROUND_DOWN": (q, None),
        "ROUND_UP": (q + 1, None),
        "REMAINDER_ASKED": (r, None),
        "BOTH_ASKED": (q, r),
    }[use]


def _boxes(it):
    return {r.rid: r for r in it.responses}


def test_a_story_uses_what_is_left_over_as_it_needs():
    """Each story divides one of the level's own numbers with something left over, and asks what the story needs: the
    full boxes, the rickshaws for everyone, what is left over, or both — its answers worked from the division."""
    within = _check()["within"]
    for case, use in USE.items():
        drawn = _drawn(case)
        assert len(drawn) == 24 and len({it.item_id for it in drawn}) == 24, case
        for it in drawn:
            sp = it.spec
            a, b = sp["a"], sp["b"]
            assert it.fmt == "word_1step" and sp["op"] == "÷" and sp["remainder_use"] == use, sp
            assert (len(str(a)), len(str(b))) == (within["operand_1_digits"], within["operand_2_digits"]), sp
            assert a % b and a // b >= 10, sp
            ans, rem = _want(use, a, b)
            rs = _boxes(it)
            assert rs["ans"].answer == str(ans), (case, sp, rs["ans"].answer)
            assert set(rs) == {"ans"} | ({"rem"} if rem is not None else set()), (case, set(rs))
            if rem is not None:
                assert rs["rem"].answer == str(rem), (case, sp)
            assert taxonomy.matches(_matches(_check())[case], it.fmt, tags.derive(it)), (case, sp)


def test_a_storys_words_are_a_row_that_says_what_it_does_with_the_remainder():
    """The words are a template row, the file the school edits, that says what the story does with what is left over;
    two rows at least for each, so a paper's stories are not all one sentence. What it does is part of the story's
    spec, so 26 laddoos in boxes of 4 asked for the full boxes and for those left over are two questions."""
    for case, use in USE.items():
        rows = [t for t in W.templates("word_1step", "÷", "GROUPING") if t.get("remainder_use") == use]
        assert len(rows) >= 2, (use, rows)
        for it in _drawn(case):
            tpl = W.template_of(it.stem)
            assert tpl is not None and tpl.get("remainder_use") == use and tpl["op"] == "÷", it.stem
    a, b = 26, 4
    down, left = (W.story_spec(t, a=a, b=b) for t in (_row("ROUND_DOWN"), _row("REMAINDER_ASKED")))
    assert (
        down != left and down["remainder_use"] == "ROUND_DOWN" and left["remainder_use"] == "REMAINDER_ASKED"
    )


def _row(use):
    return next(t for t in W.templates("word_1step", "÷", "GROUPING") if t.get("remainder_use") == use)


def test_the_remainder_not_rounded_up_is_a_mistake_of_its_own():
    """26 children, 4 to a rickshaw, answered 6: the remainder not rounded up, a mistake of its own with its own row and
    on DIV.2D1D's list. Every value a box names is a named mistake's: the full boxes and both asked by the division's
    own, how many are left over by the remainder's box's, the rickshaws needed by the remainder not rounded up and by
    each division slip then rounded up as the child would round it."""
    row = [r for r in ROWS if r["code"] == NOT_UP]
    assert len(row) == 1 and row[0]["op"] == "÷" and row[0]["name"] and row[0]["repair_hint"], row
    named = set(SETS[SKILL]["misconception_codes"])
    assert NOT_UP in named
    for case, use in USE.items():
        for it in _drawn(case):
            a, b = it.spec["a"], it.spec["b"]
            q, r = divmod(a, b)
            rs = _boxes(it)
            if use == "ROUND_DOWN":
                want = DM.in_box(a, b, 0)
            elif use == "ROUND_UP":
                slips = {c: g[0] + (1 if g[1] else 0) for c, g in DM.predict(a, b).items()}
                want = {NOT_UP: q} | {c: v for c, v in slips.items() if v != q + 1}
            elif use == "REMAINDER_ASKED":
                want = DM.in_box(a, b, 1)
            else:
                want = DM.in_box(a, b, 0)
                assert rs["rem"].misconceptions == DM.in_box(a, b, 1), it.spec
            assert rs["ans"].misconceptions == want, (case, it.spec, rs["ans"].misconceptions, want)
            for x in it.responses:
                assert set(x.misconceptions or {}) <= named, (case, set(x.misconceptions) - named)
                assert all(str(v) != x.answer for v in (x.misconceptions or {}).values()), (case, x)


def test_a_scenario_recomputes_a_storys_answer_by_what_it_does_with_the_remainder():
    """The scenarios' own check works each story's answer from its numbers and what it does with its remainder, and a
    box one off fails it."""
    for case in USE:
        for it in _drawn(case)[:8]:
            assert scenarios._answer_is_right(it) is True, (case, it.spec)
            for i, r in enumerate(it.responses):
                bad = list(it.responses)
                bad[i] = dataclasses.replace(r, answer=str(int(r.answer) + 1))
                assert scenarios._answer_is_right(dataclasses.replace(it, responses=bad)) is False, (
                    case,
                    r.rid,
                )


def test_a_division_story_and_a_worked_division_print_the_remainders_box():
    """On paper a story that asks both, and a worked division whose right answer leaves a remainder, print the
    quotient's box, its "r" and the remainder's box as one answer; every answer a question asks has its box."""
    both = _drawn("B17")[0]
    check = {**_check(), "cases": ["C05"]}
    found = next(
        it
        for _, it in draw.level(random.Random(2), check, _matches(check), SETS[SKILL]["rung_code"], 12)
        if any(r.rid == "rem" for r in it.responses)
    )
    for it in (both, found):
        html = render.render_item(Sheet("CS000000", "G3", "Advance", 1, "W1", [it]), it, 1)
        assert re.search(r'class="quotient">.*data-r="ans".*>r<.*data-r="rem"', html, re.S), (it.fmt, it.spec)
        assert set(re.findall(r'data-r="([^"]+)"', html)) == {r.rid for r in it.responses}, it.fmt
