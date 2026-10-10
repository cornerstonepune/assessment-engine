"""Division as four skills, each level its document's own cases, drawn by the case drawer that makes the other three
operations (goals/md3a-straight-division.yaml).

The levels are held to the drafted document (docs/design/multiplication-division-cases.json, each case's
`placed_in`), the drawing to the cases as measured (`assess/tags.py`), and the answers and every label to arithmetic
done here: a quotient and its remainder, the digits divided one at a time from the left, never read back from the code
that made the question."""

import functools
import json
import os
import pathlib
import random
import re

import pytest

from engine.assess import draw, placing, render, tags, taxonomy, verify
from engine.assess.items import Item
from engine.assess.pick import Sheet
from engine.core import db
from engine.w1_bank import cases
from engine.w3_read import marking

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase/seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
RUNGS = {r["code"]: r for r in json.loads((SEED / "rungs.json").read_text())["rungs"]}
TOPICS = json.loads((SEED / "topics.json").read_text())["topics"]
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
FOUR = ["DIV.FACTS", "DIV.TENS", "DIV.2D1D", "DIV.3D1D"]
LEVELS = ["Easy", "Medium", "Hard", "Advance"]
STRAIGHT = set(draw.STRAIGHT)
# The document's grades (assumption A6), Easy · Medium · Hard · Advance
GRADES = {
    "DIV.FACTS": ["G2", "G2", "G2", "G3"],
    "DIV.TENS": ["G4", "G4", "G4", "G4"],
    "DIV.2D1D": ["G2", "G2", "G3"],
    "DIV.3D1D": ["G4", "G4", "G4"],
}
# The two whose Advance the document gives straight questions no lower level holds: the 11 and 12 tables, a 2-digit
# divisor and a remainder under a 1-digit quotient; ÷ 10, 100 or 1000 with a remainder. The other two have no Advance
# until M3b gives them the kinds an Advance needs, as multiplication's had none until M2b: an Advance of Hard's own
# questions is no level (`engine load` refuses two levels on one region).
ADVANCE = ["DIV.FACTS", "DIV.TENS"]
LEVELS_OF = {s: LEVELS if s in ADVANCE else LEVELS[:3] for s in FOUR}


def _straight(code):
    alts = CASES[code]["match"] if isinstance(CASES[code]["match"], list) else [CASES[code]["match"]]
    return all(set(a["fmt"] if isinstance(a.get("fmt"), list) else [a.get("fmt")]) <= STRAIGHT for a in alts)


def _documents(skill):
    """{level: [case]} as the document places them, straight cases only (M3b adds the other kinds)."""
    out = {lv: [] for lv in LEVELS}
    for code, c in DOC.items():
        for where in c["placed_in"]:
            s, lv = where.split(":")
            if s == skill and lv in out and _straight(code):
                out[lv].append(code)
    return out


def _check(skill, level):
    return SETS[skill]["difficulty"][level]["check"]


@functools.cache
def MATCHES():  # noqa: N802  the rows as `cases.matches` reads them
    return {c: CASES[c]["match"] for c in CASES}


def _matches(check):
    return cases.on_level(check, MATCHES())


def _want(skill, level):
    """Forty, or every question the level holds where its numbers run out first (its row's `min_items`)."""
    return min(40, SETS[skill]["difficulty"][level].get("min_items", 40))


@functools.cache
def _drawn(skill, level, seed=7):
    check = _check(skill, level)
    return draw.level(
        random.Random(seed), check, _matches(check), SETS[skill]["rung_code"], _want(skill, level)
    )


def _item(fmt, a, b, layout):
    return Item("x", "x", "R9", [], "P", fmt, False, "", {"a": a, "b": b, "op": "÷", "layout": layout}, [])


def _measured(a, b):
    return [
        (fmt, tags.derive(_item(fmt, a, b, layout)))
        for fmt, layout in (("bare_sum", "horizontal"), ("column_grid", "column"))
    ]


# ---------------------------------------------------------------------------------------------- the rows


