"""The column skills' Advance, ÷ (goals/md3b2-divide-advance.yaml): DIV.2D1D and DIV.3D1D hold the boxes, estimates and
checks the drafted document places on them, each drawn on its level's own numbers (ADR 0057) and each box keyed by the
act that finds it (STATE.md "M3b2 — measured before the build"). The mistake found and the remainder stories are M3b3's.
Every expected value here is worked from the named mistakes' own predictors, never read back from the code under test."""

import dataclasses
import functools
import json
import os
import pathlib
import random
import re

import pytest

from engine.assess import div_mistakes as DM
from engine.assess import draw, placing, render, stale, tags, taxonomy, verify
from engine.assess import misconceptions as M
from engine.assess import operations as O
from engine.assess.pick import Sheet
from engine.assess.rounding import half_up
from engine.checks import scenarios
from engine.core import db
from engine.w1_bank import cases

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase/seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
KINDS = {"DIV.2D1D": ["Q09", "Q12", "Q13", "V09", "Y10"], "DIV.3D1D": ["Q10", "V04", "V10", "H09"]}
# the document's other placements on these two levels: the mistake found and the remainder stories, M3b3's
LATER = {"DIV.2D1D": ["B14", "B15", "B16", "B17", "C05"], "DIV.3D1D": ["C04", "C07"]}
FMT = {
    **dict.fromkeys(["Q09", "Q10"], "missing_digit"),
    **dict.fromkeys(["Q12", "Q13"], "missing_number"),
    **dict.fromkeys(["V04", "V10"], "estimate_then_calc"),
    "V09": "possible_answer",
    "Y10": "inverse_check",
    "H09": "efficient_method",
}
GRADE = {"DIV.2D1D": "G3", "DIV.3D1D": "G4"}


def _check(skill):
    return SETS[skill]["difficulty"]["Advance"]["check"]


def _matches(check):
    """The level's cases on its own numbers, as the bank reads them (`cases.on_level`)."""
    return cases.on_level(check, {c: row["match"] for c, row in CASES.items()})


@functools.cache
def _drawn(skill, n=72, seed=7):
    check = _check(skill)
    return draw.level(random.Random(seed), check, _matches(check), SETS[skill]["rung_code"], n)


def _of(skill, code):
    return [it for c, it in _drawn(skill) if c == code]


def _resp(it, rid):
    return next(r for r in it.responses if r.rid == rid)


def _codes(it):
    return {c for r in it.responses for c in (r.misconceptions or {})}


def _at(n, place):
    """`n`'s digit `place` from the ones (0 is the ones); None past its lead."""
    s = str(n)
    return int(s[-1 - place]) if place < len(s) else None


def _division(text):
    """(number divided, divisor, quotient, remainder or None) of a printed division, each as printed."""
    m = re.fullmatch(r"(\S+) ÷ (\S+) = (\S+)(?: r (\S+))?", text)
    assert m, text
    return m[1], m[2], m[3], m[4]


def _each(text):
    """Every value of the one □ in a printed division that makes it true, its remainder less than its divisor: a digit
    where □ sits among digits (no number led by 0), a whole number to the number divided where it stands alone."""
    parts = list(_division(text))
    k = next(i for i, p in enumerate(parts) if p and "□" in p)
    alone = parts[k] == "□"
    out = []
    for v in range(int(parts[0].replace("□", "9")) + 1) if alone else range(10):
        filled = [p.replace("□", str(v)) if p else "0" for p in parts]
        a, b, q, r = (int(p) for p in filled)
        if b and not (len(filled[k]) > 1 and filled[k][0] == "0") and a == q * b + r and r < b:
            out.append(v)
    return out


def _same(a, b):
    """The division a ÷ b asked the usual way, its boxes keyed as M3a keys them."""
    return verify.division(a, b, "R45")


# ---------------------------------------------------------------------------------------------- the rows


def test_each_column_advance_holds_the_documents_boxes_estimates_and_checks():
    """Each skill has an Advance now, of its document's grade, on Hard's numbers, listing the document's kind cases this
    slice builds and no straight case Hard holds; each case names its kind and ÷."""
    for skill, kinds in KINDS.items():
        check = _check(skill)
        assert check["cases"] == kinds, (skill, check["cases"])
        assert check["within"] == SETS[skill]["difficulty"]["Hard"]["check"]["within"], skill
        assert SETS[skill]["level_band"]["Advance"] == GRADE[skill], skill
        for c in kinds:
            match = CASES[c]["match"]
            assert match.get("fmt") == FMT[c] and match.get("operation") == "DIV", (c, match)


