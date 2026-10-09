"""Multiplication's three column skills get their Advance (goals/md2b-times-advance.yaml): the drafted document's cases
of the kinds an Advance asks for, each kind making × as it makes + and −. Every check here reads the question, never
the generator: answers in plain arithmetic, boxes solved by trying every digit, a planted mistake worked by hand."""

import functools
import itertools
import json
import os
import pathlib
import random
import re

import pytest

from engine.assess import draw, placing, render, tags, taxonomy
from engine.assess import misconceptions as M
from engine.assess.pick import Sheet
from engine.assess.words import template_of
from engine.core import db

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase/seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
THREE = ["MUL.2D1D", "MUL.3D1D", "MUL.2D2D"]
GRADE = {
    "MUL.2D1D": "G3",
    "MUL.3D1D": "G4",
    "MUL.2D2D": "G4",
}  # the document's Advance grades (assumption A6)
# The document's Advance cases each level holds now: C06 (partitioning, tens taken as ones) comes with the methods
# (M2d). T13 (6 × 125 in a line) left 3 × 1's Advance: its every question is one Easy to Hard hold (STATE.md, M2b).
KINDS = {
    "MUL.2D1D": ["Q07", "Q08", "Q11", "C01", "C02", "V01", "V07", "B06", "B08", "H01", "H07"],
    "MUL.3D1D": ["Q16", "C09"],
    "MUL.2D2D": ["C03", "V02", "V03", "Q15", "B12"],
}
LATER = {"MUL.2D1D": {"C06"}, "MUL.3D1D": set(), "MUL.2D2D": set()}
FMT = {
    **dict.fromkeys(["Q07", "Q08", "Q11", "Q16"], "missing_digit"),
    **dict.fromkeys(["C01", "C02", "C03", "C09"], "find_mistake"),
    **dict.fromkeys(["V01", "V02", "V03", "V07"], "estimate_then_calc"),
    **dict.fromkeys(["B06", "B08", "B12"], "word_1step"),
    **dict.fromkeys(["H01", "H07"], "efficient_method"),
    "Q15": "missing_number",
}


def _check(skill, level="Advance"):
    return SETS[skill]["difficulty"][level]["check"]


def _matches(check):
    return {c: taxonomy.within(CASES[c]["match"], check["within"]) for c in check["cases"]}


@functools.cache
def _drawn(skill, n=60, seed=11):
    """[(case, question)] for a level's kinds only: what this slice makes."""
    check = _check(skill)
    kinds = {**check, "cases": KINDS[skill]}
    return draw.level(random.Random(seed), kinds, _matches(kinds), SETS[skill]["rung_code"], n)


def _of(skill, *codes):
    return [it for c, it in _drawn(skill) if c in codes]


def _resp(it, rid):
    return next(r for r in it.responses if r.rid == rid)


