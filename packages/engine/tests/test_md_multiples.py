"""Multiples, factors and divisibility (goals/md4c-multiples-and-factors.yaml).

MD.MULTIPLES asks for the multiples of a number, its factors and factor pairs, common multiples, and divisibility by
2, 3, 5 and 10. A list is one answer, written in any order, read group by group and marked as a whole. Every answer is
worked out here from the question's own numbers, never read back from the code that made it."""

import dataclasses
import importlib
import json
import math
import pathlib
import random
import re
import sys
from collections import Counter

from engine.adapters import ocr
from engine.assess import draw, render, skills, tags, taxonomy
from engine.assess import misconceptions as M
from engine.assess.pick import Sheet
from engine.checks import scenarios
from engine.w1_bank import cases
from engine.w3_read import boxes, marking, render_pdf
from tests.test_boxes import StandIn, _scanned, _write

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
RULES = {k.split(".", 1)[1]: v for k, v in CONFIG.items() if k.startswith("skills.")}
ROWS = json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
VOCAB = {(m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code")) for m in ROWS}
LEVELS = {"Easy": ["F01", "F02", "F06"], "Medium": ["F03", "F04", "F08"], "Hard": ["F05"], "Advance": ["F07"]}
GRADES = {"Easy": "G3", "Medium": "G3", "Hard": "G4", "Advance": "G4"}
R = "R50"
NEW = (
    "M_OUT_OF_RANGE",
    "M_NOT_A_MULTIPLE",
    "M_MULTIPLE_MISSED",
    "M_MULTIPLE_FOR_FACTOR",
    "M_NOT_A_FACTOR",
    "M_FACTOR_MISSED",
    "M_FACTOR_PAIR_TWICE",
    "M_MULTIPLE_OF_ONE_ONLY",
    "M_COMMON_MULTIPLE_MISSED",
    "M_LAST_DIGIT_RULE_MISAPPLIED",
    "M_FIRST_DIGIT_FOR_LAST",
    "M_FIVE_AS_TEN",
)
if str(ROOT / "research") not in sys.path:
    sys.path.insert(0, str(ROOT / "research"))


def _set():
    return SETS["MD.MULTIPLES"]


def _level(level, n, seed=5):
    check = _set()["difficulty"][level]["check"]
    matches = cases.on_level(check, {c: row["match"] for c, row in CASES.items()})
    got = draw.level(random.Random(seed), check, matches, R, n)
    assert len(got) == n, (level, len(got))
    return got


def _of(case, n=24, seed=5):
    level = next(lv for lv, cs in LEVELS.items() if case in cs)
    check = {**_set()["difficulty"][level]["check"], "cases": [case]}
    matches = cases.on_level(check, {c: row["match"] for c, row in CASES.items()})
    got = [it for _, it in draw.level(random.Random(seed), check, matches, R, n)]
    assert len(got) == n, (case, len(got))
    return got


def _r(it, rid):
    return next(r for r in it.responses if r.rid == rid)


def _members(text):
    """A list as written, its members in any order: numbers, or pairs written "3 × 8" (a pair either way round)."""
    out = []
    for part in re.split(r"\s*[,;]\s*", text.strip()):
        nums = [int(x) for x in re.findall(r"\d+", part)]
        if nums:
            out.append(tuple(sorted(nums)))
    return Counter(out)


def _numbers(it):
    """The question's own numbers, read from its sentence (the stem), never from what the code stored with it."""
    return [int(x) for x in re.findall(r"\d+", it.stem)]


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def _stored(r):
    return {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}


# ------------------------------------------------------------------------------------------- the kinds, case by case


def test_the_multiples_of_a_number_up_to_a_limit():
    """F01: the multiples of 6 up to 60. One list answer: every multiple from the number itself up to the limit, the limit
    a multiple or not; going past it, a step counted wrong and a multiple left out are each named."""
    for it in _of("F01"):
        n, limit = _numbers(it)[:2]
        assert it.fmt == "multiples" and f"multiples of {n} up to {limit}" in it.stem, it.stem
        (r,) = it.responses
        assert r.kind == "list" and _members(r.answer) == Counter((k,) for k in range(n, limit + 1, n)), (
            r.answer
        )
        assert {"M_OUT_OF_RANGE", "M_NOT_A_MULTIPLE", "M_MULTIPLE_MISSED"} <= set(r.misconceptions), (
            r.misconceptions
        )
        assert 5 * n <= limit <= 100, it.stem


def test_whether_a_number_is_a_multiple_of_another():
    """F02: is 45 a multiple of 5? A yes or a no, one as often as the other; a no that ends in the other number's digit
    (is 34 a multiple of 4?) names the last-digit rule used where it does not work."""
    drawn = _of("F02", 48)
    for it in drawn:
        number, of = _numbers(it)[:2]
        tick = _r(it, "yes")
        assert tick.options == ["yes", "no"] and tick.answer == ("yes" if number % of == 0 else "no"), it.stem
        if tick.answer == "no" and number % 10 == of % 10 and of not in (2, 5, 10):
            assert tick.misconceptions == {"M_LAST_DIGIT_RULE_MISAPPLIED": "yes"}, (
                it.stem,
                tick.misconceptions,
            )
        else:
            assert tick.misconceptions == {"M_REVERSES_CLAIM_TRUTH": "no" if tick.answer == "yes" else "yes"}
    yes = sum(_r(it, "yes").answer == "yes" for it in drawn)
    assert 0.3 <= yes / len(drawn) <= 0.7, yes


def test_divisible_by_two_five_and_ten_from_the_last_digit():
    """F06: is 340 divisible by 2, by 5 and by 10? Three ticks, a 3-digit number; a wrong tick that its first digit would
    give names the first digit read for the last, and a yes to 10 for a number ending in 5 takes 5 for 10."""
    for it in _of("F06", 36):
        (number,) = [x for x in _numbers(it) if x >= 100][:1]
        for rid, by in (("by2", 2), ("by5", 5), ("by10", 10)):
            tick = _r(it, rid)
            assert tick.answer == ("yes" if number % by == 0 else "no"), (number, rid)
            wrong = "no" if tick.answer == "yes" else "yes"
            first = "yes" if int(str(number)[0]) % by == 0 else "no"
            if by == 10 and number % 10 == 5:
                assert tick.misconceptions == {"M_FIVE_AS_TEN": "yes"}, (number, tick.misconceptions)
            elif first == wrong:
                assert tick.misconceptions == {"M_FIRST_DIGIT_FOR_LAST": wrong}, (
                    number,
                    rid,
                    tick.misconceptions,
                )
            else:
                assert tick.misconceptions == {"M_REVERSES_CLAIM_TRUTH": wrong}, (
                    number,
                    rid,
                    tick.misconceptions,
                )


def test_all_the_factors_and_the_factor_pairs_of_a_number():
    """F03: all the factors of 12, in any order; a multiple written for a factor, a number that does not divide and a
    factor left out are named. F04: the factor pairs of 24, each pair either way round; a pair written twice, turned
    round, is named."""
    for it in _of("F03"):
        (number,) = [x for x in _numbers(it)][:1]
        (r,) = it.responses
        assert r.kind == "list" and _members(r.answer) == Counter(
            (d,) for d in range(1, number + 1) if number % d == 0
        )
        assert 4 <= sum(_members(r.answer).values()) <= 8 and number <= 60, number
        assert {"M_MULTIPLE_FOR_FACTOR", "M_NOT_A_FACTOR", "M_FACTOR_MISSED"} <= set(r.misconceptions)
    for it in _of("F04"):
        (number,) = [x for x in _numbers(it)][:1]
        (r,) = it.responses
        want = Counter((d, number // d) for d in range(1, math.isqrt(number) + 1) if number % d == 0)
        assert r.kind == "list" and _members(r.answer) == want, (number, r.answer)
        assert {"M_FACTOR_PAIR_TWICE", "M_FACTOR_MISSED"} <= set(r.misconceptions), r.misconceptions


def test_the_common_multiples_of_two_numbers_below_a_limit():
    """F05: the common multiples of 3 and 4 below 30: every multiple of both under the limit, two to four of them; a
    multiple of one only, a common multiple left out and one past the limit are named."""
    for it in _of("F05"):
        a, b, limit = _numbers(it)[:3]
        (r,) = it.responses
        want = Counter((k,) for k in range(1, limit) if k % a == 0 and k % b == 0)
        assert r.kind == "list" and _members(r.answer) == want and 2 <= sum(want.values()) <= 4, (
            it.stem,
            r.answer,
        )
        assert {"M_MULTIPLE_OF_ONE_ONLY", "M_COMMON_MULTIPLE_MISSED", "M_OUT_OF_RANGE"} <= set(
            r.misconceptions
        )


def test_divisible_by_three_from_the_sum_of_the_digits():
    """F07: is 117 divisible by 3? The sum of its digits in a box (1 + 1 + 7 = □), then yes or no, one as often as the
    other; a wrong tick its last digit would give names the last-digit rule used where it does not work."""
    drawn = _of("F07", 48)
    for it in drawn:
        number = next(x for x in _numbers(it) if x >= 100)
        total, tick = _r(it, "sum"), _r(it, "by3")
        assert int(total.answer) == sum(map(int, str(number))) and total.misconceptions, (number, total)
        assert tick.answer == ("yes" if number % 3 == 0 else "no"), number
        wrong = "no" if tick.answer == "yes" else "yes"
        by_last = "yes" if number % 10 % 3 == 0 else "no"
        want = "M_LAST_DIGIT_RULE_MISAPPLIED" if by_last == wrong else "M_REVERSES_CLAIM_TRUTH"
        assert tick.misconceptions == {want: wrong}, (number, tick.misconceptions)
    yes = sum(_r(it, "by3").answer == "yes" for it in drawn)
    assert 0.3 <= yes / len(drawn) <= 0.7, yes


# ------------------------------------------------------------------------------------------- levels, balance, names


def test_each_level_holds_its_cases_at_the_grade_the_document_gives():
    """MD.MULTIPLES is Grade 3 at Easy and Medium and Grade 4 at Hard and Advance, as drafted; "Tables, multiples and
    factors" is the school's objective at both grades, on the skills its rung holds. A topic of its own, untaught."""
    s = _set()
    assert s["rung_code"] == R and s["level_band"] == GRADES, s["level_band"]
    assert {lv: d["check"]["cases"] for lv, d in s["difficulty"].items()} == LEVELS
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == R)
    registry = json.loads((SEED / "registry.json").read_text())
    named = {
        x["skill"] for x in registry["learning_objective_skills"] if x["lo"] in ("LO-G3-0942", "LO-G4-1339")
    }
    assert set(rung["skill_codes"]) == named == {"NUM.CNT.08", "NUM.OPS.03"} and rung["band"] == "G3", rung
    topic = next(
        t
        for t in json.loads((SEED / "topics.json").read_text())["topics"]
        if "MD.MULTIPLES" in t["skill_sets"]
    )
    assert topic["skill_sets"] == ["MD.MULTIPLES"] and topic["taught"] is False, topic
    drafted = importlib.import_module("md_taxonomy")
    _, _, grades, levels, _ = next(x for x in drafted.SKILLS if x[0] == "MD.MULTIPLES")
    assert grades == "G3 G3 G4 G4" and levels == LEVELS, (grades, levels)


def test_no_yes_or_no_is_answered_by_guessing():
    """Every tick is right one way as often as the other in every place it is asked: a 3-digit number divisible by 10
    one time in ten would let a child who always ticked no score nine in ten."""
    for case in ("F02", "F06", "F07", "F08"):
        places = {}
        for it in _of(case, 60, seed=11):
            for t in (r for r in it.responses if r.kind == "tick"):
                places.setdefault(t.rid, Counter())[t.answer] += 1
        for rid, seen in places.items():
            assert max(seen.values()) / sum(seen.values()) <= 0.7, (case, rid, seen)


def test_every_question_names_a_mistake_its_wrong_answer_shows():
    """Every question of every MD.MULTIPLES level names at least one mistake, each a row of the vocabulary."""
    rows = {code for code, _ in VOCAB}
    for level, cs in LEVELS.items():
        for _, it in _level(level, 4 * len(cs)):
            named = {c for r in it.responses for c in r.misconceptions}
            assert named and named <= rows, (level, it.stem, named)


def test_the_twelve_new_mistakes_are_rows_drafted_for_achal():
    """The twelve new mistakes are rows, each with what to do about it, counting against multiples and factors, on
    MD.MULTIPLES's list and in the drafted document's table for Achal to correct."""
    table = (ROOT / "docs/design/multiplication-division-taxonomy.md").read_text()
    for code in NEW:
        row = next(r for r in ROWS if r["code"] == code)
        assert row["name"] and row["repair_hint"] and "md4c" in row["source"], row
        assert row.get("skill_from") == "row" and row.get("skill_code") == "NUM.CNT.08", row
        assert code in _set()["misconception_codes"] and f"{code} (new)" in table, code


def test_a_list_is_printed_with_room_for_more_than_it_holds(tmp_path):
    """A list's numbers are printed as groups of boxes, two groups more than it holds and each with room for its widest
    number, beside the words "You may not need every space": the boxes do not tell the child how many there are."""
    its = [it for c in ("F01", "F03", "F04", "F05") for it in _of(c, 3)]
    key = render.render_sheet(Sheet("CS00D4C1", "G3", "Medium", 1, "W1", its), tmp_path)
    for it in its:
        (r,) = it.responses
        mine = [g for g in key["geometry"] if g["item"] == it.item_id and g["kind"] == "digit"]
        members = {g["resp"].split("#")[1].split(".")[0] for g in mine}
        assert len(members) == sum(_members(r.answer).values()) + 2, (it.stem, len(members))
        widest = max(len(str(x)) for m in _members(r.answer) for x in m)
        cells = Counter(g["resp"] for g in mine)
        assert min(cells.values()) >= widest, (it.stem, cells)
        assert "You may not need every space" in it.stem, it.stem


def test_a_right_answer_counts_for_multiples_and_the_tables():
    """A right answer counts for multiples (NUM.CNT.08) and the tables (NUM.OPS.03); a factor left out counts against
    multiples and factors, its row's own skill."""
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == R)
    it = _of("F03", 1)[0]
    used = skills.used(it.fmt, it.spec, it.stem, rung["skill_codes"], RULES)
    assert used[:2] == ["NUM.CNT.08", "NUM.OPS.03"], used
    assert skills.charges(it.fmt, it.spec, it.stem, used, ["M_FACTOR_MISSED"], VOCAB, RULES) == {
        "M_FACTOR_MISSED": "NUM.CNT.08"
    }


# ------------------------------------------------------------------------------------------- marking and reading


def test_a_list_is_marked_as_a_whole_in_any_order():
    """A list is right in any order and wrong as one answer: the factors of 12 written backwards are right; with 4 left
    out they are one wrong answer naming a factor left out, never a row of wrong boxes; with 24 added, a multiple written
    for a factor; a pair turned round counts once, and written both ways names the pair written twice."""
    it = next(x for x in _of("F03", 24) if _numbers(x)[0] == 12)
    r = _stored(it.responses[0])
    assert marking.mark(it.spec, r, _wrote("12, 6, 4, 3, 2, 1"))[0] == "correct"
    status, codes, _ = marking.mark(it.spec, r, _wrote("1, 2, 3, 6, 12"))
    assert (status, codes) == ("wrong", ["M_FACTOR_MISSED"]), (status, codes)
    status, codes, _ = marking.mark(it.spec, r, _wrote("1, 2, 3, 4, 6, 12, 24"))
    assert (status, codes) == ("wrong", ["M_MULTIPLE_FOR_FACTOR"]), (status, codes)
    pairs = next(x for x in _of("F04", 24) if _numbers(x)[0] == 24)
    p = _stored(pairs.responses[0])
    assert marking.mark(pairs.spec, p, _wrote("24 × 1, 12 × 2, 8 × 3, 6 × 4"))[0] == "correct"
    status, codes, _ = marking.mark(pairs.spec, p, _wrote("1 × 24, 2 × 12, 3 × 8, 8 × 3, 4 × 6"))
    assert (status, codes) == ("wrong", ["M_FACTOR_PAIR_TWICE"]), (status, codes)


def test_a_printed_list_is_read_group_by_group_and_marked(tmp_path, monkeypatch):
    """A printed paper, written on in any order and scanned as a phone hands it over: each group is read where it was
    written, the empty ones left out, and the list comes back as one answer that marking marks right; with one group
    left empty it is one wrong answer naming the factor left out."""
    reader = StandIn()
    monkeypatch.setattr(boxes.digits, "read", reader.read)
    its = [next(x for x in _of("F03", 24) if _numbers(x)[0] == 12), next(x for x in _of("F01", 24))]
    key = render.render_sheet(Sheet("CS00D4C2", "G3", "Easy", 1, "W1", its), tmp_path)
    pdf = tmp_path / "CS00D4C2.pdf"
    img = render_pdf.render(pdf, dpi=boxes.PPM * 25.4)[0]
    factors, multiples = (sorted(_members(it.responses[0].answer), reverse=True) for it in its)
    fills = {its[0].item_id: [m[0] for m in factors], its[1].item_id: [m[0] for m in multiples][:-1]}
    width = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    for g in key["geometry"]:
        if g["kind"] != "digit" or g["item"] not in fills:
            continue
        member, numbers = int(g["resp"].split("#")[1]) - 1, fills[g["item"]]
        if (
            member < len(numbers)
            and (ch := str(numbers[member]).rjust(width[(g["item"], g["resp"])])[g["k"]]).strip()
        ):
            _write(img, g, ch, boxes.PPM)
    scan = _scanned(img, tmp_path / "scan.pdf")
    wanted = {f"{n + 1}": (it.item_id, "list") for n, it in enumerate(its)}
    photo, frame = render_pdf.photo(scan, 1)
    got = boxes.read_page(photo, 1, pdf, key["geometry"], wanted, ocr.settings(), frame=frame)
    right = marking.mark(its[0].spec, _stored(its[0].responses[0]), got["1"])
    assert right[0] == "correct", (got["1"]["child_answer"], right)
    short = marking.mark(its[1].spec, _stored(its[1].responses[0]), got["2"])
    assert short[:2] == ("wrong", ["M_MULTIPLE_MISSED"]), (got["2"]["child_answer"], short)


def test_a_scenario_works_out_every_list_yes_or_no_and_digit_sum():
    """The scenarios' own check works out every list, tick and digit sum from the question's own numbers; one changed
    answer is found wrong."""
    for _, it in [x for level, cs in LEVELS.items() for x in _level(level, 4 * len(cs))]:
        assert scenarios._answer_is_right(it) is True, (it.stem, [(r.rid, r.answer) for r in it.responses])
        r = it.responses[0]
        if r.kind == "list":
            other = ", ".join(str(m[0]) for m in list(_members(r.answer))[1:])
        elif r.kind == "tick":
            other = next(o for o in r.options if o != r.answer)
        else:
            other = str(int(r.answer) + 1)
        bad = [dataclasses.replace(r, answer=other), *it.responses[1:]]
        assert scenarios._answer_is_right(dataclasses.replace(it, responses=bad)) is False, it.stem


def test_every_answer_is_marked_against_its_own_key():
    """Each list, box and tick marked by itself: its own key is right, and each wrong answer named for it names its
    mistake."""
    for level, cs in LEVELS.items():
        for _, it in _level(level, 4 * len(cs)):
            for r in it.responses:
                assert marking.mark(it.spec, _stored(r), _wrote(str(r.answer)))[0] == "correct", (
                    it.stem,
                    r.rid,
                )
                for code, wrong in r.misconceptions.items():
                    status, codes, _ = marking.mark(it.spec, _stored(r), _wrote(str(wrong)))
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
            assert c != "F08" or (it.fmt == "odd_even" and M.compute("×", it.spec["a"], it.spec["b"]) <= 144)