def test_what_the_column_advances_still_wait_for_is_named():
    """The document's other placements on these levels, the mistake found and the remainder stories, wait for M3b3,
    which BUILD-ORDER names; nothing else is placed there."""
    assert "| M3b3 |" in (ROOT / "BUILD-ORDER.md").read_text()
    for skill in KINDS:
        placed = sorted(c for c, x in DOC.items() if f"{skill}:Advance" in x["placed_in"])
        assert placed == sorted(KINDS[skill] + LATER[skill]), (skill, placed)


# ---------------------------------------------------------------------------------------------- drawn


@pytest.mark.parametrize("skill", list(KINDS))
def test_every_column_advance_draws_its_cases_as_measured(skill):
    """Every case drawn on its level's own numbers, each question its case as measured, no two alike, every answer
    recomputed by the scenarios' own check, and every wrong answer it names one of its skill's mistakes."""
    drawn = _drawn(skill)
    assert {c for c, _ in drawn} == set(KINDS[skill])
    assert len({it.item_id for _, it in drawn}) == len(drawn)
    matches, named = _matches(_check(skill)), set(SETS[skill]["misconception_codes"])
    for case, it in drawn:
        assert it.fmt == FMT[case], (case, it.fmt)
        assert taxonomy.matches(matches[case], it.fmt, tags.derive(it)), (skill, case, it.spec)
        assert scenarios._answer_is_right(it) is True, (case, it.spec, [r.answer for r in it.responses])
        assert _codes(it) and _codes(it) <= named, (case, _codes(it) - named)
        for r in it.responses:
            assert all(str(v) != r.answer for v in (r.misconceptions or {}).values()), (case, r)
        assert stale.key_problems(it.fmt, it.spec, [dataclasses.asdict(r) for r in it.responses]) == []


def test_a_column_advance_question_has_one_home():
    """Placed as a child's answer is placed (`assess/placing.py`), every question lands on its own skill's Advance."""
    sets = list(SETS.values())
    matches = {c: x["match"] for c, x in CASES.items()}
    for skill in KINDS:
        for case, it in _drawn(skill):
            got = placing.place(it.fmt, tags.derive(it), sets, matches)
            assert got and got[0]["code"] == skill and got[1] == "Advance", (skill, case, it.spec, got)


def test_an_estimate_of_a_division_drawn_alone_never_crashes():
    """V04 and V10 drawn with no level around them crashed with KeyError 'digits': `times_kinds.sizes` read a ×
    rule's digits before anything asked the operation. Alone, each draws or refuses in a sentence."""
    for code in ("V04", "V10"):
        check = {"cases": [code]}
        try:
            draw.level(random.Random(5), check, _matches(check), "R45", 4)
        except O.CannotMake:
            pass


# ---------------------------------------------------------------------------------------------- the kinds, by hand


def test_a_digit_missing_in_the_number_divided_is_found_by_multiplying():
    """7□ ÷ 4 = 18: exact, one digit fills it (2), found by multiplying 18 × 4. Its box names that multiplication's
    mistakes read at the box's place ("wrong operation" excepted: the child multiplied, as the question asks), and each
    mistake of the division that, made with another digit there, gives the quotient shown."""
    drawn = _of("DIV.2D1D", "Q09")
    assert len(drawn) >= 8
    for it in drawn:
        text = it.spec["text"]
        a_s, b_s, q_s, r_s = _division(text)
        assert "□" in a_s and r_s is None and "□" not in b_s + q_s, text
        box, b, q = _resp(it, "d1"), int(b_s), int(q_s)
        right = int(box.answer)
        a = int(a_s.replace("□", box.answer))
        assert _each(text) == [right] and a == q * b, text
        place = len(a_s) - 1 - a_s.index("□")
        want = {}
        for code, p in M.predict("×", q, b).items():
            d = _at(p, place) if isinstance(p, int) and p >= 0 else None
            if code != "M_WRONG_OP" and d is not None and d != right:
                want.setdefault(code, d)
        for d in range(10):
            if d == right or (place == len(a_s) - 1 and d == 0):
                continue
            for code, (q2, r2) in DM.predict(a + (d - right) * 10**place, b).items():
                if q2 == q and not r2:
                    want.setdefault(code, d)
        assert want and box.misconceptions == want, (text, box.misconceptions, want)


