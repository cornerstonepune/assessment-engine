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
from engine.core import db

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
STRAIGHT = {"bare_sum", "column_grid"}
# The document's grades (assumption A6), Easy · Medium · Hard · Advance
GRADES = {
    "MUL.FACTS": ["G1", "G1", "G2", "G3"],
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
    return SETS[skill]["difficulty"][level]["check"]


def _matches(check):
    return {c: taxonomy.within(CASES[c]["match"], check["within"]) for c in check["cases"]}


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


def _levels(skill):
    """Easy to Hard, and Advance where the document places straight cases at it. 2-digit × 1-digit's and 2 × 2's
    Advance are all kinds M2b makes (missing numbers, stories, finding the mistake): an Advance of Hard's cases alone
    would be Hard again, which `engine load` names as two levels holding one region."""
    return [lv for lv in LEVELS if lv != "Advance" or _documents(skill)["Advance"]]


def test_multiplication_is_five_skills_each_level_its_documents_cases():
    """Easy to Hard are the document's straight cases for that level; Advance mixes the hardest straight cases (Hard's)
    with the document's own straight Advance cases, as addition's Advance does (ADD.2D1D: A14 to A16)."""
    rungs = [SETS[s]["rung_code"] for s in FIVE]
    others = {x["rung_code"] for s, x in SETS.items() if s not in FIVE}
    assert len(set(rungs)) == 5 and not others & set(rungs)
    assert [s for s in FIVE if "Advance" in SETS[s]["difficulty"]] == ["MUL.FACTS", "MUL.TENS", "MUL.3D1D"]
    for skill in FIVE:
        s, doc, levels = SETS[skill], _documents(skill), _levels(skill)
        assert RUNGS[s["rung_code"]]["skill_codes"] == ["NUM.OPS.03"], skill
        assert list(s["difficulty"]) == levels, skill
        for lv in ("Easy", "Medium", "Hard"):
            assert sorted(_check(skill, lv)["cases"]) == sorted(doc[lv]), (skill, lv)
        if "Advance" in levels:
            want = sorted(set(doc["Hard"]) | set(doc["Advance"]))
            assert sorted(_check(skill, "Advance")["cases"]) == want, skill
        shapes = {json.dumps(_check(skill, lv)["within"], sort_keys=True) for lv in levels}
        assert len(shapes) == 1 and _check(skill, "Easy")["within"]["operation"] == "MUL", skill
        assert [s["level_band"][lv] for lv in levels] == GRADES[skill][: len(levels)], skill
        topic = next(t for t in TOPICS if skill in t["skill_sets"])
        assert topic["taught"] is False, f"{skill} is taught before an educator said so"


def test_every_case_the_document_places_in_the_five_is_a_level_of_one_of_them():
    """Every straight case the document places in the five is in a level of its skill, and inside its skill's numbers
    (a case the skill's shape contradicts raises)."""
    for skill in FIVE:
        for lv, codes in _documents(skill).items():
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
    shapes = {s: _check(s, "Easy")["within"] for s in FIVE}
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


@functools.cache
def CASES_MATCHES():  # noqa: N802  the rows as `cases.matches` reads them
    return {c: CASES[c]["match"] for c in CASES}


# ---------------------------------------------------------------------------------------------- the drawing


@pytest.mark.parametrize(
    "skill, level", [(s, lv) for s in FIVE for lv in LEVELS if lv in SETS[s]["difficulty"]]
)
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
        assert it.spec["op"] == "×" and it.responses[0].answer == str(a * b)
        assert set(it.responses[0].misconceptions) <= set(SETS[skill]["misconception_codes"]), (
            skill,
            it.spec,
        )


def test_a_case_that_names_its_method_is_printed_that_way():
    """In columns when the case is about columns or a long multiplication, in a line when it is about a line, and the
    tables in a line except where the case is a fact in columns (TF16)."""
    printed = {}
    for skill in FIVE:
        for level in _levels(skill):
            for code, it in _drawn(skill, level):
                printed.setdefault(code, set()).add(it.fmt)
    assert printed["T01"] == {"column_grid"} and printed["T02"] == {"bare_sum"}
    assert printed["TF16"] == {"column_grid"} and printed["T13"] == {"bare_sum"}
    assert printed["TZ07"] == {"column_grid"}
    for code in ("TF01", "TF02", "TF03", "TF04", "TF05", "TF06", "TF07", "TF15"):
        assert printed[code] == {"bare_sum"}, code
    for code in (
        "T04",
        "T17",
        "T19",
        "TC07",
    ):  # no method of its own: in columns and in a line, in fair shares
        assert printed[code] == {"bare_sum", "column_grid"}, code


def test_the_eleven_and_twelve_tables_appear_only_at_advance():
    """Assumption A4: the tables run from 0 to 12, and ×11 and ×12 appear only at Advance."""
    for level in ("Easy", "Medium", "Hard"):
        for _, it in _drawn("MUL.FACTS", level):
            assert max(it.spec["a"], it.spec["b"]) <= 10, (level, it.spec)
    top = {max(it.spec["a"], it.spec["b"]) for _, it in _drawn("MUL.FACTS", "Advance")}
    assert {11, 12} <= top


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
