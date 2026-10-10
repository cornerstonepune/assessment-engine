"""Multiplication as five skills, each level its document's own cases, drawn by the case drawer that makes addition and
subtraction (goals/md2a-straight-multiplication.yaml).

The levels are held to the drafted document (docs/design/multiplication-division-cases.json, each case's
`placed_in`), the drawing to the cases as measured (`assess/tags.py`), and the answers to arithmetic done here."""

import functools
import json
import os
import pathlib
import random

import pytest

from engine.assess import draw, placing, tags, taxonomy
from engine.assess import draw_case as K
from engine.core import db
from engine.w1_bank import cases

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase/seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
RUNGS = {r["code"]: r for r in json.loads((SEED / "rungs.json").read_text())["rungs"]}
TOPICS = json.loads((SEED / "topics.json").read_text())["topics"]
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
FIVE = ["MUL.FACTS", "MUL.TENS", "MUL.2D1D", "MUL.3D1D", "MUL.2D2D"]
LEVELS = ["Easy", "Medium", "Hard", "Advance"]
# a straight calculation, in a line, in columns or in a written method (ADR 0055)
STRAIGHT = set(draw.STRAIGHT)
# The document's grades (assumption A6), Easy · Medium · Hard · Advance
GRADES = {
    "MUL.FACTS": ["G2", "G2", "G2", "G3"],  # Grade 1 is what its educator taught (2026-10-06)
    "MUL.TENS": ["G3", "G3", "G4", "G4"],
    "MUL.2D1D": ["G2", "G2", "G3", "G3"],
    "MUL.3D1D": ["G4", "G4", "G4", "G4"],
    "MUL.2D2D": ["G4", "G4", "G4", "G4"],
}


def _straight(code):
    alts = CASES[code]["match"] if isinstance(CASES[code]["match"], list) else [CASES[code]["match"]]
    return all(set(a["fmt"] if isinstance(a.get("fmt"), list) else [a.get("fmt")]) <= STRAIGHT for a in alts)


def _documents(skill):
    """{level: [case]} as the document places them, straight cases only (M2b adds the other kinds)."""
    out = {lv: [] for lv in LEVELS}
    for code, c in DOC.items():
        for where in c["placed_in"]:
            s, lv = where.split(":")
            if s == skill and lv in out and _straight(code):
                out[lv].append(code)
    return out


def _check(skill, level):
    """A level's rule as these tests read it, its straight cases only: the kinds an Advance holds besides (a missing
    number, a fact family, a story) are `test_facts_advance.py`'s and `test_mul_advance.py`'s."""
    check = SETS[skill]["difficulty"][level]["check"]
    return {**check, "cases": [c for c in check["cases"] if _straight(c)]}


def _matches(check):
    """The level's cases and the written methods it prints them in (ADR 0055), on its own numbers, as the bank reads
    them (`cases.on_level`)."""
    return cases.on_level(check, {c: row["match"] for c, row in CASES.items()})


def _ans(it):
    """The question's own answer: a written method's last box, after its steps."""
    return next(r for r in it.responses if r.rid == "ans")


def _want(skill, level):
    """Forty, or every question the level holds where its numbers run out first (its row's `min_items`)."""
    return min(40, SETS[skill]["difficulty"][level].get("min_items", 40))


@functools.cache
def _drawn(skill, level, seed=7):
    check = _check(skill, level)
    return draw.level(
        random.Random(seed), check, _matches(check), SETS[skill]["rung_code"], _want(skill, level)
    )


# ---------------------------------------------------------------------------------------------- the rows


# The two whose Advance the document gives straight questions no lower level holds: the 11 and 12 tables, and a round
# number with no table fact under its zeros; their kinds came with M3b1 (`tests/test_facts_advance.py`). The other
# three's Advance is Hard's straight cases with kinds M2b makes (missing digits, finding the mistake, estimates,
# stories: `tests/test_mul_advance.py`); the straight questions those levels draw are what these tests read.
ADVANCE = ["MUL.FACTS", "MUL.TENS"]


def _levels(skill):
    return [lv for lv in LEVELS if lv != "Advance" or skill in ADVANCE]