def test_a_digit_missing_in_the_quotient_names_the_divisions_mistakes_that_fit_its_boxes():
    """936 ÷ 3 = 3□2: exact, one digit fills it. Its box names each mistake of the division whose quotient is as long as
    the one printed, that quotient's digit in the box's place; a wrong quotient of another length does not fit the
    printed boxes and says nothing about this one (measured: 11% name none, and are drawn again)."""
    drawn = _of("DIV.3D1D", "Q10")
    assert len(drawn) >= 8
    for it in drawn:
        text = it.spec["text"]
        a_s, b_s, q_s, r_s = _division(text)
        assert "□" in q_s and r_s is None and "□" not in a_s + b_s, text
        a, b, box = int(a_s), int(b_s), _resp(it, "d1")
        assert _each(text) == [int(box.answer)] and a % b == 0, text
        q, pos = str(a // b), q_s.index("□")
        want = {}
        for code, (q2, _r2) in DM.predict(a, b).items():
            w = str(q2)
            if len(w) == len(q) and w[pos] != q[pos]:
                want.setdefault(code, int(w[pos]))
        assert want and box.misconceptions == want, (text, box.misconceptions, want)


def test_the_remainder_missing_is_found_by_taking_away():
    """85 ÷ 4 = 21 r □: one answer (1), found by taking 21 × 4 away from 85. No mistake of the division keeps the
    printed quotient (measured: 556 of 556 name none), so the box names the taking away's mistakes, and the
    multiplication's with its product taken away rightly ("wrong operation" excepted); and one group short leaves the
    division's own remainder too big (r + 4)."""
    drawn = _of("DIV.2D1D", "Q12")
    assert len(drawn) >= 8
    for it in drawn:
        text = it.spec["text"]
        a_s, b_s, q_s, r_s = _division(text)
        assert r_s == "□", text
        a, b, q, box = int(a_s), int(b_s), int(q_s), _resp(it, "ans")
        r = int(box.answer)
        assert _each(text) == [r] and 0 < r < b and a == q * b + r, text
        want = {}
        for code, v in M.predict("-", a, q * b).items():
            if code != "M_WRONG_OP" and isinstance(v, int) and 0 <= v != r:
                want.setdefault(code, v)
        for code, p in M.predict("×", q, b).items():
            if code != "M_WRONG_OP" and isinstance(p, int) and 0 <= a - p != r:
                want.setdefault(code, a - p)
        want.setdefault("M_DIV_REMAINDER_TOO_BIG", r + b)
        assert box.misconceptions == want, (text, box.misconceptions, want)


def test_the_divisor_missing_with_a_remainder_has_one_answer():
    """85 ÷ □ = 21 r 1: one divisor makes it true with its remainder less than it (4), the remainder some or the
    largest a divisor leaves, as the case says. Read as − it is 64 (M_DIV_SUBTRACTED) and the two numbers multiplied
    1785 (M_WRONG_OP), as M3b1's divisor box names them."""
    drawn = _of("DIV.2D1D", "Q13")
    assert len(drawn) >= 8
    for it in drawn:
        text = it.spec["text"]
        a_s, b_s, q_s, r_s = _division(text)
        assert b_s == "□" and r_s and r_s != "□", text
        a, q, box = int(a_s), int(q_s), _resp(it, "ans")
        d = int(box.answer)
        assert _each(text) == [d] and int(r_s) > 0, text
        want = {"M_DIV_SUBTRACTED": a - q, "M_WRONG_OP": a * q}
        assert box.misconceptions == {k: v for k, v in want.items() if v != d and v >= 0}, (
            text,
            box.misconceptions,
        )


def test_how_many_digits_a_quotient_has_is_asked_before_it_is_worked():
    """156 ÷ 4: how many digits its quotient has (2: the first digit is less than the divisor), then the quotient and
    any remainder, keyed as the division asked the usual way. Both lengths are asked, and the exact answer prints in as
    many boxes as the number divided has digits, so the boxes never answer the first question (M3b1)."""
    drawn = _of("DIV.3D1D", "V04")
    assert len(drawn) >= 8
    gaps = set()
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        assert it.spec["op"] == "÷" and it.spec["shape"] == "ANSWER_DIGITS", it.spec
        assert _resp(it, "est").answer == str(len(str(a // b)))
        for r in _same(a, b).responses:
            assert (_resp(it, r.rid).answer, _resp(it, r.rid).misconceptions) == (r.answer, r.misconceptions)
        assert {x.rid for x in it.responses} == {"est"} | {r.rid for r in _same(a, b).responses}
        gaps.add(len(str(a)) - len(str(a // b)))
        html = render.render_item(Sheet("CS000000", "G4", "Advance", 1, "W1", [it]), it, 1)
        assert html.count('data-r="ans"') == len(str(a)), it.spec
    assert gaps == {0, 1}


def test_an_estimate_rounds_the_number_divided_to_the_nearest_hundred():
    """412 ÷ 8 ≈ 400 ÷ 8 = 50: the number divided rounded to the nearest hundred, asked only where the divisor divides
    that hundred, so the estimate is the one its rounding gives; then the quotient and any remainder (51 r 4), keyed as
    the division asked the usual way."""
    drawn = _of("DIV.3D1D", "V10")
    assert len(drawn) >= 8
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        ra = half_up(a, 100)
        assert it.spec["shape"] == "ROUND_ONE" and it.spec["ra"] == ra and ra % b == 0, it.spec
        assert _resp(it, "est").answer == str(ra // b) and "nearest hundred" in it.stem, it.stem
        for r in _same(a, b).responses:
            assert (_resp(it, r.rid).answer, _resp(it, r.rid).misconceptions) == (r.answer, r.misconceptions)


def test_could_it_be_right_judges_the_remainder_against_the_divisor():
    """85 ÷ 4 = 20 r 5: could it be right? No: a remainder is less than the divisor, and this one is a group short. The
    claim is the right answer or that one group short, one as often as the other; a yes to the remainder too big names
    M_DIV_REMAINDER_TOO_BIG, and a no to the right answer M_REVERSES_CLAIM_TRUTH."""
    drawn = _of("DIV.2D1D", "V09")
    assert len(drawn) >= 10
    seen = set()
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        q, r = divmod(a, b)
        m = re.fullmatch(r"(\d+) r (\d+)", it.spec["claimed"])
        assert m and r > 0 and it.spec["claimed"] in it.stem, it.spec
        tick = _resp(it, "could")
        if (int(m[1]), int(m[2])) == (q, r):
            assert (tick.answer, tick.misconceptions) == ("yes", {"M_REVERSES_CLAIM_TRUTH": "no"})
        else:
            assert (int(m[1]), int(m[2])) == (q - 1, r + b), it.spec
            assert (tick.answer, tick.misconceptions) == ("no", {"M_DIV_REMAINDER_TOO_BIG": "yes"})
        seen.add(tick.answer)
    assert seen == {"yes", "no"}


def test_a_division_is_checked_by_multiplying():
    """96 ÷ 4 = 24? 24 × 4 = □: exact; the claim is the right answer or what a named mistake of the division layout
    writes, its remainder with it (96 ÷ 4 = 21 r 2, each digit divided alone), one as often as the other. The check
    multiplies the claim back and adds its remainder; its box names the multiplication's mistakes ("wrong operation"
    excepted, ADR 0057), and a verdict the wrong way round is M_REVERSES_CLAIM_TRUTH."""
    drawn = _of("DIV.2D1D", "Y10")
    assert len(drawn) >= 10
    seen = set()
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        m = re.fullmatch(r"(\d+)(?: r (\d+))?", it.spec["claimed"])
        assert m and a % b == 0, it.spec
        cq, cr = int(m[1]), int(m[2] or 0)
        right = (cq, cr) == (a // b, 0)
        layout = {
            (g[0], g[1] or 0)
            for c, g in DM.predict(a, b).items()
            if c.startswith("M_DIV_") and c != "M_DIV_SUBTRACTED"
        }
        assert right or (cq, cr) in layout, it.spec
        check = _resp(it, "check")
        assert check.label == (f"{cq} × {b} + {cr} = □" if cr else f"{cq} × {b} = □"), check.label
        assert check.answer == str(cq * b + cr)
        want = {
            c: p + cr
            for c, p in M.predict("×", cq, b).items()
            if c != "M_WRONG_OP" and isinstance(p, int) and 0 <= p != cq * b
        }
        assert check.misconceptions == want, (check.misconceptions, want)
        verdict = _resp(it, "right")
        assert verdict.answer == ("yes" if right else "no")
        assert verdict.misconceptions == {"M_REVERSES_CLAIM_TRUTH": "no" if right else "yes"}
        seen.add(verdict.answer)
    assert seen == {"yes", "no"}


def test_five_is_ten_then_doubled_on_a_number_with_no_fact_under_its_zero():
    """240 ÷ 5: first 240 ÷ 10 = 24, then doubled, 48. The number divided is a 3-digit number ending in 0 whose tens are
    no multiple of 5 (250 ÷ 5 is a fact under its zero, `DIV.TENS`'s); the step names one zero fewer taken away among
    its division's slips, and the answer what 240 ÷ 5 asked the usual way names."""
    drawn = _of("DIV.3D1D", "H09")
    assert len(drawn) >= 8
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        assert b == 5 and a % 10 == 0 and 100 <= a <= 999 and (a // 10) % 5, it.spec
        assert it.spec["strategy"] == "DIVIDE_BY_TEN_THEN_DOUBLE"
        step, ans = _resp(it, "step"), _resp(it, "ans")
        assert (step.label, step.answer) == (f"{a} ÷ 10 =", str(a // 10))
        assert step.misconceptions == DM.in_box(a, 10, 0) and "M_DIV_TENS_ZERO_LEFT" in step.misconceptions
        assert (ans.label, ans.answer) == (f"{a} ÷ 5 =", str(a // 5))
        assert ans.misconceptions == _resp(_same(a, 5), "ans").misconceptions


def test_a_scenario_recomputes_every_new_box():
    """Every box of these kinds is worked by the scenarios' own check from its own printed numbers, and one changed box
    fails it: a digit, a remainder, a divisor, an estimate, a step, a check and a verdict."""
    for skill in KINDS:
        for case, it in _drawn(skill)[:36]:
            assert scenarios._answer_is_right(it) is True, (case, it.spec)
            for i, r in enumerate(it.responses):
                bad = list(it.responses)
                if r.kind == "digits":
                    bad[i] = dataclasses.replace(r, answer=str(int(r.answer) + 1))
                elif r.kind == "tick":
                    bad[i] = dataclasses.replace(r, answer=next(o for o in r.options if o != r.answer))
                else:
                    continue
                assert scenarios._answer_is_right(dataclasses.replace(it, responses=bad)) is False, (
                    case,
                    r.rid,
                )


def test_every_new_kind_prints_its_numbers_and_sign():
    """On paper each question shows its own numbers and ÷, and a box for every answer it asks."""
    for skill in KINDS:
        for case, it in _drawn(skill)[:36]:
            html = render.render_item(Sheet("CS000000", GRADE[skill], "Advance", 1, "W1", [it]), it, 1)
            text = re.sub(r"<[^>]+>", " ", html)
            assert "÷" in text, (case, text[:200])
            shown = it.spec.get("text") or f"{it.spec['a']} {it.spec['b']}"
            for n in re.findall(r"\d+", shown):
                assert re.search(rf"(?<!\d){n}(?!\d)", text), (case, n, text[:300])
            assert set(re.findall(r'data-r="([^"]+)"', html)) == {r.rid for r in it.responses}, case


# ---------------------------------------------------------------------------------------------- the whole loop


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_every_column_advance_fills_its_worksheets(conn):
    """Each Advance holds questions enough for its worksheets, every kind among them, and the library makes at least
    ten worksheets of each."""
    from engine.w2_print import library

    library.build(conn)
    for skill, kinds in KINDS.items():
        n = conn.execute(
            "select count(*) as n from sheet_template where source = 'library' and retired_at is null"
            " and skill_set_code = %s and difficulty = 'Advance'",
            (skill,),
        ).fetchone()["n"]
        assert n >= library.MIN_PER_LEVEL, (skill, n)
        fmts = {
            r["fmt"]
            for r in conn.execute(
                "select distinct fmt from item where skill_set_code = %s and difficulty = 'Advance'"
                " and status = 'active'",
                (skill,),
            )
        }
        assert {FMT[c] for c in kinds} <= fmts, (skill, fmts)
