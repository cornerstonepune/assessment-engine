"""The tables' and the tens' Advance levels hold the kinds the drafted document places on them, × and ÷
(goals/md3b1-facts-advance.yaml), each drawn from its level's own numbers as a straight question is. Every check here
reads the question as it is printed, never the generator: a box's answer is the one number that makes its own sentence
true, tried number by number, and a mistake is worked from its definition."""

import dataclasses
import functools
import json
import os
import pathlib
import random
import re
from collections import defaultdict

import pytest

from engine.assess import draw, placing, render, stale, tags, taxonomy, verify
from engine.assess.pick import Sheet
from engine.assess.words import template_of
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
KINDS = {
    "MUL.FACTS": ["Q01", "Q02", "Q06", "Y09", "H08"],
    "MUL.TENS": ["Q14", "H10"],
    "DIV.FACTS": ["Q03", "Q04", "Q05", "G20", "B07"],
}
FMT = {
    **dict.fromkeys(["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q14"], "missing_number"),
    "Y09": "fact_family",
    "G20": "inverse_check",
    **dict.fromkeys(["H08", "H10"], "efficient_method"),
    "B07": "word_1step",
}
SIGN = {"MUL.FACTS": "×", "MUL.TENS": "×", "DIV.FACTS": "÷"}
# The document's placements no level holds yet, each with the slice of BUILD-ORDER that will hold them. A slice's line
# goes when it is built: a placement it leaves unheld fails here, and so does a line nothing waits for.
SLICE_OF = {
    "DIV.2D1D:Advance": "M3b2",
    "DIV.3D1D:Advance": "M3b2",
    "DIV.2D1D:method": "M3d",
    "DIV.3D1D:method": "M3d",
    "DIV.GROUPS": "M3c",
    **dict.fromkeys(["MD.WORD", "MD.MENTAL", "MD.MULTIPLES", "MD.EQUALITY", "MD.ESTIMATE"], "M4"),
}
POWERS = (10, 100, 1000)


def _check(skill, level="Advance"):
    return SETS[skill]["difficulty"][level]["check"]


def _matches(check):
    """The level's cases on its own numbers, as the bank reads them (`cases.on_level`)."""
    return cases.on_level(check, {c: row["match"] for c, row in CASES.items()})


@functools.cache
def _drawn(skill, n=60, seed=7):
    """[(case, question)] for a level's new kinds only: what this slice makes."""
    kinds = {**_check(skill), "cases": KINDS[skill]}
    return draw.level(random.Random(seed), kinds, _matches(kinds), SETS[skill]["rung_code"], n)


def _of(skill, *codes):
    return [it for c, it in _drawn(skill) if c in codes]


def _resp(it, rid):
    return next(r for r in it.responses if r.rid == rid)


def _value(side):
    """A side of a printed sentence as a number: "42 ÷ 6" is 7, "28" is 28; None when it is no whole number."""
    side = side.strip()
    m = re.fullmatch(r"(\d+)\s*([+−×÷-])\s*(\d+)", side)
    if not m:
        return int(side) if side.isdigit() else None
    x, op, y = int(m[1]), m[2], int(m[3])
    if op == "÷":
        return x // y if y and x % y == 0 else None
    return {"+": x + y, "−": x - y, "-": x - y, "×": x * y}[op]


def _solutions(sentence):
    """Every whole number that makes a printed sentence true, every □ in it that one number: "8 × □ = 72" is [9],
    "□ × □ = 49" [7]; a sentence ending "=" asks its answer. Tried number by number, to 13 times its largest number."""
    s = sentence.strip()
    s = s + " □" if s.endswith("=") else s
    top = max([int(x) for x in re.findall(r"\d+", s)] + [1]) * 13
    out = []
    for v in range(top + 1):
        left, right = s.replace("□", str(v)).split("=")
        x, y = _value(left), _value(right)
        if x is not None and x == y:
            out.append(v)
    return out


def _codes(it):
    return {c for r in it.responses for c in (r.misconceptions or {})}


# ---------------------------------------------------------------------------------------------- the rows