def test_multiplication_is_five_skills_each_level_its_documents_cases():
    """Easy to Hard are the document's straight cases for that level; Advance mixes the hardest straight cases (Hard's)
    with the document's own Advance cases, as addition's Advance does (ADD.2D1D: A14 to A16)."""
    rungs = [SETS[s]["rung_code"] for s in FIVE]
    others = {x["rung_code"] for s, x in SETS.items() if s not in FIVE}
    assert len(set(rungs)) == 5 and not others & set(rungs)
    for skill in FIVE:
        s, doc, levels = SETS[skill], _documents(skill), _levels(skill)
        assert RUNGS[s["rung_code"]]["skill_codes"] == ["NUM.OPS.03"], skill
        assert list(s["difficulty"]) == LEVELS, skill
        for lv in ("Easy", "Medium", "Hard"):
            assert sorted(_check(skill, lv)["cases"]) == sorted(doc[lv]), (skill, lv)
        # the tables' Advance holds every table, so a fact that needs the 11 or 12 tables has a level (A4)
        below = set(doc["Easy"]) | set(doc["Medium"]) if skill == "MUL.FACTS" else set()
        want = sorted(below | set(doc["Hard"]) | set(doc["Advance"]))
        assert sorted(c for c in _check(skill, "Advance")["cases"] if _straight(c)) == want, skill
        shapes = {json.dumps(_check(skill, lv)["within"], sort_keys=True) for lv in levels}
        assert len(shapes) == (2 if skill == "MUL.FACTS" else 1), skill  # the tables: A4 below Advance
        assert all(_check(skill, lv)["within"]["operation"] == "MUL" for lv in levels), skill
        assert [s["level_band"][lv] for lv in levels] == GRADES[skill][: len(levels)], skill
        topic = next(t for t in TOPICS if skill in t["skill_sets"])
        assert topic["taught"] is False, f"{skill} is taught before an educator said so"


def test_every_case_the_document_places_in_the_five_is_a_level_of_one_of_them():
    """Every straight case the document places in the five is in a level of its skill, and inside its skill's numbers
    (a case the skill's shape contradicts raises)."""
    for skill in FIVE:
        for lv, codes in _documents(skill).items():
            if lv not in _levels(skill):
                continue  # an Advance M2b makes
            for c in codes:
                assert any(c in _check(skill, x)["cases"] for x in _levels(skill)), (skill, lv, c)
                for x in _levels(skill):
                    taxonomy.within(CASES[c]["match"], _check(skill, x)["within"])


def _every_times_question():
    """Every straight × a Grade 1 to 4 paper prints: the tables to 12, up to 3 digits by 1 (either first), 2 digits by
    2, and round numbers by anything up to 4 digits, in a line and in columns."""
    pairs = {(a, b) for a in range(13) for b in range(13)}
    pairs |= {
        p for a in (*range(10, 100), *range(100, 1000, 3)) for b in range(1, 10) for p in ((a, b), (b, a))
    }
    pairs |= {(a, b) for a in range(10, 100) for b in range(10, 100)}
    rounds = [x * 10**z for x in range(1, 100) for z in (1, 2, 3) if x * 10**z < 10000]
    pairs |= {p for x in rounds for b in (*range(2, 100, 3), 10, 100, 1000) for p in ((x, b), (b, x))}
    for a, b in sorted(pairs):
        for layout in ("horizontal", "column"):
            fmt = "column_grid" if layout == "column" else "bare_sum"
            yield fmt, a, b, tags.derive(_item(fmt, a, b, layout))


def _item(fmt, a, b, layout):
    from engine.assess.items import Item

    return Item("x", "x", "R9", [], "P", fmt, False, "", {"a": a, "b": b, "op": "×", "layout": layout}, [])