def test_division_is_four_skills_each_level_its_documents_cases():
    """Easy to Hard are the document's straight cases for that level; the tables' and ÷ 10's Advance holds the hardest
    straight cases with the document's own Advance straight cases, as multiplication's does, and the other two have
    none until M3b; every level divides, at the document's grade, on a rung of its own counting on Division, untaught
    until an educator says so."""
    rungs = [SETS[s]["rung_code"] for s in FOUR]
    others = {x["rung_code"] for s, x in SETS.items() if s not in FOUR}
    assert len(set(rungs)) == 4 and not others & set(rungs)
    for skill in FOUR:
        s, doc = SETS[skill], _documents(skill)
        assert RUNGS[s["rung_code"]]["skill_codes"] == ["NUM.OPS.04"], skill
        assert list(s["difficulty"]) == LEVELS_OF[skill], skill
        for lv in ("Easy", "Medium", "Hard"):
            assert sorted(_check(skill, lv)["cases"]) == sorted(doc[lv]), (skill, lv)
        if skill in ADVANCE:
            below = set(doc["Easy"]) | set(doc["Medium"]) if skill == "DIV.FACTS" else set()
            want = sorted(below | set(doc["Hard"]) | set(doc["Advance"]))
            assert sorted(c for c in _check(skill, "Advance")["cases"] if _straight(c)) == want, skill
        assert all(_check(skill, lv)["within"]["operation"] == "DIV" for lv in LEVELS_OF[skill]), skill
        assert [s["level_band"][lv] for lv in LEVELS_OF[skill]] == GRADES[skill], skill
        topic = next(t for t in TOPICS if skill in t["skill_sets"])
        assert topic["taught"] is False, f"{skill} is taught before an educator said so"


def _tz(n):
    return len(str(n)) - len(str(n).rstrip("0")) if n else 0