def _half_up(n, to=10):
    return (n + to // 2) // to * to


# ---------------------------------------------------------------------------------------------- the rows


def test_each_advance_is_its_documents_cases_of_the_kinds_it_needs():
    """Advance is Hard's straight cases with the document's own Advance cases, as addition's is (ADD.2D1D: A14 to A16
    with missing numbers, stories and the mistake found), on the skill's own numbers, at the document's grade."""
    for skill in THREE:
        s, hard = SETS[skill], _check(skill, "Hard")
        assert list(s["difficulty"]) == ["Easy", "Medium", "Hard", "Advance"], skill
        assert _check(skill)["cases"] == hard["cases"] + KINDS[skill], skill
        assert _check(skill)["within"] == hard["within"], skill
        assert s["level_band"]["Advance"] == GRADE[skill], skill
        placed = {c for c, x in DOC.items() for w in x["placed_in"] if w == f"{skill}:Advance"}
        assert placed == set(KINDS[skill]) | LATER[skill], skill
        for c in KINDS[skill]:
            fmt = CASES[c]["match"].get("fmt")
            assert fmt == FMT[c], (c, fmt)  # a case names its kind, or the drawer has nothing to draw it with
            assert CASES[c]["match"].get("operation") == "MUL" or c == "Q15", c


@pytest.mark.parametrize("skill", THREE)
def test_every_advance_draws_its_own_cases_as_measured(skill):
    """Every kind case drawn, each question its case as measured, no two alike, each answer the product worked out here,
    and every wrong answer it names one of its skill's mistakes."""
    drawn = _drawn(skill)
    assert {c for c, _ in drawn} == set(KINDS[skill])
    assert len({it.item_id for _, it in drawn}) == len(drawn)
    matches, named = _matches(_check(skill)), set(SETS[skill]["misconception_codes"])
    for case, it in drawn:
        assert it.fmt == FMT[case], (case, it.fmt)
        assert taxonomy.matches(matches[case], it.fmt, tags.derive(it)), (skill, case, it.spec)
        a, b = it.spec.get("a"), it.spec.get("b")
        if (
            isinstance(a, int)
            and isinstance(b, int)
            and not it.spec.get("missing")
            and any(r.rid == "ans" for r in it.responses)
        ):
            assert it.spec["op"] == "×" and _resp(it, "ans").answer == str(a * b), (case, it.spec)
        codes = {c for r in it.responses for c in (r.misconceptions or {})}
        assert codes and codes <= named, (case, codes - named)


def test_a_times_advance_question_has_one_home():
    """Placed as a child's answer is placed (`assess/placing.py`), every question lands on its own skill's Advance."""
    sets = list(SETS.values())
    matches = {c: x["match"] for c, x in CASES.items()}
    for skill in THREE:
        for case, it in _drawn(skill):
            got = placing.place(it.fmt, tags.derive(it), sets, matches)
            assert got and got[0]["code"] == skill and got[1] == "Advance", (skill, case, it.spec, got)


# ---------------------------------------------------------------------------------------------- the kinds, by hand


def _fillings(a, b, c):
    """Every digit filling that makes `a × b = c` true, a leading box never 0."""
    rows = [a, b, c]
    boxes = [(r, i) for r, s in enumerate(rows) for i, ch in enumerate(s) if ch == "□"]
    out = []
    for fill in itertools.product(range(10), repeat=len(boxes)):
        s = [list(x) for x in rows]
        for (r, i), d in zip(boxes, fill):
            s[r][i] = str(d)
        if any(x[0] == "0" and len(x) > 1 for x in s):
            continue
        x, y, z = (int("".join(v)) for v in s)
        if x * y == z:
            out.append(fill)
    return out


def _others(a, b, row, col):
    """The digits other than the right one that make the box's column come out alone: a child who works the column
    by itself, the carry from the right forgotten or the carry it sends unchecked. 2□ × 4 = 92: 8 × 4 ends in 2 too."""
    c, da = a * b, str(a)[::-1]
    if row == "RESULT":
        return {int(da[col]) * b % 10} - {int(str(c)[::-1][col])} if col < len(da) else set()
    right = int(da[col])
    if col == len(da) - 1:  # the lead: the whole rest of the answer, carry and all
        return {x for x in range(1, 10) if x * b == c // 10**col} - {right}
    return {x for x in range(10) if x * b % 10 == int(str(c)[::-1][col])} - {right}


def test_a_missing_digit_in_a_multiplication_has_one_answer_and_names_the_forgotten_carry():
    """Exactly one filling makes it true; the boxes ask for that filling; a box whose column alone another digit
    satisfies names that digit (M_MISSING_DIGIT_LOCAL), worked out here; and every question names one."""
    seen = 0
    for skill in ("MUL.2D1D", "MUL.3D1D"):
        for it in _of(skill, "Q07", "Q08", "Q11", "Q16"):
            sp = it.spec
            assert sp["op"] == "×"
            fills = _fillings(sp["a"], sp["b"], sp["c"])
            assert len(fills) == 1, sp
            assert [r.answer for r in it.responses] == [str(d) for d in fills[0]], sp
            a, b = sp["solved"]["a"], sp["solved"]["b"]
            boxes = [
                (row, len(s) - 1 - i)
                for row, s in (("FIRST", sp["a"]), ("RESULT", sp["c"]))
                for i, ch in enumerate(s)
                if ch == "□"
            ]
            named = 0
            for r, (row, col) in zip(it.responses, boxes):
                others = _others(a, b, row, col)
                got = r.misconceptions.get("M_MISSING_DIGIT_LOCAL")
                assert got == (next(iter(others)) if len(others) == 1 else None), (sp, row, col, others)
                named += got is not None
            assert named, sp
            seen += 1
    assert seen


def _concat(a, b):
    return int("".join(str(int(d) * b) for d in str(a)))


def _no_carry(a, b):
    return int("".join(str(int(d) * b % 10) for d in str(a)))


def _onto_zero_lost(a, b):
    out, carry = [], 0
    for d in map(int, str(a)[::-1]):
        carry = 0 if d == 0 else carry  # a carry that lands on a 0 is lost
        v = d * b + carry
        out.append(v % 10)
        carry = v // 10
    return int(str(carry or "") + "".join(map(str, out[::-1])))


def _placeholder(a, b):
    return a * (b % 10) + a * (b // 10)  # the second row not moved its place


BY_HAND = {
    "M_MUL_CONCAT": _concat,
    "M_MUL_NO_CARRY": _no_carry,
    "M_MUL_CARRY_ONTO_ZERO_LOST": _onto_zero_lost,
    "M_MUL_PLACEHOLDER": _placeholder,
}


def test_a_planted_multiplication_mistake_is_the_one_the_predictors_compute():
    """The worked answer shown is the planted mistake's, worked here by hand, and the one `predict` gives; the child
    is asked the first wrong column, the right answer, and why."""
    seen = set()
    for skill in THREE:
        for case, it in _drawn(skill):
            if it.fmt != "find_mistake":
                continue
            sp = it.spec
            a, b, code = sp["a"], sp["b"], sp["planted"]
            assert code == CASES[case]["match"]["planted"]
            assert sp["op"] == "×" and sp["wrong"] == BY_HAND[code](a, b) == M.predict("×", a, b)[code], sp
            assert sp["wrong"] != a * b and str(sp["wrong"]) in it.stem and f"{a} × {b}" in it.stem
            assert [r.rid for r in it.responses] == ["where", "ans", "why"]
            assert _resp(it, "ans").answer == str(a * b)
            seen.add(code)
    assert seen == set(BY_HAND)


def test_an_estimate_is_the_one_its_rounding_gives():
    """Each shape asks its judgement first, then the exact product: the larger number rounded to the ten (48 × 6 ≈
    300), both rounded (38 × 21 ≈ 800), how many digits the product has, the digit it ends in."""
    want = {
        "ROUND_ONE": lambda a, b: _half_up(max(a, b)) * min(a, b),
        "ROUND_BOTH": lambda a, b: _half_up(a) * _half_up(b),
        "ANSWER_DIGITS": lambda a, b: len(str(a * b)),
        "LAST_DIGIT": lambda a, b: a * b % 10,
    }
    seen = set()
    for skill in THREE:
        for case, it in _drawn(skill):
            if it.fmt != "estimate_then_calc":
                continue
            sp = it.spec
            shape = CASES[case]["match"]["shape"]
            assert sp["shape"] == shape and sp["op"] == "×"
            assert _resp(it, "est").answer == str(want[shape](sp["a"], sp["b"])), sp
            assert _resp(it, "ans").answer == str(sp["a"] * sp["b"])
            seen.add(shape)
    assert seen == set(want)


def test_a_times_story_is_its_templates_shape_and_its_answer_the_product():
    """The story's template says its shape and that it multiplies (`word_templates.json`); its two numbers are in its
    sentence and the answer is their product."""
    seen = set()
    for skill in THREE:
        for case, it in _drawn(skill):
            if it.fmt != "word_1step":
                continue
            tpl, sp = template_of(it.stem), it.spec
            assert tpl and tpl["op"] == "×" and tpl["structure"] == CASES[case]["match"]["structure"], it.stem
            assert str(sp["a"]) in it.stem and str(sp["b"]) in it.stem
            assert _resp(it, "ans").answer == str(sp["a"] * sp["b"])
            seen.add(tpl["structure"])
    assert seen == {"RATE_TOTAL", "TIMES_AS_MANY_LARGER", "COMBINATIONS"}


def test_a_shortcut_is_worked_the_way_it_is_named():
    """× 5 as × 10 then halved: the step is the other number times 10. Near a round number: the step is the round
    number's product, and the answer takes the extra group away (19 × 6 = 20 × 6 − 6)."""
    seen = set()
    for it in _of("MUL.2D1D", "H01", "H07"):
        sp = it.spec
        a, b = sp["a"], sp["b"]
        step = int(_resp(it, "step").answer)
        if sp["strategy"] == "TIMES_TEN_THEN_HALVE":
            assert 5 in (a, b) and step == (a if b == 5 else b) * 10 and step // 2 == a * b, sp
        else:
            assert sp["strategy"] == "COMPENSATION"
            near = max(a, b)
            assert near % 10 in (1, 9) and step == _half_up(near) * min(a, b), sp
        assert _resp(it, "ans").answer == str(a * b)
        seen.add(sp["strategy"])
    assert seen == {"TIMES_TEN_THEN_HALVE", "COMPENSATION"}


def test_a_missing_row_is_the_second_row_moved_its_place():
    """34 × 26 = 204 + □: the box is 34 × 20, and a child who does not move the row writes 68 (M_MUL_PLACEHOLDER)."""
    drawn = _of("MUL.2D2D", "Q15")
    assert drawn
    for it in drawn:
        sp = it.spec
        a, b = sp["a"], sp["b"]
        assert sp["text"] == f"{a} × {b} = {a * (b % 10)} + □" and b % 10 and b // 10
        r = _resp(it, "ans")
        assert r.answer == str(a * (b // 10) * 10)
        assert r.misconceptions.get("M_MUL_PLACEHOLDER") == a * (b // 10)


def test_every_times_kind_prints_its_sign():
    """Printed, each kind shows × (a story in its words), never the + or − a kind made only for those printed."""
    for skill in THREE:
        for case, it in _drawn(skill):
            html = render.render_item(Sheet("CS000000", "G4", "Advance", 1, "W1", [it]), it, 1)
            assert "×" in html or it.fmt == "word_1step", (case, it.fmt)  # a story says it in words
            text = re.sub(r"<[^>]+>", " ", html)
            assert "−" not in text, (case, it.fmt)
            if case != "Q15":  # a missing row adds its two rows
                assert not re.search(r"\d\s*\+\s*[\d□]", text), (case, it.fmt, text[:200])


# ---------------------------------------------------------------------------------------------- the whole loop


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_every_advance_fills_its_worksheets(conn):
    """Each Advance holds questions enough for its worksheets, and the library makes at least ten of each."""
    from engine.w2_print import library

    library.build(conn)
    for skill in THREE:
        n = conn.execute(
            "select count(*) as n from sheet_template where source = 'library' and retired_at is null"
            " and skill_set_code = %s and difficulty = 'Advance'",
            (skill,),
        ).fetchone()["n"]
        assert n >= library.MIN_PER_LEVEL, (skill, n)