def test_a_multiplication_has_exactly_one_home_among_the_five():
    """A child's answer is graphed on one skill (`assess/placing.py` refuses a question two skills hold). Every
    round-number × that is not a table fact is MUL.TENS's: 230 × 4 and 23 × 40 with 23 × 30 (TP10)."""
    shapes = {s: placing.shape(SETS[s]) for s in FIVE}
    for fmt, a, b, t in _every_times_question():
        homes = [s for s, shape in shapes.items() if taxonomy.matches(shape, fmt, t)]
        if 0 in (a, b) and max(a, b) > 12:
            continue  # 0 × 345 is no column work and no table fact: not a question a paper prints
        assert len(homes) == 1, (a, b, fmt, homes)
    want = {(7, 8): "MUL.FACTS", (12, 5): "MUL.FACTS", (10, 4): "MUL.FACTS", (45, 10): "MUL.TENS",
            (30, 4): "MUL.TENS", (230, 4): "MUL.TENS", (23, 40): "MUL.TENS", (3, 21): "MUL.2D1D",
            (13, 4): "MUL.2D1D", (6, 125): "MUL.3D1D", (506, 7): "MUL.3D1D", (68, 17): "MUL.2D2D"}  # fmt: skip
    for (a, b), skill in want.items():
        t = tags.derive(_item("bare_sum", a, b, "horizontal"))
        assert placing.place("bare_sum", t, [SETS[s] for s in FIVE], CASES_MATCHES())[0]["code"] == skill, (
            a,
            b,
        )


def test_every_question_the_old_multiplication_set_made_has_a_skill_and_a_level():
    """`MUL.1D` (2 × 1, 3 × 1 and 2 × 2 digits, the longer number first) is re-homed on the five by `engine bank rehome`,
    which stops and moves nothing if one question has no place; its stories, whose shape no level of the five holds
    yet, are kept retired. As addition's old ladder was re-homed (ADR 0034)."""
    skills = [SETS[s] for s in FIVE]
    pairs = [(a, b) for a in range(10, 100) for b in range(2, 10)]
    pairs += [(a, b) for a in range(100, 1000, 7) for b in range(2, 10)]
    pairs += [(a, b) for a in range(10, 100, 3) for b in range(10, 100, 3)]
    for a, b in pairs:
        for fmt, layout in (("bare_sum", "horizontal"), ("column_grid", "column")):
            t = tags.derive(_item(fmt, a, b, layout))
            assert placing.place(fmt, t, skills, CASES_MATCHES()), (a, b, fmt)


def _in_reach(a, b):
    """Within the five's numbers: by 10, 100 or 1000 to a 5-digit answer, or 3 digits by 1, 2 by 2 and the tables, round
    or not. 3 digits by 2 and 4 by 1 are the document's unplaced cases (T15, T16, T23), round or not."""
    if a in (10, 100, 1000) or b in (10, 100, 1000):
        return a * b < 100000
    return sorted(len(str(n)) for n in (a, b)) in ([1, 1], [1, 2], [1, 3], [2, 2])


def test_every_question_in_the_fives_reach_has_a_level_not_only_a_skill():
    """A question with a skill and no level is retired the day it is re-homed or read off an old paper: every one in
    reach has a level. Found missing, and added as cases: 401 × 3 (TZ09), 30 × 100 (TP11), and 11 × 20, which TP10's own
    words held and its match did not (second reader, 2026-10-09)."""
    skills = [SETS[s] for s in FIVE]
    rounds = [x * 10**z for x in range(1, 100) for z in (1, 2, 3) if x * 10**z < 10000]
    pairs = [(a, b) for a in range(13) for b in range(13)]
    pairs += [
        p for a in (*range(10, 100), *range(100, 1000, 7)) for b in range(2, 10) for p in ((a, b), (b, a))
    ]
    pairs += [(a, b) for a in range(10, 100, 3) for b in range(10, 100, 2)]
    pairs += [p for x in rounds for b in (*range(2, 100, 3), 10, 100, 1000) for p in ((x, b), (b, x))]
    for a, b in pairs:
        if not _in_reach(a, b) or (0 in (a, b) and max(a, b) > 12):
            continue
        for fmt, layout in (("bare_sum", "horizontal"), ("column_grid", "column")):
            assert placing.place(fmt, tags.derive(_item(fmt, a, b, layout)), skills, CASES_MATCHES()), (
                a,
                b,
                fmt,
            )


def test_every_times_question_on_the_schools_papers_has_a_skill_and_a_level():
    """The July quiz and baselines and the Grade 2 diagnostic (`supabase/seed/papers`), filed as `legacy.rung_for` files
    them: on the five's rungs, so a child's July answers count on the skill they practised, not the old `M1`."""
    from engine.w3_read import legacy

    papers = [json.loads(f.read_text()) for f in sorted((SEED / "papers").glob("*.json"))]
    sums = [legacy.parse_expr(it["expr"]) for pp in papers for it in pp["items"] if it.get("expr")]
    times = [(a, b) for op, a, b in (x for x in sums if x) if op == "×"]
    assert len(times) >= 20, times
    rungs = {SETS[s]["rung_code"] for s in FIVE}
    where = ([SETS[s] for s in FIVE], CASES_MATCHES())
    for a, b in times:
        assert legacy.rung_for("×", a, b, where) in rungs, (a, b)