def test_each_advance_holds_its_documents_kind_cases():
    """Each Advance holds what it held, and after it the document's cases of the kinds an Advance asks for on that
    skill, each case naming its kind and its operation, on the skill's own numbers."""
    for skill, kinds in KINDS.items():
        check = _check(skill)
        assert check["cases"][-len(kinds) :] == kinds, skill
        placed = {c for c, x in DOC.items() for w in x["placed_in"] if w == f"{skill}:Advance"}
        assert placed <= set(check["cases"]), (skill, placed - set(check["cases"]))
        for c in kinds:
            match = CASES[c]["match"]
            assert match.get("fmt") == FMT[c], (c, match.get("fmt"))
            assert match.get("operation") == ("DIV" if SIGN[skill] == "÷" else "MUL"), c


def _held(skill, level, code):
    """Whether a level holds a case: one it lists, a written method any of its levels prints in, or any case of the one
    native kind a level is made of (MUL.GROUPS's equal groups)."""
    s = SETS.get(skill)
    if s is None:
        return False
    if level == "method":
        return any(code in (d["check"].get("methods") or []) for d in s["difficulty"].values())
    d = s["difficulty"].get(level)
    return d is not None and ("cases" not in d["check"] or code in d["check"]["cases"])


def test_every_case_the_document_places_on_a_level_is_held_or_its_slice_named():
    """Seven cases the document placed on MUL.FACTS's and MUL.TENS's Advance were held by no level and waited for no
    slice (STATE.md "M3b — measured before the build"). Every placement is held now, or waits for a slice BUILD-ORDER
    names; and a slice named here still has a placement waiting for it."""
    order = (ROOT / "BUILD-ORDER.md").read_text()
    waiting = defaultdict(list)
    for code, c in sorted(DOC.items()):
        for where in c["placed_in"]:
            skill, level = where.split(":")
            if _held(skill, level, code):
                continue
            key = where if where in SLICE_OF else skill
            assert key in SLICE_OF, (
                f"{code} is placed on {where}, which neither holds it nor waits for a slice"
            )
            waiting[key].append(code)
    for key, name in SLICE_OF.items():
        assert f"| {name} |" in order, (key, name)
        assert waiting[key], f"{key} waits for {name} but every case placed there is held: its line goes"


# ---------------------------------------------------------------------------------------------- drawn


@pytest.mark.parametrize("skill", list(KINDS))
def test_every_advance_draws_its_kind_cases_as_measured(skill):
    """Every kind case drawn on its level's own numbers, each question its case as measured, no two alike, every box's
    answer the one number its own sentence allows, and every wrong answer it names one of its skill's mistakes."""
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
            assert all(v != r.answer and str(v) != r.answer for v in (r.misconceptions or {}).values()), r
        assert stale.key_problems(it.fmt, it.spec, [dataclasses.asdict(r) for r in it.responses]) == []


def test_a_facts_advance_question_has_one_home():
    """Placed as a child's answer is placed (`assess/placing.py`), every question lands on its own skill's Advance."""
    sets = list(SETS.values())
    matches = {c: x["match"] for c, x in CASES.items()}
    for skill in KINDS:
        for case, it in _drawn(skill):
            got = placing.place(it.fmt, tags.derive(it), sets, matches)
            assert got and got[0]["code"] == skill and got[1] == "Advance", (skill, case, it.spec, got)


# ---------------------------------------------------------------------------------------------- the kinds, by hand


def _sentence(it):
    return it.spec["text"]


