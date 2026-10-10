"""Finding the mistake in a division (goals/md3b3-divide-mistakes-and-stories.yaml): on DIV.2D1D a remainder too big
(C05), on DIV.3D1D the zero left out of the quotient (C04) and the last digit never brought down (C07), each a worked
answer with its named mistake made on the level's own numbers (STATE.md "M3b3 — measured before the build"). Every
expected value is worked here from the named mistakes' own predictors and from the division itself, never read back
from the code under test."""

import functools
import json
import pathlib
import random

import pytest

from engine.assess import div_mistakes as DM
from engine.assess import divide_kinds as DK
from engine.assess import draw, md_tags, tags, taxonomy
from engine.assess import draw_case as K
from engine.assess import draw_divide as DD
from engine.w1_bank import cases

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase/seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
ROWS = json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
FOUND = {
    "DIV.2D1D": {"C05": "M_DIV_REMAINDER_TOO_BIG"},
    "DIV.3D1D": {"C04": "M_DIV_QUOTIENT_ZERO_DROPPED", "C07": "M_DIV_BRING_DOWN_MISSED"},
}
EACH = [(skill, case, code) for skill, found in FOUND.items() for case, code in found.items()]
# every division each level holds where its mistake changes the worked answer (STATE.md "M3b3 — measured")
MEASURED = {"C05": 254, "C04": 1170, "C07": 7035}


def _check(skill):
    return SETS[skill]["difficulty"]["Advance"]["check"]


def _matches(check):
    """The level's cases on its own numbers, as the bank reads them (`cases.on_level`)."""
    return cases.on_level(check, {c: row["match"] for c, row in CASES.items()})


@functools.cache
def _drawn(skill, case, n=24, seed=11):
    """`n` questions of one case on its level's own numbers, as the bank draws them."""
    check = {**_check(skill), "cases": [case]}
    return [
        it for _, it in draw.level(random.Random(seed), check, _matches(check), SETS[skill]["rung_code"], n)
    ]


def _held(skill, a, b):
    """Whether a ÷ b is one of the level's own divisions, measured as a straight question's numbers are."""
    t = md_tags.two_numbers({}, "bare_sum", "÷", a, b, "line", {})
    return all(t.get(k) is not None and taxonomy.holds(v, t[k]) for k, v in _check(skill)["within"].items())


def _shown(got):
    """A worked answer as a child writes it: 20 r 5, or 12 with nothing left over."""
    q, r = got
    return f"{q} r {r}" if r else str(q)


@pytest.mark.parametrize(("skill", "case", "code"), EACH)
def test_a_worked_division_shows_its_named_mistake_on_the_levels_own_numbers(skill, case, code):
    """Each question is its case as measured, on its level's numbers (a 2- or 3-digit number divided by a 1-digit one),
    and its worked answer is what its named mistake writes on those numbers: 85 ÷ 4 = 20 r 5, 612 ÷ 6 = 12,
    516 ÷ 4 = 12 r 3."""
    within, match = _check(skill)["within"], _matches(_check(skill))[case]
    drawn = _drawn(skill, case)
    assert len(drawn) == 24 and len({it.item_id for it in drawn}) == 24
    for it in drawn:
        sp = it.spec
        a, b = sp["a"], sp["b"]
        assert it.fmt == "find_mistake" and sp["op"] == "÷" and sp["planted"] == code, sp
        assert (len(str(a)), len(str(b))) == (within["operand_1_digits"], within["operand_2_digits"]), sp
        assert _held(skill, a, b), sp
        wrote = DM.PREDICTORS[code](a, b)
        assert wrote is not None and DM.wrong(a, b, wrote), sp
        assert sp["wrong"] == _shown(wrote) and f"{a} ÷ {b} and wrote {_shown(wrote)}." in it.stem, it.stem
        assert taxonomy.matches(match, it.fmt, tags.derive(it)), (case, sp)


@pytest.mark.parametrize(("skill", "case", "code"), EACH)
def test_the_right_answer_goes_in_the_divisions_own_boxes(skill, case, code):
    """The right answer in the quotient's box and, where the division leaves one, the remainder's, each keyed as a
    straight division's are: by every value a named mistake writes there, the planted one among them."""
    for it in _drawn(skill, case):
        a, b = it.spec["a"], it.spec["b"]
        q, r = divmod(a, b)
        rs = {x.rid: x for x in it.responses}
        assert set(rs) == {"ans", "why"} | ({"rem"} if r else set()), (it.spec, set(rs))
        assert rs["ans"].kind == "digits" and rs["ans"].answer == str(q)
        assert rs["ans"].misconceptions == DM.in_box(a, b, 0), it.spec
        if r:
            assert rs["rem"].answer == str(r) and rs["rem"].misconceptions == DM.in_box(a, b, 1), it.spec
        wq, wr = DM.PREDICTORS[code](a, b)
        named = {**rs["ans"].misconceptions, **(rs["rem"].misconceptions if r else {})}
        assert code in named and wq in (q, rs["ans"].misconceptions.get(code)), it.spec
        assert not wr or wr == r or rs["rem"].misconceptions.get(code) == wr, it.spec


@pytest.mark.parametrize(("skill", "case", "code"), EACH)
def test_no_step_is_ticked_the_why_says_it(skill, case, code):
    """No box asks which step went wrong: for the last digit not brought down its answer would always be "bring down",
    which a child ticking the same box every time would score. The child says it in the why, which a person reads
    against the mistake's own row; the question names no mistake itself, in a code or in words of its own."""
    names = {r["name"] for r in ROWS}
    for it in _drawn(skill, case):
        rs = {x.rid: x for x in it.responses}
        assert "where" not in rs and not any(x.kind == "tick" for x in it.responses), it.spec
        why = rs["why"]
        assert why.kind == "text" and why.answer is None and why.rubric, why
        assert "M_" not in why.rubric and not any(n in why.rubric for n in names), why.rubric


@pytest.mark.parametrize(("skill", "case", "code"), EACH)
def test_every_division_a_level_holds_where_its_mistake_shows_is_a_question(skill, case, code):
    """Over every division the level holds (`draw_divide.every`), a question is made wherever the mistake changes the
    worked answer — 254, 1,170 and 7,035, as measured — and nowhere else: none is lost to a filter of the kind's own."""
    check = _check(skill)
    alt = taxonomy.within(CASES[case]["match"], check["within"])
    build = DK.builder(alt, "find_mistake")
    assert build is not None, alt
    made, rng = 0, random.Random(3)
    for a, b in DD.every(alt, K.pairs(alt, check, "÷")):
        if not _held(skill, a, b):
            continue
        shows = (w := DM.PREDICTORS[code](a, b)) is not None and DM.wrong(a, b, w)
        try:
            build(rng, a, b, SETS[skill]["rung_code"], alt)
            made += 1
            assert shows, (a, b)
        except RuntimeError:
            assert not shows, (a, b)
    assert made == MEASURED[case], (case, made)