@functools.cache
def CASES_MATCHES():  # noqa: N802  the rows as `cases.matches` reads them
    return {c: CASES[c]["match"] for c in CASES}


# ---------------------------------------------------------------------------------------------- the drawing


@pytest.mark.parametrize("skill, level", [(s, lv) for s in FIVE for lv in _levels(s)])
def test_every_level_draws_its_own_cases_as_measured(skill, level):
    """Forty questions (or all a small level holds), no two alike, each one of its level's cases as measured, every
    case drawn, and each answer the product worked out here: the drawer is told the case, the check reads only the
    question."""
    drawn, check, want = _drawn(skill, level), _check(skill, level), _want(skill, level)
    assert len(drawn) == want, f"{skill} {level}: {len(drawn)} of {want}"
    assert len({it.item_id for _, it in drawn}) == want
    assert {code for code, _ in drawn} == set(check["cases"])
    matches = _matches(check)
    for code, it in drawn:
        t = tags.derive(it)
        assert taxonomy.matches(matches[code], it.fmt, t), (skill, level, code, it.spec)
        a, b = it.spec["a"], it.spec["b"]
        assert it.spec["op"] == "×" and _ans(it).answer == str(a * b)
        named = {c for r in it.responses for c in r.misconceptions}
        assert named <= set(SETS[skill]["misconception_codes"]), (skill, it.spec)


WHOLE = [(s, lv) for s in FIVE for lv in LEVELS if "min_items" in SETS[s]["difficulty"].get(lv, {})]


@pytest.mark.parametrize("skill, level", WHOLE)
def test_a_level_whose_target_is_all_it_holds_is_filled_to_the_last_question(skill, level):
    """`min_items` is everything a level holds once the levels beside it hold theirs, so its fill must find the last
    question too. MUL.2D1D Easy's 3 × 21 turns up once in about 3,000 random draws, and CI's bank stopped at 66 of 69
    (2026-10-09): a case that runs dry is now listed whole (`draw._rest`), so three questions held back are found
    whatever the random draws do."""
    check = _check(skill, level)
    matches = _matches(check)
    methods = [matches[m] for m in check.get("methods", [])]
    whole = {
        it.item_id
        for c in check["cases"]
        for way in K.ways(matches[c], methods)  # each case in every method its level prints it in (ADR 0055)
        for it in draw._rest(way, check, "R9", 10**6, set())
    }
    assert len(whole) >= SETS[skill]["difficulty"][level]["min_items"], (skill, level, len(whole))
    held_back = sorted(whole)[:3]
    seen = whole - set(held_back)
    got = draw.level(
        random.Random(0),
        check,
        matches,
        "R9",
        3,
        seen=seen,
        quotas=dict.fromkeys(check["cases"], 0),
        tries_per_item=20,
    )
    assert sorted(it.item_id for _, it in got) == held_back


# ---------------------------------------------------------------------------------------------- the labels, by hand
# Each case's words as plain arithmetic written here, never the code under test (`assess/md_tags.py`): what the drawer
# makes is held to what the label says, so a case whose match says less than its label is caught by what it draws.


def _w(a, b):
    return (b, a) if len(str(a)) < len(str(b)) else (a, b)


def _carries(a, b):
    """The carry out of each column of the longer number times the 1-digit one, from the ones, the last left out."""
    top, d = _w(a, b)
    out, carry = [], 0
    for x in reversed(str(top)):
        carry = (int(x) * d + carry) // 10
        out.append(carry)
    return out[:-1]


def _knock_on(a, b):
    top, d = _w(a, b)
    carry = 0
    for x in reversed(str(top)):
        hit = int(x) * d < 10 <= int(x) * d + carry
        carry = (int(x) * d + carry) // 10
        if hit:
            return True
    return False