def test_a_missing_factor_or_divisor_has_one_answer_and_names_the_operation_misread():
    """8 × □ = 72 has one answer, 9; a child who reads × as + writes 64 (M_WRONG_OP), one who reads the table one row
    out 8 (M_MUL_ROW_OUT). □ ÷ 4 = 7 has one, 28; ÷ read as − takes 4 away once: 11 (M_DIV_SUBTRACTED). 56 ÷ □ = 8 has
    one, 7; read as − it is 48, and the two numbers multiplied 448 (M_WRONG_OP), as + and − name theirs."""
    pairs = [("MUL.FACTS", "Q01"), ("MUL.FACTS", "Q02"), ("DIV.FACTS", "Q03"), ("DIV.FACTS", "Q04")]
    for skill, case in pairs:
        drawn = _of(skill, case)
        assert drawn, case
        for it in drawn:
            text, r = _sentence(it), _resp(it, "ans")
            assert _solutions(text) == [int(r.answer)], (case, text)
            hidden = int(r.answer)
            m = re.fullmatch(r"(□|\d+) ([×÷]) (□|\d+) = (\d+)", text)
            assert m, text
            x, op, y, c = m[1], m[2], m[3], int(m[4])
            if op == "×":
                known = int(y if x == "□" else x)
                want = {"M_WRONG_OP": c - known, "M_MUL_ROW_OUT": hidden - 1}
            elif x == "□":
                want = {"M_DIV_SUBTRACTED": c + int(y)}
            else:
                want = {"M_DIV_SUBTRACTED": int(x) - c, "M_WRONG_OP": int(x) * c}
            want = {k: v for k, v in want.items() if v != hidden and v >= 0}
            assert r.misconceptions == want, (case, text, r.misconceptions)