def _scaled(a, b):
    """A round number whose zeros, taken off, leave a table fact: 200 ÷ 4 is 20 ÷ 4, 800 ÷ 40 is 80 ÷ 4."""
    common = 0
    while a and a % 10 == 0 and b % 10 == 0:
        a, b, common = a // 10, b // 10, common + 1
    ks = range(_tz(a), -1 if common else 0, -1)
    return b <= 12 and any((a // 10**k) % b == 0 and (a // 10**k) // b <= 12 for k in ks)


def _in_reach(a, b):
    """Within the four's numbers: a table read backwards, or one with a remainder under a 1-digit quotient; ÷ 10, 100
    or 1000 of a number at least as big, to 4 digits; a round number by one digit or by a round number whose zeros leave
    a fact; 2 and 3 digits by 1. 4 digits by 1 and 3 by 2 are the document's unplaced cases (D11 to D14), and a round
    number by a 2-digit number not round (240 ÷ 12) is in none of its labels."""
    if b == 0:
        return False
    q, r = divmod(a, b)
    if b <= 12 and (q <= 12 if r == 0 else q <= 9):
        return True
    if b in (10, 100, 1000):
        return b <= a < 10000
    if b < 10 and len(str(a)) in (2, 3):
        return True
    return a % 10 == 0 and a < 10000 and (b < 10 or b % 10 == 0) and _scaled(a, b)


def _every_division():
    """Every straight ÷ a Grade 2 to 4 paper prints, and the ones just past the four's reach."""
    pairs = {(q * d + r, d) for d in range(1, 13) for q in range(13) for r in range(d)}
    pairs |= {(a, d) for a in range(10, 1000) for d in range(2, 10)}
    pairs |= {(a, d) for d in (10, 100, 1000) for a in range(1, 10000, 7)}
    pairs |= {(a, d) for a in range(10, 10000, 10) for d in (*range(2, 10), *range(20, 100, 10))}
    pairs |= {(a, d) for a in range(10, 100, 3) for d in range(10, 100, 3)}
    pairs |= {(a, d) for a in range(1000, 10000, 13) for d in range(2, 10)}
    return sorted(pairs)


def test_a_division_has_exactly_one_home_among_the_four():
    """A child's answer is graphed on one skill (`assess/placing.py` refuses a question two skills hold): a table read
    backwards and a remainder under a 1-digit quotient are the tables'; ÷ 10, 100 and 1000 and a round number whose
    zeros leave a fact are DIV.TENS's; every other division by one digit is worked digit by digit (30 ÷ 2 = 15 is an
    exchange from the tens, not place value; 21 ÷ 2 = 10 r 1 is short division's)."""
    shapes = {s: placing.shape(SETS[s]) for s in FOUR}
    for a, b in _every_division():
        for fmt, t in _measured(a, b):
            homes = [s for s, shape in shapes.items() if taxonomy.matches(shape, fmt, t)]
            assert len(homes) == (1 if _in_reach(a, b) else len(homes)) and len(homes) <= 1, (
                a,
                b,
                fmt,
                homes,
            )
    want = {(42, 6): "DIV.FACTS", (17, 5): "DIV.FACTS", (7, 3): "DIV.FACTS", (144, 12): "DIV.FACTS",
            (84, 12): "DIV.FACTS", (100, 11): "DIV.FACTS", (450, 10): "DIV.TENS", (4567, 100): "DIV.TENS",
            (200, 4): "DIV.TENS", (800, 40): "DIV.TENS", (72, 4): "DIV.2D1D", (30, 2): "DIV.2D1D",
            (21, 2): "DIV.2D1D", (804, 4): "DIV.3D1D", (130, 2): "DIV.3D1D", (210, 2): "DIV.3D1D",
            (156, 4): "DIV.3D1D"}  # fmt: skip
    for (a, b), skill in want.items():
        got = placing.place(
            "bare_sum", tags.derive(_item("bare_sum", a, b, "horizontal")), list(SETS.values()), MATCHES()
        )
        assert got and got[0]["code"] == skill, (a, b, got and got[0]["code"])


def test_every_division_in_the_fours_reach_has_a_level_not_only_a_skill():
    """A question with a skill and no level is retired the day it is read off an old paper: every one in reach has a
    level, in a line and in the division layout. Found missing in the draft and corrected where it was drafted: 7 ÷ 3,
    100 ÷ 11, 210 ÷ 2 and ÷ 100 with a remainder (STATE.md, "M3 — measured before the build")."""
    skills = [SETS[s] for s in FOUR]
    for a, b in _every_division():
        if _in_reach(a, b):
            for fmt, t in _measured(a, b):
                assert placing.place(fmt, t, skills, MATCHES()), (a, b, fmt)


def test_every_division_on_the_schools_papers_has_a_skill_and_a_level():
    """The July quiz and baselines and the Grade 2 diagnostic (`supabase/seed/papers`), filed as `legacy.rung_for` files
    them: on the four's rungs, so a child's July 144 ÷ 12 counts on the tables, not on `EQUALITY.INVERSE`."""
    from engine.w3_read import legacy

    papers = [json.loads(f.read_text()) for f in sorted((SEED / "papers").glob("*.json"))]
    sums = [legacy.parse_expr(it["expr"]) for pp in papers for it in pp["items"] if it.get("expr")]
    divides = [(a, b) for op, a, b in (x for x in sums if x) if op == "÷"]
    assert (144, 12) in divides, divides
    rungs = {SETS[s]["rung_code"] for s in FOUR}
    for a, b in divides:
        assert legacy.rung_for("÷", a, b, (list(SETS.values()), MATCHES())) in rungs, (a, b)
    assert legacy.rung_for("÷", 144, 12, (list(SETS.values()), MATCHES())) == SETS["DIV.FACTS"]["rung_code"]


# ---------------------------------------------------------------------------------------------- the drawing


@pytest.mark.parametrize("skill, level", [(s, lv) for s in FOUR for lv in LEVELS_OF[s]])
def test_every_level_draws_its_own_cases_as_measured(skill, level):
    """Forty questions (or all a small level holds), no two alike, each one of its level's cases as measured; its
    quotient and remainder worked here, a remainder's box only where there is one, every wrong answer it names one of
    its skill's mistakes."""
    drawn = _drawn(skill, level)
    assert len(drawn) == _want(skill, level), (skill, level, len(drawn))
    assert len({it.item_id for _, it in drawn}) == len(drawn)
    matches = _matches(_check(skill, level))
    for code, it in drawn:
        assert taxonomy.matches(matches[code], it.fmt, tags.derive(it)), (skill, level, code, it.spec)
        a, b = it.spec["a"], it.spec["b"]
        q, r = a // b, a - a // b * b
        boxes = {x.rid: x for x in it.responses}
        assert it.spec["op"] == "÷" and boxes["ans"].answer == str(q), (code, a, b)
        assert ("rem" in boxes) == (r > 0) and (r == 0 or boxes["rem"].answer == str(r)), (code, a, b)
        named = {c for x in it.responses for c in x.misconceptions}
        assert named <= set(SETS[skill]["misconception_codes"]), (
            skill,
            a,
            b,
            named - set(SETS[skill]["misconception_codes"]),
        )


def _digits(n):
    return [int(x) for x in str(n)]


def _carried(a, b):
    """Short division from the left, worked here: the remainder each digit passes to the next (a first digit smaller
    than the divisor passes itself, the hundreds joining the tens), the last digit's left out."""
    out, r = [], 0
    for x in _digits(a):
        r = (r * 10 + x) % b
        out.append(r)
    return out[:-1]


def _qzero(a, b):
    q = str(a // b)
    return "MIDDLE" if "0" in q[1:-1] else ("END" if len(q) > 1 and q.endswith("0") else "NONE")


def _uses_a_zero(a, b):
    """The zeros both numbers end in taken off together, the number divided is a fact of the divisor's table to 12 only
    with one of its own zeros left on: 200 ÷ 4 is 20 ÷ 4 = 5, 600 ÷ 50 is 60 ÷ 5 = 12, 2000 ÷ 40 is 20 ÷ 4 and a zero.
    DP06 names no divisor's size; DP04 and DP07 say ÷ 1 digit. With no zero shared, a fact needs one zero off: 60 ÷ 5
    alone is the 5 table's."""
    common = 0
    while a and a % 10 == 0 and b % 10 == 0:
        a, b, common = a // 10, b // 10, common + 1
    z = _tz(a)

    def fact(n):
        return b <= 12 and n % b == 0 and n // b <= 12

    return z >= 1 and not fact(a // 10**z) and any(fact(a // 10**k) for k in range(0 if common else 1, z))


# What each straight case's label says, worked with plain arithmetic: every question it holds must be what it says.
SAYS = {
    "DF01": lambda a, b, col: b == 1 and a <= 12,
    "DF02": lambda a, b, col: a == b > 0,
    "DF03": lambda a, b, col: a == 0 < b,
    **{
        f"DF{n:02}": (lambda t: lambda a, b, col: a % b == 0 and t in (b, a // b))(t)
        for n, t in (
            (4, 2),
            (5, 5),
            (6, 10),
            (7, 3),
            (8, 4),
            (9, 6),
            (10, 7),
            (11, 8),
            (12, 9),
            (13, 11),
            (14, 12),
        )
    },
    "DF15": lambda a, b, col: a % b == 0 and 0 < a // b <= 12 and b <= 12 and not col,  # asked in words
    "DF16": lambda a, b, col: 10 <= b <= 99 and a // b <= 9,
    "DR01": lambda a, b, col: b <= 9 and 0 < a % b and a // b <= 9,
    "DR02": lambda a, b, col: a % b == b - 1 > 0 and a // b <= 9,
    "DR03": lambda a, b, col: 0 < a < b,
    "DR10": lambda a, b, col: b in (10, 100, 1000) and a % b > 0 and a > b,
    "DP01": lambda a, b, col: b == 10 and a % 10 == 0 and a // 10 > 12,
    "DP02": lambda a, b, col: b == 100 and a % 100 == 0,
    "DP03": lambda a, b, col: b == 1000 and a % 1000 == 0,
    "DP04": lambda a, b, col: b < 10 and _tz(a) == 1 and (a // 10) % b == 0 and a // 10 // b <= 12,
    "DP05": lambda a, b, col: a % 10 == 0 and b % 10 == 0 and b not in (10, 100, 1000),
    "DP06": lambda a, b, col: _uses_a_zero(a, b),
    "DP07": lambda a, b, col: b < 10 and _tz(a) >= 2 and (a // 10 ** _tz(a)) % b == 0,
    "D01": lambda a, b, col: len(str(a)) == 2 and b < 10 and not any(_carried(a, b)) and a % b == 0 and col,
    "D02": lambda a, b, col: (
        len(str(a)) == 2 and b < 10 and not any(_carried(a, b)) and a % b == 0 and not col
    ),
    "D03": lambda a, b, col: (
        len(str(a)) == 2 and 2 <= b <= 5 and _carried(a, b) and a % b == 0 and a // 10 >= b
    ),
    "D04": lambda a, b, col: (
        len(str(a)) == 2 and 6 <= b <= 9 and _carried(a, b) and a % b == 0 and a // 10 >= b
    ),
    "DZ07": lambda a, b, col: len(str(a)) == 2 and _qzero(a, b) == "END" and a % b > 0,
    "DR04": lambda a, b, col: len(str(a)) == 2 and not any(_carried(a, b)) and a % b > 0 and a // b >= 10,
    "DR05": lambda a, b, col: len(str(a)) == 2 and any(_carried(a, b)) and a % b > 0 and a // b >= 10,
    "D05": lambda a, b, col: (
        len(str(a)) == 3 and not any(_carried(a, b)) and a % b == 0 and _qzero(a, b) == "NONE"
    ),
    "D06": lambda a, b, col: len(str(a)) == 3 and _carried(a, b)[0] == 0 < _carried(a, b)[1] and a % b == 0,
    "D07": lambda a, b, col: (
        len(str(a)) == 3
        and _carried(a, b)[0] > 0
        and _carried(a, b)[1] == 0
        and a % b == 0
        and _digits(a)[0] >= b
    ),
    "D08": lambda a, b, col: len(str(a)) == 3 and all(_carried(a, b)) and _digits(a)[0] >= b and a % b == 0,
    "D09": lambda a, b, col: len(str(a)) == 3 and _digits(a)[0] < b and _carried(a, b)[1] == 0 and a % b == 0,
    "D10": lambda a, b, col: len(str(a)) == 3 and _digits(a)[0] < b and _carried(a, b)[1] > 0 and a % b == 0,
    "DZ01": lambda a, b, col: len(str(a)) == 3 and str(a)[1] == "0" and _qzero(a, b) == "MIDDLE",
    "DZ02": lambda a, b, col: len(str(a)) == 3 and _qzero(a, b) == "END" and a % b == 0,
    "DZ03": lambda a, b, col: len(str(a)) == 3 and _qzero(a, b) == "MIDDLE" and str(a)[1] != "0",
    "DZ04": lambda a, b, col: len(str(a)) == 3 and str(a)[1] == "0" and "0" not in str(a // b),
    "DR06": lambda a, b, col: len(str(a)) == 3 and b < 10 and a % b > 0,
    "DR07": lambda a, b, col: _qzero(a, b) == "MIDDLE" and a % b > 0,
    "DR08": lambda a, b, col: len(str(a)) == 3 and _digits(a)[0] < b and a % b > 0,
}


def test_every_question_a_level_draws_is_what_its_cases_label_says():
    """Read against plain arithmetic written here, so a tag measured wrong cannot make its own case look right."""
    seen = set()
    for skill in FOUR:
        for level in LEVELS_OF[skill]:
            for code, it in _drawn(skill, level):
                a, b, col = it.spec["a"], it.spec["b"], it.fmt == "column_grid"
                assert SAYS[code](a, b, col), (
                    skill,
                    level,
                    code,
                    f"{a} ÷ {b}",
                    "columns" if col else "a line",
                )
                # "How many 6s make 42?": the numbers in words, never the sign that gives the operation away
                worded = str(a) in it.stem and str(b) in it.stem and "÷" not in it.stem
                assert worded == (code == "DF15"), (code, it.stem)
                seen.add(code)
    assert seen == {c for s in FOUR for lv in LEVELS_OF[s] for c in _check(s, lv)["cases"]}, (
        "a case drew nothing"
    )


def test_a_case_that_names_its_layout_is_printed_that_way():
    """The tables and ÷ 10, 100 and 1000 in a line; D01 in the division layout and D02 in a line, as the document names
    them; every other division in the division layout and in a line, in fair shares."""
    printed = {}
    for skill in FOUR:
        for level in LEVELS_OF[skill]:
            for code, it in _drawn(skill, level):
                printed.setdefault((skill, code), set()).add(it.fmt)
    for (skill, code), fmts in printed.items():
        if skill in ("DIV.FACTS", "DIV.TENS"):
            assert fmts == {"bare_sum"}, (skill, code, fmts)
    assert printed[("DIV.2D1D", "D01")] == {"column_grid"} and printed[("DIV.2D1D", "D02")] == {"bare_sum"}
    for code in ("D03", "DR05", "D05", "D08", "DR06"):
        skill = "DIV.2D1D" if code in ("D03", "DR05") else "DIV.3D1D"
        assert printed[(skill, code)] == {"bare_sum", "column_grid"}, (code, printed[(skill, code)])


# ---------------------------------------------------------------------------------------------- the answer


def test_a_remainder_is_an_answer_of_its_own():
    """85 ÷ 4 asks two answers, 21 and then 1 after "r", each a box of its own with its own key; 84 ÷ 4 asks one. In a
    line it reads "85 ÷ 4 = □ r □" (a remainder's box shows only where there is one: ADR 0056)."""
    it = verify.division(85, 4, "R44")
    assert [(r.rid, r.answer) for r in it.responses] == [("ans", "21"), ("rem", "1")]
    assert [(r.rid, r.answer) for r in verify.division(84, 4, "R44").responses] == [("ans", "21")]
    page = render.render_item(Sheet("CS000000", "G3", "Hard", 1, "W1", [it]), it, 1)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
    assert "85 ÷ 4 =" in text and " r " in text, text
    # the quotient's boxes, then "r", then the remainder's: "85 ÷ 4 = □□ r □"
    assert page.index('data-r="ans"') < page.index(">r<") < page.index('data-r="rem"'), page


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def test_each_box_of_a_division_is_marked_against_its_own_key():
    """Each box marked by itself, as every several-answer question is (M0a): its own key is right, and each wrong value
    predicted for it names its mistake — the quotient's and the remainder's alike."""
    for a, b in ((85, 4), (17, 5), (813, 4), (804, 4), (47, 6)):
        it = verify.division(a, b, "R44")
        for r in it.responses:
            stored = {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}
            assert marking.mark(it.spec, stored, _wrote(r.answer))[0] == "correct", (a, b, r.rid)
            for code, wrong in r.misconceptions.items():
                status, codes, _ = marking.mark(it.spec, stored, _wrote(str(wrong)))
                assert status == "wrong" and code in codes, (a, b, r.rid, code, wrong)


# ---------------------------------------------------------------------------------------------- the whole loop


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_every_level_of_the_four_fills_its_worksheets(conn):
    """Each of the four's levels holds questions enough for its worksheets, and the library makes at least ten of
    each."""
    from engine.w2_print import library

    library.build(conn)
    for skill in FOUR:
        for level in LEVELS_OF[skill]:
            n = conn.execute(
                "select count(*) as n from sheet_template where source = 'library' and retired_at is null"
                " and skill_set_code = %s and difficulty = %s",
                (skill, level),
            ).fetchone()["n"]
            assert n >= library.MIN_PER_LEVEL, (skill, level, n)