def _rows(a, b):
    """A 2 × 2 multiplication's two rows (ones row, tens row), whether each carries, and how many carries adding them."""
    ones, tens = a * (b % 10), a * (b // 10) * 10
    row_carries = [
        any(_carries(a, d)) for d in (b % 10, b // 10)
    ]  # a carry into a next column, not a longer row
    adds, carry = 0, 0
    for i in range(6):
        carry = ((ones // 10**i) % 10 + (tens // 10**i) % 10 + carry) // 10
        adds += carry > 0
    return row_carries, adds


def _digits(a, b):
    return sorted(len(str(x)) for x in (a, b))


def _fact(a, b):
    return a <= 12 and b <= 12


def _tz(n):
    return len(str(n)) - len(str(n).rstrip("0"))


def _stripped(n):
    return int(str(n).rstrip("0") or "0")


def _round_answer(q):
    return q >= 10 and str(q).rstrip("0") == str(q)[0]


GROUP = {0: 0, 1: 0, 2: 1, 5: 1, 10: 1, 3: 2, 4: 2, 6: 3, 7: 3, 8: 3, 9: 3, 11: 4, 12: 4}
ONE_BY = lambda a, b: _digits(a, b) == [1, 2]  # noqa: E731
THREE_BY = lambda a, b: _digits(a, b) == [1, 3]  # noqa: E731
TWO_BY_TWO = lambda a, b: _digits(a, b) == [2, 2]  # noqa: E731
LABEL = {
    "TF01": lambda a, b, col: _fact(a, b) and 0 in (a, b),
    "TF02": lambda a, b, col: _fact(a, b) and 1 in (a, b),
    **{f"TF{n:02d}": (lambda t: lambda a, b, col: _fact(a, b) and a == t)(t)
       for n, t in ((3, 2), (4, 5), (5, 10), (6, 3), (7, 4), (8, 6), (9, 7), (10, 8), (11, 9), (13, 11), (14, 12))},
    "TF12": lambda a, b, col: _fact(a, b) and a == b,
    "TF15": lambda a, b, col: _fact(a, b) and b >= 2 and GROUP[b] < GROUP[a],
    "TF16": lambda a, b, col: _fact(a, b) and col,
    "TP01": lambda a, b, col: 10 in (a, b) and "0" not in str(b if a == 10 else a),
    "TP02": lambda a, b, col: 100 in (a, b) and "0" not in str(b if a == 100 else a) and max(a, b) < 1000,
    "TP03": lambda a, b, col: 1000 in (a, b) and min(a, b) < 100,
    "TP04": lambda a, b, col: 10 in (a, b) and (b if a == 10 else a) % 10 == 0,
    "TP05": lambda a, b, col: 100 in (a, b) and "0" in str(b if a == 100 else a).rstrip("0") and max(a, b) < 1000,
    "TP11": lambda a, b, col: 100 in (a, b) and (b if a == 100 else a) % 10 == 0 and max(a, b) < 1000,
    "TP06": lambda a, b, col: min(a, b) < 10 and _tz(max(a, b)) == 1 and _fact(_stripped(max(a, b)), min(a, b))
    and (_stripped(max(a, b)) * min(a, b)) % 10 != 0,
    "TP07": lambda a, b, col: a % 10 == 0 and b % 10 == 0 and TWO_BY_TWO(a, b),
    "TP08": lambda a, b, col: min(a, b) < 10 and _tz(max(a, b)) >= 2 and _fact(_stripped(max(a, b)), min(a, b)),
    "TP09": lambda a, b, col: min(a, b) < 10 and _tz(max(a, b)) == 1 and (_stripped(max(a, b)) * min(a, b)) % 10 == 0,
    "TP10": lambda a, b, col: TWO_BY_TWO(a, b) and (a % 10 == 0) != (b % 10 == 0),
    "TZ01": lambda a, b, col: THREE_BY(a, b) and max(a, b) % 10 == 0,
    "TZ07": lambda a, b, col: col and TWO_BY_TWO(a, b) and b % 10 == 0,
    "TZ08": lambda a, b, col: a % 10 == 0 and b % 10 == 0 and _digits(a, b) == [2, 3],
    "T01": lambda a, b, col: ONE_BY(a, b) and not any(_carries(a, b)) and a * b < 100,
    "T03": lambda a, b, col: a < 10 <= b < 100 and not any(_carries(a, b)) and a * b < 100 and not col,
    "T04": lambda a, b, col: ONE_BY(a, b) and _carries(a, b) == [1] and a * b < 100,
    "T05": lambda a, b, col: ONE_BY(a, b) and _carries(a, b)[0] > 1 and a * b < 100,
    "T06": lambda a, b, col: ONE_BY(a, b) and not any(_carries(a, b)) and a * b >= 100,
    "T07": lambda a, b, col: ONE_BY(a, b) and _carries(a, b) == [1] and a * b >= 100 and not _knock_on(a, b),
    "T08": lambda a, b, col: ONE_BY(a, b) and _knock_on(a, b) and "0" in str(a * b)[1:-1],
    "T09": lambda a, b, col: ONE_BY(a, b) and _carries(a, b)[0] > 0 and (a * b) % 10 == 0,
    "T10": lambda a, b, col: ONE_BY(a, b) and max(_carries(a, b)) == 8,
    "TC09": lambda a, b, col: ONE_BY(a, b) and max(_carries(a, b)) > 1 and a * b >= 100,
    "TZ05": lambda a, b, col: ONE_BY(a, b) and _round_answer(a * b),
    "T11": lambda a, b, col: THREE_BY(a, b) and not any(_carries(a, b)) and a * b < 1000,
    "T12": lambda a, b, col: THREE_BY(a, b) and any(_carries(a, b)),
    **{code: (lambda ones, tens, grows: lambda a, b, col: THREE_BY(a, b) and "0" not in str(max(a, b))
              and (bool(_carries(a, b)[0]), bool(_carries(a, b)[1])) == (ones, tens) and (a * b >= 1000) == grows)(*k)
       for code, k in (("TC01", (False, False, False)), ("TC02", (False, False, True)), ("TC03", (False, True, False)),
                       ("TC04", (False, True, True)), ("TC05", (True, False, False)), ("TC06", (True, False, True)),
                       ("TC07", (True, True, False)), ("TC08", (True, True, True)))},
    "TC10": lambda a, b, col: THREE_BY(a, b) and _knock_on(a, b),
    "TC11": lambda a, b, col: THREE_BY(a, b) and all(_carries(a, b)) and "0" in str(a * b)[1:-1],
    "TZ02": lambda a, b, col: THREE_BY(a, b) and "0" in str(max(a, b))[1:-1] and a * b < 1000 and 0 not in (a, b)
    and not any(c for x, c in zip(str(max(a, b))[::-1][1:], _carries(a, b)) if x == "0"),
    "TZ03": lambda a, b, col: THREE_BY(a, b) and any(c for x, c in zip(str(max(a, b))[::-1][1:], _carries(a, b)) if x == "0"),
    "TZ09": lambda a, b, col: THREE_BY(a, b) and "0" in str(max(a, b))[1:-1] and a * b >= 1000 and 0 not in (a, b)
    and not any(c for x, c in zip(str(max(a, b))[::-1][1:], _carries(a, b)) if x == "0"),
    "TZ06": lambda a, b, col: THREE_BY(a, b) and _round_answer(a * b),
    "T17": lambda a, b, col: TWO_BY_TWO(a, b) and _rows(a, b) == ([False, False], 0) and a * b < 1000,
    "T18": lambda a, b, col: TWO_BY_TWO(a, b) and sum(_rows(a, b)[0]) == 1 and _rows(a, b)[1] == 0 and a * b < 1000,
    "T19": lambda a, b, col: TWO_BY_TWO(a, b) and _rows(a, b) == ([True, True], 0) and a * b < 1000,
    "T20": lambda a, b, col: TWO_BY_TWO(a, b) and all(_rows(a, b)[0]) and _rows(a, b)[1] > 0 and a * b >= 1000,
    "T21": lambda a, b, col: TWO_BY_TWO(a, b) and _rows(a, b)[1] == 0 and a * b >= 1000,
    "T27": lambda a, b, col: TWO_BY_TWO(a, b) and _rows(a, b)[1] > 0 and a * b < 1000,
    "T28": lambda a, b, col: TWO_BY_TWO(a, b) and not all(_rows(a, b)[0]) and _rows(a, b)[1] > 0 and a * b >= 1000,
}  # fmt: skip


def test_every_question_a_level_draws_is_what_its_cases_label_says():
    """The labels as arithmetic done here: 6700 × 1000 is no "× 1000 of a number to 2 digits", and a level that drew it
    would fail here though its match held it (second reader, 2026-10-09)."""
    seen = set()
    for skill in FIVE:
        for level in _levels(skill):
            for code, it in _drawn(skill, level):
                a, b, col = it.spec["a"], it.spec["b"], it.fmt == "column_grid"
                assert LABEL[code](a, b, col), f"{skill} {level} {code} ({CASES[code]['label']}): {a} × {b}"
                seen.add(code)
    assert seen == set(LABEL), sorted(set(LABEL) ^ seen)


# the kind each written method is printed by, written here: a line as a sum; columns and long multiplication in columns
PRINTED_BY = {
    "LINE": "bare_sum",
    "COLUMNS": "column_grid",
    "LONG_MULTIPLICATION": "column_grid",
    "PARTITIONING": "partitioning",
    "GRID": "grid_method",
    "EXPANDED": "expanded_columns",
    "LATTICE": "lattice",
}


def test_a_case_that_names_its_method_is_printed_that_way():
    """The tables and the round numbers, whose levels list no written method, in a line, and in columns only where the
    case is about columns (TF16, TZ07). The levels that list methods print each calculation in every one of them
    (ADR 0055): the 1-digit number written first never in columns, where the longer number goes on top."""
    printed = {}
    for skill in FIVE:
        for level in _levels(skill):
            for code, it in _drawn(skill, level):
                printed.setdefault(code, set()).add(it.fmt)
    assert printed["TF16"] == {"column_grid"} and printed["TZ07"] == {"column_grid"}
    for code in ("TP01", "TP04", "TP06", "TP10", "TZ01", "TZ08"):  # zeros are placed in a line
        assert printed[code] == {"bare_sum"}, code
    for code in ("TF01", "TF02", "TF03", "TF04", "TF05", "TF06", "TF07", "TF15"):
        assert printed[code] == {"bare_sum"}, code
    # a case on each skill's straight levels, printed by the kind of every method its levels list
    for skill, code in {"MUL.2D1D": "T01", "MUL.3D1D": "TC07", "MUL.2D2D": "T17"}.items():
        kinds = {PRINTED_BY[CASES[m]["match"]["method"]] for m in _check(skill, "Easy")["methods"]}
        assert printed[code] == kinds, (skill, code, printed[code])
    # the 1-digit number first: in a line, partitioned or in a grid, never in columns
    assert printed["T03"] == {"bare_sum", "partitioning", "grid_method"}


def test_the_eleven_and_twelve_tables_appear_only_at_advance():
    """Assumption A4: the tables run from 0 to 12, and ×11 and ×12 appear only at Advance. Held by what each level
    is, not only by what it draws: a question that arrives another way (an old paper's 12 × 7) is placed at Advance."""
    for level in ("Easy", "Medium", "Hard"):
        for _, it in _drawn("MUL.FACTS", level):
            a, b = it.spec["a"], it.spec["b"]
            assert max(a, b) <= 10 or min(a, b) <= 1, (
                level,
                it.spec,
            )  # 12 × 0 and 11 × 1 are 0's and 1's facts
    top = {max(it.spec["a"], it.spec["b"]) for _, it in _drawn("MUL.FACTS", "Advance")}
    assert {11, 12} <= top
    facts = [SETS["MUL.FACTS"]]
    for a, b in ((12, 7), (3, 12), (11, 11), (7, 8), (12, 0)):
        t = tags.derive(_item("bare_sum", a, b, "horizontal"))
        want = "Advance" if min(a, b) >= 2 and max(a, b) >= 11 else ("Hard" if (a, b) == (7, 8) else "Medium")
        assert placing.place("bare_sum", t, facts, CASES_MATCHES())[1] == want, (a, b)


# ---------------------------------------------------------------------------------------------- the whole loop


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_every_level_of_the_five_fills_its_worksheets(conn):
    """Each level holds questions enough for its worksheets, and the library makes at least ten of each."""
    from engine.w2_print import library

    library.build(conn)
    for skill in FIVE:
        for level in _levels(skill):
            n = conn.execute(
                "select count(*) as n from sheet_template where source = 'library' and retired_at is null"
                " and skill_set_code = %s and difficulty = %s",
                (skill, level),
            ).fetchone()["n"]
            assert n >= library.MIN_PER_LEVEL, (skill, level, n)