def test_the_box_first_asks_the_divisions_own_answer():
    """□ = 63 ÷ 9: the box is the quotient, written first; exact, as the number divided and the divisor missing are,
    and keyed by the mistakes the same division asked the usual way names."""
    drawn = _of("DIV.FACTS", "Q05")
    assert drawn
    for it in drawn:
        m = re.fullmatch(r"□ = (\d+) ÷ (\d+)", _sentence(it))
        assert m, _sentence(it)
        a, b = int(m[1]), int(m[2])
        assert a % b == 0 and tags.derive(it)["answer_first"] == "YES"
        r = _resp(it, "ans")
        assert r.answer == str(a // b)
        assert r.misconceptions.get("M_WRONG_OP") == a * b, r.misconceptions
        assert a - b == a // b or r.misconceptions.get("M_DIV_SUBTRACTED") == a - b, r.misconceptions


def test_the_same_number_in_both_boxes_is_a_square():
    """□ × □ = 49: one number in both boxes, 7, written once; one row out it is 6, and read as □ + □ an even square is
    halved (64 answered 32)."""
    drawn = _of("MUL.FACTS", "Q06")
    assert len(drawn) >= 8
    for it in drawn:
        m = re.fullmatch(r"□ × □ = (\d+)", _sentence(it))
        assert m, _sentence(it)
        n, r = int(m[1]), _resp(it, "ans")
        k = int(r.answer)
        assert _solutions(_sentence(it)) == [k] and k * k == n and 2 <= k <= 12
        want = {"M_MUL_ROW_OUT": k - 1} | ({"M_WRONG_OP": n // 2} if n % 2 == 0 and n // 2 != k else {})
        assert r.misconceptions == want, (n, r.misconceptions)


def test_a_missing_place_value_factor_hides_the_factor():
    """45 × □ = 4500: the box hides 10, 100 or 1000, never the other number; that number has at most 2 digits, as
    × 1000's own case keeps it (TP03), so nothing reaches 9500 × 1000; one zero too few (10) and × read as + are named."""
    drawn = _of("MUL.TENS", "Q14")
    assert len(drawn) >= 10
    for it in drawn:
        m = re.fullmatch(r"(□|\d+) × (□|\d+) = (\d+)", _sentence(it))
        assert m, _sentence(it)
        r = _resp(it, "ans")
        hidden, known, c = int(r.answer), int(m[2] if m[1] == "□" else m[1]), int(m[3])
        assert _solutions(_sentence(it)) == [hidden] and hidden in POWERS, _sentence(it)
        assert len(str(min(known, hidden))) <= 2, _sentence(it)
        want = {"M_TENS_ZERO_DROPPED": hidden // 10, "M_WRONG_OP": c - known}
        assert r.misconceptions == {k: v for k, v in want.items() if v != hidden}, (
            _sentence(it),
            r.misconceptions,
        )


def test_a_fact_family_is_the_three_facts_its_fact_makes():
    """4 × 7 = 28 gives 7 × 4 = □, 28 ÷ 4 = □ and 28 ÷ 7 = □, as 7 + 5 = 12 gives its three: each box the one number
    its fact allows, the two numbers never equal (7 × 7 has two facts, not four), and each keyed as the same sum asked
    the usual way: × read as + in the first, the two numbers multiplied and the divisor taken away in a division."""
    drawn = _of("MUL.FACTS", "Y09")
    assert drawn
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        c = a * b
        assert a != b and it.spec["given"] == f"{a} × {b} = {c}" and it.spec["shape"] == "FROM_MULTIPLICATION"
        labels = [r.label for r in it.responses]
        assert labels == [f"{b} × {a} = □", f"{c} ÷ {a} = □", f"{c} ÷ {b} = □"], labels
        for r in it.responses:
            assert _solutions(r.label) == [int(r.answer)], r.label
        first, by_a, by_b = it.responses
        assert first.misconceptions.get("M_WRONG_OP") == a + b
        for r, d in ((by_a, a), (by_b, b)):
            assert r.misconceptions.get("M_WRONG_OP") == c * d, r.misconceptions
            assert c - d == c // d or r.misconceptions.get("M_DIV_SUBTRACTED") == c - d, r.misconceptions


def test_the_table_backwards_is_answered_by_dividing_and_by_its_fact():
    """42 ÷ 6 = □ because 6 × □ = 42: printed as the document's example, both boxes 7, a table fact read backwards with
    nothing left over. The division's box names the division's mistakes, the fact's a missing factor's."""
    drawn = _of("DIV.FACTS", "G20")
    assert drawn
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        assert it.spec["op"] == "÷" and it.spec["shape"] == "TABLE_BACKWARDS"
        assert a % b == 0 and 2 <= b <= 12 and 2 <= a // b <= 12
        q, f = _resp(it, "ans"), _resp(it, "fact")
        assert (q.label, f.label) == (f"{a} ÷ {b} = □", f"{b} × □ = {a}")
        assert _solutions(q.label) == _solutions(f.label) == [int(q.answer)] == [int(f.answer)] == [a // b]
        assert q.misconceptions.get("M_WRONG_OP") == a * b
        assert f.misconceptions == {
            k: v for k, v in {"M_WRONG_OP": a - b, "M_MUL_ROW_OUT": a // b - 1}.items() if v != a // b
        }


def test_a_fact_from_a_known_fact_starts_from_the_row_above():
    """7 × 8 = 56, so 7 × 9 = □: the fact given is the row above the one asked, and a child who stops at it writes 56
    (M_MUL_ROW_OUT), the table one row out."""
    drawn = _of("MUL.FACTS", "H08")
    assert drawn
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        assert it.spec["strategy"] == "FACT_DERIVED" and 2 <= b <= 12 and 2 <= a <= 12
        assert it.stem.startswith(f"{a} × {b - 1} = {a * (b - 1)}."), it.stem
        r = _resp(it, "ans")
        assert r.label == f"{a} × {b} =" and _solutions(r.label) == [int(r.answer)] == [a * b]
        assert r.misconceptions.get("M_MUL_ROW_OUT") == a * (b - 1)


def test_a_fact_scaled_by_ten_is_worked_from_its_fact():
    """6 × 7 = 42, so 60 × 7 = □ and 600 × 7 = □: the fact given, then the round number ten times and a hundred times
    its table number, each box one zero more, and a zero too few named in each."""
    drawn = _of("MUL.TENS", "H10")
    assert len(drawn) >= 10
    for it in drawn:
        a, b = it.spec["a"], it.spec["b"]
        f = a // 10
        assert it.spec["strategy"] == "SCALED_FACT" and a == f * 10 and 2 <= f <= 12 and 2 <= b <= 12
        assert 10 not in (f, b), it.spec
        assert it.stem.startswith(f"{f} × {b} = {f * b}."), it.stem
        labels = [r.label for r in it.responses]
        assert labels == [f"{a} × {b} =", f"{a * 10} × {b} ="], labels
        for r in it.responses:
            assert _solutions(r.label) == [int(r.answer)]
            assert r.misconceptions.get("M_TENS_ZERO_DROPPED") == int(r.answer) // 10, r.misconceptions


def test_the_cost_of_one_is_an_exact_division_in_its_templates_words():
    """8 pencils cost ₹48. What does one cost? A template row's words, the shape the row names, exact, the answer the
    quotient, and multiplying the two numbers named (M_WRONG_OP)."""
    drawn = _of("DIV.FACTS", "B07")
    assert drawn
    for it in drawn:
        tpl = template_of(it.stem)
        assert tpl and tpl["op"] == "÷" and tpl["structure"] == "RATE_UNIT", it.stem
        a, b = it.spec["a"], it.spec["b"]
        assert a % b == 0 and str(a) in it.stem and str(b) in it.stem
        r = _resp(it, "ans")
        assert r.answer == str(a // b) and r.misconceptions.get("M_WRONG_OP") == a * b


def test_the_documents_slips_are_corrected_where_they_were_drafted():
    """Measured before the build (STATE.md "M3b"): Y10 (a check by multiplying, no table fact) and H09 (÷ 5 as ÷ 10
    then doubled, 240 ÷ 5) could hold nothing on DIV.FACTS and DIV.TENS, and move to the levels their examples are; the
    box first and the cost of one are exact, as the number divided and the divisor missing are; a missing place-value
    factor is of a number to 2 digits, as × 1000's own case is; the table backwards is printed as its example."""
    assert DOC["Y10"]["placed_in"] == ["DIV.2D1D:Advance", "MD.EQUALITY:Medium"]
    assert DOC["H09"]["placed_in"] == ["DIV.3D1D:Advance", "MD.MENTAL:Hard"]
    assert CASES["Q05"]["match"]["remainder"] == "NONE" and CASES["B07"]["match"]["remainder"] == "NONE"
    assert CASES["Q14"]["match"]["digits_min"] == {"lte": 2}
    assert CASES["G20"]["match"]["shape"] == "TABLE_BACKWARDS" and "shape" not in CASES["Y10"]["match"]
    # why they moved, in the numbers: every exact division read off a table is a table fact, so no question is Y10's
    # (no fact, nothing left) and DIV.FACTS's (read off a table); and 240 ÷ 5 has no fact under its zero
    for b in range(1, 13):
        for a in range(0, 13 * b):
            t = tags.derive(verify.division(a, b, "R42"))
            assert not (t["from_table"] == "YES" and t["remainder"] == "NONE" and t["fact"] == "NO"), (a, b)
    assert tags.derive(verify.division(240, 5, "R43"))["place_value_factor"] == "NONE"


def test_a_scenario_recomputes_every_box_from_its_printed_sentence():
    """A scenario counted a question it could not recompute as recomputed. Every box of these kinds is recomputed from
    its own sentence now, one changed box fails it, and the count says how many were recomputed."""
    for skill in KINDS:
        for case, it in _drawn(skill)[:12]:
            assert scenarios._answer_is_right(it) is True, (case, it.spec)
            for i, r in enumerate(it.responses):
                if r.kind != "digits":
                    continue
                bad = list(it.responses)
                bad[i] = dataclasses.replace(r, answer=str(int(r.answer) + 1))
                assert scenarios._answer_is_right(dataclasses.replace(it, responses=bad)) is False, (
                    case,
                    r.rid,
                )


def test_every_new_kind_prints_its_numbers_and_sign():
    """On paper each question shows its own numbers and its sign (a story says it in words), and a box for every
    answer it asks."""
    for skill in KINDS:
        for case, it in _drawn(skill):
            html = render.render_item(Sheet("CS000000", "G4", "Advance", 1, "W1", [it]), it, 1)
            text = re.sub(r"<[^>]+>", " ", html)
            assert SIGN[skill] in text or it.fmt == "word_1step", (case, text[:200])
            # a missing number shows the numbers of its sentence, the one its box hides not among them
            shown = it.spec["text"] if it.fmt == "missing_number" else f"{it.spec['a']} {it.spec['b']}"
            for n in re.findall(r"\d+", shown):
                assert re.search(rf"(?<!\d){n}(?!\d)", text), (case, n, text[:300])
            boxes = set(re.findall(r'data-r="([^"]+)"', html))
            assert boxes == {r.rid for r in it.responses}, (case, boxes)


# ---------------------------------------------------------------------------------------------- the whole loop


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_every_advance_fills_its_worksheets(conn):
    """Each Advance holds questions enough for its worksheets, its kinds among them, and the library makes at least
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
