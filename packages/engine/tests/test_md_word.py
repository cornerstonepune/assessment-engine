"""Stories with × and ÷ (goals/md4d1-times-stories.yaml).

MD.WORD asks for the stories of × and ÷, Grades 2 to 4: the sixteen that draw on other skills already, and ten new —
times as many, the smaller and how many times; half as many; the two-step stories with × and ÷; a number the story does
not need; a price list. Every answer is worked out here from the story's own numbers and its shape, never read back
from the code that made it."""

import dataclasses
import functools
import importlib
import json
import pathlib
import random
import re
import sys
from collections import Counter

from engine.assess import draw, skills, tags, taxonomy
from engine.checks import scenarios
from engine.w1_bank import cases
from engine.w3_read import marking

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
RULES = {k.split(".", 1)[1]: v for k, v in CONFIG.items() if k.startswith("skills.")}
ROWS = json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
VOCAB = {(m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code")) for m in ROWS}
TEMPLATES = json.loads((ROOT / "packages/engine/engine/assess/word_templates.json").read_text())[
    "word_templates"
]
LEVELS = {
    "Easy": ["B01", "B02", "B03", "B06"],
    "Medium": ["B04", "B05", "B07", "B11", "B27"],
    "Hard": ["B08", "B09", "B10", "B14", "B15", "B16", "B17"],
    "Advance": ["B12", "B13", "B18", "B19", "B20", "B21", "B22", "B23", "B25", "B26"],
}
GRADES = {"Easy": "G2", "Medium": "G2", "Hard": "G3", "Advance": "G4"}
# the shapes M4d1 adds, each a template row of its own
NEW_SHAPES = {
    "B09": "TIMES_AS_MANY_SMALLER",
    "B10": "HOW_MANY_TIMES",
    "B27": "HALF_AS_MANY",
    "B18": "MULTIPLY_THEN_ADD",
    "B19": "MULTIPLY_THEN_SUBTRACT",
    "B20": "DIVIDE_THEN_MULTIPLY",
    "B21": "TWO_PRODUCTS_ADDED",
    "B22": "ADD_THEN_DIVIDE",
    "B23": "BAR_MODEL_TIMES_AS_MANY",
    "B25": "EXTRA_INFORMATION",
    "B26": "RATE_TOTAL",
}
NEW = (
    "M_TIMES_WORD_MULTIPLIED",
    "M_HALF_AS_DOUBLE",
    "M_EXTRA_NUMBER_USED",
    "M_WRONG_PRICE_READ",
    "M_BAR_PART_MISSED",
)
if str(ROOT / "research") not in sys.path:
    sys.path.insert(0, str(ROOT / "research"))


def _set():
    return SETS["MD.WORD"]


def _rung():
    return _set()["rung_code"]


def _matches(check):
    return cases.on_level(check, {c: row["match"] for c, row in CASES.items()})


@functools.cache
def _level(level, n, seed=5):
    check = _set()["difficulty"][level]["check"]
    got = draw.level(random.Random(seed), check, _matches(check), _rung(), n)
    assert len(got) == n, (level, len(got))
    return tuple(got)


@functools.cache
def _of(case, n=24, seed=5):
    level = next(lv for lv, cs in LEVELS.items() if case in cs)
    check = {**_set()["difficulty"][level]["check"], "cases": [case]}
    got = [it for _, it in draw.level(random.Random(seed), check, _matches(check), _rung(), n)]
    assert len(got) == n, (case, len(got))
    return tuple(got)


def _ans(it):
    return next(r for r in it.responses if r.rid == "ans")


def _stated(r):
    return {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def _in_stem(it, *values):
    """Each number the story's working needs is printed in its own sentence."""
    printed = {int(x) for x in re.findall(r"\d+", it.stem.replace(",", ""))}
    return all(v in printed for v in values)


# ------------------------------------------------------------------------------------------- the new stories


def test_times_as_many_the_smaller_and_how_many_times():
    """B09: Dev has 12, 3 times as many as Riya: Riya has 12 ÷ 3; multiplying because the story says "times" is named.
    B10: Dev has 12 and Riya 4: 12 ÷ 4 times as many; answering how many more (12 − 4) is "times as many" read as
    "more"."""
    for it in _of("B09"):
        sp = it.spec
        a, b = sp["a"], sp["b"]
        assert sp["structure"] == "TIMES_AS_MANY_SMALLER" and sp["op"] == "÷" and a % b == 0 and b > 1, sp
        assert _in_stem(it, a, b) and "times as many" in it.stem, it.stem
        r = _ans(it)
        assert r.answer == str(a // b) and r.misconceptions.get("M_TIMES_WORD_MULTIPLIED") == a * b, r
    for it in _of("B10"):
        sp = it.spec
        a, b = sp["a"], sp["b"]
        assert sp["structure"] == "HOW_MANY_TIMES" and sp["op"] == "÷" and a % b == 0 and a // b > 1, sp
        assert _in_stem(it, a, b) and "times as many" in it.stem, it.stem
        r = _ans(it)
        assert r.answer == str(a // b) and r.misconceptions.get("M_TIMES_AS_MORE") == a - b, r


def test_half_as_many():
    """B27: Meera read 30 pages, Aman half as many: 30 ÷ 2; doubling (30 × 2) is half read as twice."""
    for it in _of("B27"):
        sp = it.spec
        a = sp["a"]
        assert sp["structure"] == "HALF_AS_MANY" and sp["op"] == "÷" and sp["b"] == 2 and a % 2 == 0, sp
        assert _in_stem(it, a) and "half as many" in it.stem, it.stem
        r = _ans(it)
        assert r.answer == str(a // 2) and r.misconceptions.get("M_HALF_AS_DOUBLE") == a * 2, r


# what each two-step story asks, and the number a child who stops after its first step writes
TWO_STEP = {
    "MULTIPLY_THEN_ADD": (lambda s: s["a"] * s["b"] + s["c"], lambda s: s["a"] * s["b"]),
    "MULTIPLY_THEN_SUBTRACT": (lambda s: s["a"] - s["b"] * s["c"], lambda s: s["b"] * s["c"]),
    "DIVIDE_THEN_MULTIPLY": (lambda s: s["b"] // s["a"] * s["c"], lambda s: s["b"] // s["a"]),
    "TWO_PRODUCTS_ADDED": (lambda s: s["a"] * s["b"] + s["c"] * s["d"], lambda s: s["a"] * s["b"]),
    "ADD_THEN_DIVIDE": (lambda s: (s["a"] + s["b"]) // s["c"], lambda s: s["a"] + s["b"]),
}


def test_the_two_step_stories_work_out_both_steps():
    """B18 to B22: × then +, × then −, ÷ then ×, two products added, + then ÷ — each answer worked from its numbers, its
    first step alone named as one step only, and every number printed. B23: Ria and Sam have 32, Sam 3 times as many:
    Ria has 32 ÷ (3 + 1); dividing by the times alone leaves out Ria's own part."""
    for case in ("B18", "B19", "B20", "B21", "B22"):
        shape = NEW_SHAPES[case]
        right, first = TWO_STEP[shape]
        for it in _of(case):
            sp = it.spec
            assert it.fmt == "word_2step" and sp["structure"] == shape, (case, sp)
            nums = [sp[k] for k in "abcd" if k in sp]
            assert _in_stem(it, *nums), (case, it.stem)
            if shape == "DIVIDE_THEN_MULTIPLY":
                assert sp["b"] % sp["a"] == 0, sp
            if shape == "ADD_THEN_DIVIDE":
                assert (sp["a"] + sp["b"]) % sp["c"] == 0, sp
            r = _ans(it)
            assert r.answer == str(right(sp)) and right(sp) > 0, (case, sp, r.answer)
            assert r.misconceptions.get("M_ONE_STEP_ONLY") == first(sp), (case, sp, r.misconceptions)
    for it in _of("B23"):
        sp = it.spec
        a, b = sp["a"], sp["b"]
        assert sp["structure"] == "BAR_MODEL_TIMES_AS_MANY" and a % (b + 1) == 0 and b > 1, sp
        assert _in_stem(it, a, b) and "times as many" in it.stem, it.stem
        r = _ans(it)
        assert r.answer == str(a // (b + 1)), (sp, r.answer)
        if a % b == 0:
            assert r.misconceptions.get("M_BAR_PART_MISSED") == a // b, (sp, r.misconceptions)


def test_a_number_the_story_does_not_need_and_a_price_list():
    """B25: 8 boxes of 9 mangoes and 3 drivers: 8 × 9; using the drivers too (8 × 9 × 3) is named. B26: a price list,
    pen ₹15, eraser ₹5: 3 pens cost 3 × 15; reading the eraser's price (3 × 5) is named."""
    for it in _of("B25"):
        sp = it.spec
        a, b, extra = sp["a"], sp["b"], sp["extra"]
        assert sp["structure"] == "EXTRA_INFORMATION" and sp["op"] == "×" and _in_stem(it, a, b, extra), (
            it.stem
        )
        r = _ans(it)
        assert r.answer == str(a * b) and r.misconceptions.get("M_EXTRA_NUMBER_USED") == a * b * extra, r
    for it in _of("B26"):
        sp = it.spec
        (item, price), (other, other_price) = sp["table"]
        assert sp["structure"] == "RATE_TOTAL" and sp["b"] == price and price != other_price, sp
        assert _in_stem(it, sp["a"]) and item and other, (it.stem, sp["table"])
        r = _ans(it)
        assert r.answer == str(sp["a"] * price), (sp, r.answer)
        assert r.misconceptions.get("M_WRONG_PRICE_READ") == sp["a"] * other_price, r.misconceptions


# ------------------------------------------------------------------------------------------- levels, ranges, names


def test_each_level_holds_its_cases_at_the_grade_the_document_gives():
    """MD.WORD is Grade 2 at Easy and Medium, Grade 3 at Hard, Grade 4 at Advance, as drafted; "Solve multi-step word
    problems using bar models" is the school's objective at Grades 2, 3 and 4, on the skills its rung holds. A topic of
    its own, untaught."""
    s = _set()
    assert (
        s["level_band"] == GRADES and {lv: d["check"]["cases"] for lv, d in s["difficulty"].items()} == LEVELS
    )
    rung = next(
        r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == s["rung_code"]
    )
    registry = json.loads((SEED / "registry.json").read_text())
    named = {
        x["skill"]
        for x in registry["learning_objective_skills"]
        if x["lo"] in ("LO-G2-0530", "LO-G3-0959", "LO-G4-1356")
    }
    assert set(rung["skill_codes"]) == named == {"NUM.OPS.03", "NUM.OPS.04"} and rung["band"] == "G2", rung
    topic = next(
        t for t in json.loads((SEED / "topics.json").read_text())["topics"] if "MD.WORD" in t["skill_sets"]
    )
    assert topic["skill_sets"] == ["MD.WORD"] and topic["taught"] is False, topic
    drafted = importlib.import_module("md_taxonomy")
    _, _, grades, levels, _ = next(x for x in drafted.SKILLS if x[0] == "MD.WORD")
    assert grades == "G2 G2 G3 G4" and levels == LEVELS, (grades, levels)


def test_every_new_story_says_the_range_its_numbers_take():
    """A9: each new story's template says the range each of its numbers may take, and every story drawn keeps to it —
    so no box holds 933 pencils."""
    for case, shape in NEW_SHAPES.items():
        rows = _new_rows(case, shape)
        assert rows, (case, shape)
        for t in rows:
            names = set(re.findall(r"\{([a-d])\}", t["text"])) | ({"a", "b"} if t.get("table") else set())
            assert names and names <= set(t.get("numbers", {})), (shape, t["text"], t.get("numbers"))
        for it in _of(case):
            t = next(t for t in rows if t["text"] == _template_of(it, rows))
            for k, span in t["numbers"].items():
                if k in it.spec:
                    lo, hi = (span, span) if isinstance(span, int) else span
                    assert lo <= it.spec[k] <= hi, (case, k, it.spec[k], span)


def _new_rows(case, shape):
    """The template rows M4d1 adds for a case: every row of a new shape; for B25 the one-step × story with a number it
    does not need (its + and − two-step rows are older); for B26 the × story read from a price list (the cost of many,
    without a table, is older)."""
    rows = [t for t in TEMPLATES if t["structure"] == shape]
    if case == "B25":
        return [t for t in rows if t["fmt"] == "word_1step" and t["op"] == "×"]
    if case == "B26":
        return [t for t in rows if t.get("table")]
    return rows


def _template_of(it, rows):
    """The row that wrote this story, matched by its words with the numbers and names taken out."""
    for t in rows:
        rx = re.escape(t["text"])
        rx = re.sub(r"\\\{(?:n|n2)\\\}", r"[A-Z][a-z]+", rx)
        rx = re.sub(r"\\\{[a-z0-9]+\\\}", r"[\\d,]+", rx)
        if re.fullmatch(rx, it.stem):
            return t["text"]
    raise AssertionError(f"no template wrote {it.stem!r}")


def test_every_question_names_a_mistake_its_wrong_answer_shows():
    """Every question of every MD.WORD level names at least one mistake, each a row of the vocabulary, and on the
    skill set's list."""
    rows = {code for code, _ in VOCAB}
    for level, cs in LEVELS.items():
        for _, it in _level(level, 2 * len(cs)):
            named = {c for r in it.responses for c in r.misconceptions}
            assert named and named <= rows, (level, it.stem, named)
            assert named <= set(_set()["misconception_codes"]), (
                level,
                named - set(_set()["misconception_codes"]),
            )


def test_the_six_new_mistakes_are_rows_drafted_for_achal():
    """The six new mistakes are rows (five new codes, and "times as many" read as "more" for a story that divides),
    each with what to do about it, on MD.WORD's list and in the drafted document's table for Achal to correct."""
    table = (ROOT / "docs/design/multiplication-division-taxonomy.md").read_text()
    for code in NEW:
        row = next(r for r in ROWS if r["code"] == code)
        assert row["name"] and row["repair_hint"] and "md4d1" in row["source"], row
        assert code in _set()["misconception_codes"] and f"{code} (new)" in table, code
    more = next(r for r in ROWS if (r["code"], r["op"]) == ("M_TIMES_AS_MORE", "÷"))
    assert more["repair_hint"] and "md4d1" in more["source"], more


def test_a_right_answer_counts_for_multiplying_and_dividing():
    """A story that multiplies counts for multiplying (NUM.OPS.03), one that divides for dividing (NUM.OPS.04)."""
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == _rung())
    for case, skill in (
        ("B09", "NUM.OPS.04"),
        ("B27", "NUM.OPS.04"),
        ("B25", "NUM.OPS.03"),
        ("B18", "NUM.OPS.03"),
    ):
        it = _of(case, 1)[0]
        used = skills.used(it.fmt, it.spec, it.stem, rung["skill_codes"], RULES)
        assert skill in used, (case, used)


# ------------------------------------------------------------------------------------------- the check and marking


def test_a_scenario_works_out_every_story_from_its_own_numbers():
    """The scenarios' own check works out every MD.WORD story from its numbers and shape, the two-step ones too; one
    changed answer is found wrong."""
    for level, cs in LEVELS.items():
        for _, it in _level(level, 2 * len(cs)):
            assert scenarios._answer_is_right(it) is True, (
                it.stem,
                it.spec,
                [(r.rid, r.answer) for r in it.responses],
            )
            r = it.responses[0]
            bad = [dataclasses.replace(r, answer=str(int(r.answer) + 1)), *it.responses[1:]]
            assert scenarios._answer_is_right(dataclasses.replace(it, responses=bad)) is False, it.stem


def test_every_answer_is_marked_against_its_own_key():
    """Each answer marked by itself: its own key is right, and each wrong answer named for it names its mistake."""
    for level, cs in LEVELS.items():
        for _, it in _level(level, 2 * len(cs)):
            for r in it.responses:
                assert marking.mark(it.spec, _stated(r), _wrote(str(r.answer)))[0] == "correct", (
                    it.stem,
                    r.rid,
                )
                for code, wrong in r.misconceptions.items():
                    status, codes, _ = marking.mark(it.spec, _stated(r), _wrote(str(wrong)))
                    assert status == "wrong" and code in codes, (it.stem, r.rid, code, wrong, codes)


def test_every_level_fills_each_case_as_often_as_it_asks():
    """Each level, filled as the bank fills it, holds every case it lists as often as its row asks (12 where it names
    none), every question distinct, and every question is the case it was drawn for."""
    for level, d in _set()["difficulty"].items():
        got = _level(level, d["min_items"])
        held = Counter(c for c, _ in got)
        assert len({it.item_id for _, it in got}) == len(got), level
        for c in d["check"]["cases"]:
            assert held[c] >= CASES[c].get("min_items", 12), (level, c, held[c])
        for c, it in got:
            assert taxonomy.matches(CASES[c]["match"], it.fmt, tags.derive(it)), (c, it.stem)
