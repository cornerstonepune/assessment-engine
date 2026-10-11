"""× and ÷ as equations a child completes or judges (goals/md4b2-equality.yaml).

MD.EQUALITY asks a child to complete or judge × and ÷ written as equations, each sentence printed with its own box or
its own tick. Every answer is worked out here from the sentence printed, never read back from the code that made it,
and every tick is checked to be right one way as often as the other."""

import dataclasses
import importlib
import json
import pathlib
import random
import re
import sys
from collections import Counter
from fractions import Fraction

from engine.assess import draw, render, skills, tags, taxonomy
from engine.assess import equality as EQ
from engine.assess import misconceptions as M
from engine.assess.pick import Sheet
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
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
LEVELS = {
    "Easy": ["Y01", "Y04", "Y05", "Y06", "Y16"],
    "Medium": ["Y02", "Y09", "Y10", "Y15"],
    "Hard": ["Y03", "Y11", "Y12", "Y13", "Y14"],
    "Advance": ["Y07", "Y08", "DR09", "C08"],
}
GRADES = {"Easy": "G3", "Medium": "G3", "Hard": "G4", "Advance": "G4"}
R = "R49"
NEW = ("M_DIV_BY_ZERO_AS_ZERO", "M_DIV_REMAINDER_LEFT_OUT", "M_DIV_BIGGER_DIVISOR")
if str(ROOT / "research") not in sys.path:
    sys.path.insert(0, str(ROOT / "research"))


def _equality():
    return SETS["MD.EQUALITY"]


def _level(level, n, seed=5):
    """[(case, question)] of one MD.EQUALITY level, drawn as the bank draws it."""
    check = _equality()["difficulty"][level]["check"]
    matches = cases.on_level(check, {c: row["match"] for c, row in CASES.items()})
    got = draw.level(random.Random(seed), check, matches, R, n)
    assert len(got) == n, (level, len(got))
    return got


def _of(case, n=24, seed=5):
    """`n` questions of one case, drawn alone on its MD.EQUALITY level."""
    level = next(lv for lv, cs in LEVELS.items() if case in cs)
    check = {**_equality()["difficulty"][level]["check"], "cases": [case]}
    matches = cases.on_level(check, {c: row["match"] for c, row in CASES.items()})
    got = [it for _, it in draw.level(random.Random(seed), check, matches, R, n)]
    assert len(got) == n, (case, len(got))
    return got


def _value(side):
    """A side of a printed sentence worked out here: whole numbers, + − × ÷ and brackets, exactly; None for ÷ 0."""
    expr = side.replace("×", "*").replace("÷", "/").replace("−", "-").strip()
    if not re.fullmatch(r"[\d\s()+\-*/]+", expr):
        raise AssertionError(f"not a sum: {side!r}")
    expr = re.sub(r"\d+", lambda m: f"Fraction({m[0]})", expr)
    try:
        return eval(expr, {"Fraction": Fraction, "__builtins__": {}})  # noqa: S307 — digits and signs only, checked above
    except ZeroDivisionError:
        return None


def _holds(sentence):
    """Every side of the sentence the same number; a side with none (÷ 0) holds nothing."""
    sides = [_value(s) for s in sentence.split("=")]
    return None not in sides and len(set(sides)) == 1


def _box(r):
    """The number a response's box stands for, worked out from its own sentence (`label`) here."""
    clause = next(c for c in re.split(r", so | and ", r.label) if "□" in c)
    fits = [x for x in range(0, 10000) if _holds(clause.replace("□", str(x)))]
    assert len(fits) == 1, (r.label, fits[:5])
    return fits[0]


def _tick(r):
    """The tick a response's sentence asks, worked out here: a sign, a comparison, or true or false."""
    if set(r.options) <= {"×", "÷", "+", "−"}:
        fits = [o for o in r.options if _holds(r.label.replace("□", o))]
        assert len(fits) == 1, (r.label, fits)
        return fits[0]
    if set(r.options) == {"<", "=", ">"}:
        left, right = (_value(s) for s in r.label.split("○"))
        return "<" if left < right else ">" if left > right else "="
    assert r.options == ["true", "false"], r.options
    return "true" if _holds(r.label) else "false"


def _ticks(it):
    return [r for r in it.responses if r.kind == "tick"]


# ------------------------------------------------------------------------------------------- the shapes, Easy


def test_a_product_turned_round_and_true_or_false_about_turning_round():
    """Y01: 6 × 8 = 8 × □; = read as "the answer comes next" writes 48. Y16: true or false, a product turned round
    beside a difference turned round (7 × 6 = 6 × 7, 9 − 4 = 4 − 9), in either order: ticking true for the difference
    turns a subtraction round; false for the product reverses a true claim."""
    for it in _of("Y01"):
        (r,) = it.responses
        assert it.fmt == "equation" and r.answer == str(_box(r)), r.label
        product = _value(r.label.split("=")[0])
        assert r.misconceptions.get("M_EQUALS_MEANS_ANSWER") == product, (r.label, r.misconceptions)
    for it in _of("Y16"):
        ticks = _ticks(it)
        assert len(ticks) == 2 and {t.answer for t in ticks} == {"true", "false"}, [t.label for t in ticks]
        for t in ticks:
            assert t.answer == _tick(t), t.label
            if "×" in t.label:
                assert t.answer == "true" and t.misconceptions == {"M_REVERSES_CLAIM_TRUTH": "false"}, t.label
            else:
                assert "−" in t.label and t.misconceptions == {"M_SUB_INSTEAD": "true"}, t.label


def test_times_one_divided_by_one_by_itself_and_zero_divided():
    """Y05: 37 × 1 = □ and 37 ÷ 1 = □, × 1 adding one named. Y06: 9 ÷ 9 = □ and 0 ÷ 9 = □, a number ÷ itself as 0 and
    0 ÷ a number as the number named."""
    for it in _of("Y05"):
        times, divided = it.responses
        assert "× 1 =" in times.label and "÷ 1 =" in divided.label, (times.label, divided.label)
        n = int(times.label.split()[0])
        assert times.answer == divided.answer == str(n) == str(_box(times)) == str(_box(divided))
        assert times.misconceptions.get("M_ONE_ADDED") == n + 1, times.misconceptions
    for it in _of("Y06"):
        itself, zero = it.responses
        n = int(itself.label.split()[0])
        assert itself.label == f"{n} ÷ {n} = □" and zero.label == f"0 ÷ {n} = □", (itself.label, zero.label)
        assert (itself.answer, zero.answer) == ("1", "0") == (str(_box(itself)), str(_box(zero)))
        assert itself.misconceptions == {"M_DIV_SELF_AS_ZERO": 0} and zero.misconceptions == {
            "M_DIV_ZERO_DIVIDED": n
        }


# ------------------------------------------------------------------------------------------- Medium


def test_three_numbers_grouped_either_way_and_a_factor_doubled():
    """Y02: (2 × 7) × 5 = 2 × (7 × 5) = □, its outer two numbers making 10 or 20; every number added is named, never
    where that is also one bracket's value (2 + 7 + 5 is 2 × 7). Y15: 12 × 5 = 60, so 12 × 10 = □, the answer's slips
    as multiplication names them."""
    for it in _of("Y02"):
        (r,) = it.responses
        a, b, c = map(int, re.findall(r"\d+", r.label.split("=")[0]))
        assert r.label == f"({a} × {b}) × {c} = {a} × ({b} × {c}) = □" and a * c in (10, 20), r.label
        assert int(r.answer) == a * b * c == _box(r)
        assert r.misconceptions.get("M_ADD_ALL") == a + b + c not in (a * b, b * c), r.misconceptions
    for it in _of("Y15"):
        (r,) = it.responses
        given, asked = r.label.split(", so ")
        assert _holds(given) and int(r.answer) == _box(r), r.label
        a, b = map(int, re.findall(r"\d+", given)[:2])
        assert asked == f"{a} × {2 * b} = □", r.label
        assert r.misconceptions and all(
            v in M.predict("×", a, 2 * b).values() for v in r.misconceptions.values()
        ), r.misconceptions


# ------------------------------------------------------------------------------------------- Hard


def test_a_factor_partitioned_and_a_balance_against_minus_and_divide():
    """Y03: 7 × 12 = 7 × 10 + 7 × □. Y11: 3 × 8 = 30 − □. Y12: 6 × 4 = 48 ÷ □. Writing the left side's product is = read
    as "the answer comes next"; adding every number is named too where it is another value."""
    for case in ("Y03", "Y11", "Y12"):
        for it in _of(case):
            (r,) = it.responses
            left = _value(r.label.split("=")[0])
            assert int(r.answer) == _box(r), r.label
            assert r.misconceptions.get("M_EQUALS_MEANS_ANSWER") == left, (case, r.label, r.misconceptions)
            assert int(r.answer) not in r.misconceptions.values(), r.label
    for it in _of("Y11") + _of("Y12"):
        (r,) = it.responses
        assert "M_ADD_ALL" in r.misconceptions, r.label


def test_the_missing_sign_and_comparing_without_working_for_times_and_divide():
    """Y13: 6 □ 3 = 18 and 18 □ 3 = 6, one × and one ÷, either first; the wrong sign is named. Y14: 25 × 4 ○ 25 × 5 and
    48 ÷ 6 ○ 48 ÷ 8: a × comparison turned round is named, and a ÷ one answered as if a bigger divisor gave a bigger
    answer."""
    for it in _of("Y13"):
        ticks = _ticks(it)
        assert sorted(t.answer for t in ticks) == ["×", "÷"], [t.label for t in ticks]
        for t in ticks:
            assert t.options == ["×", "÷"] and t.answer == _tick(t), t.label
            assert t.misconceptions == {"M_WRONG_OP": "÷" if t.answer == "×" else "×"}, t.misconceptions
    for it in _of("Y14"):
        ticks = _ticks(it)
        assert len(ticks) == 2 and {"×" in t.label for t in ticks} == {True, False}, [t.label for t in ticks]
        for t in ticks:
            assert t.options == ["<", "=", ">"] and t.answer == _tick(t) != "=", t.label
            flipped = {"<": ">", ">": "<"}[t.answer]
            code = "M_COMPARE_REVERSED" if "×" in t.label else "M_DIV_BIGGER_DIVISOR"
            assert t.misconceptions == {code: flipped}, (t.label, t.misconceptions)


# ------------------------------------------------------------------------------------------- Advance


def test_true_or_false_about_dividing_by_zero_and_a_division_turned_round():
    """Y07: 9 ÷ 0 = 0 beside 0 ÷ 9 = 0, either first: ÷ 0 read as 0 (new) and 0 ÷ a number taken as the number are
    named. Y08: 12 ÷ 3 = 3 ÷ 12 beside 12 × 3 = 3 × 12: a division turned round as if it could be is named."""
    for it in _of("Y07"):
        ticks = _ticks(it)
        assert {t.answer for t in ticks} == {"true", "false"}, [t.label for t in ticks]
        for t in ticks:
            assert t.answer == _tick(t), t.label
            want = (
                {"M_DIV_BY_ZERO_AS_ZERO": "true"} if "÷ 0 =" in t.label else {"M_DIV_ZERO_DIVIDED": "false"}
            )
            assert t.misconceptions == want, (t.label, t.misconceptions)
    for it in _of("Y08"):
        ticks = _ticks(it)
        assert {t.answer for t in ticks} == {"true", "false"}, [t.label for t in ticks]
        for t in ticks:
            assert t.answer == _tick(t), t.label
            want = (
                {"M_DIV_BIGGER_BY_SMALLER": "true"} if "÷" in t.label else {"M_REVERSES_CLAIM_TRUTH": "false"}
            )
            assert t.misconceptions == want, (t.label, t.misconceptions)


def test_a_remainder_checked_by_multiplying_back():
    """DR09: is 85 ÷ 4 = 21 r 1? 21 × 4 + 1 = □. The claim is right or a named slip of the division layout, one as often
    as the other; the check adds the claim's remainder back, and leaving it out is named (new)."""
    drawn = _of("DR09", 48)
    for it in drawn:
        s = it.spec
        q, r = divmod(s["a"], s["b"])
        assert it.fmt == "inverse_check" and r, s
        check = next(x for x in it.responses if x.rid == "check")
        cq, cr = map(int, re.fullmatch(r"(\d+) × \d+ \+ (\d+) = □", check.label).groups())
        assert int(check.answer) == cq * s["b"] + cr == _box(check), check.label
        assert check.misconceptions.get("M_DIV_REMAINDER_LEFT_OUT") == cq * s["b"], check.misconceptions
    rights = sum(next(x for x in it.responses if x.rid == "right").answer == "yes" for it in drawn)
    assert 0.3 <= rights / len(drawn) <= 0.7, rights


def test_a_wrong_answer_explained_by_multiplying_back():
    """C08: Riya says 804 ÷ 4 = 21; multiply back, 21 × 4 = □, and say why it cannot be right. The claim is a named slip
    of the division layout; the product is a box keyed by multiplication's slips; no yes-or-no tick to guess."""
    for it in _of("C08"):
        s = it.spec
        assert it.fmt == "explain_claim" and s["op"] == "÷" and not _ticks(it), s
        check, why = it.responses
        cq = int(s["claimed"])
        assert cq * s["b"] != s["a"] and check.label == f"{cq} × {s['b']} = □", (s, check.label)
        assert int(check.answer) == cq * s["b"] == _box(check)
        assert check.misconceptions and why.kind == "text" and "multipl" in (why.rubric or ""), why.rubric


# ------------------------------------------------------------------------------------------- levels, sizes, balance


def test_each_level_holds_its_cases_at_the_grade_the_document_gives():
    """MD.EQUALITY is Grade 3 at Easy and Medium and Grade 4 at Hard and Advance, as drafted; "Missing numbers in
    equations" is the school's objective at both grades. A rung of its own, a topic of its own, untaught."""
    s = _equality()
    assert s["rung_code"] == R and s["level_band"] == GRADES, s["level_band"]
    assert {lv: d["check"]["cases"] for lv, d in s["difficulty"].items()} == LEVELS
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == R)
    assert rung["skill_codes"] == ["NUM.OPS.05", "NUM.PRB.03"] and rung["band"] == "G3", rung
    topic = next(
        t
        for t in json.loads((SEED / "topics.json").read_text())["topics"]
        if "MD.EQUALITY" in t["skill_sets"]
    )
    assert topic["skill_sets"] == ["MD.EQUALITY"] and topic["taught"] is False, topic
    drafted = importlib.import_module("md_taxonomy")
    _, _, grades, levels, _ = next(x for x in drafted.SKILLS if x[0] == "MD.EQUALITY")
    assert grades == "G3 G3 G4 G4" and levels == LEVELS, (grades, levels)
    registry = {
        lo["code"]: lo["title"]
        for lo in json.loads((SEED / "registry.json").read_text())["learning_objectives"]
    }
    assert registry["LO-G3-0937"] == registry["LO-G4-1334"] == "Missing numbers in equations"


def test_every_case_draws_on_its_examples_sizes():
    """Y04 is 456 × 0 (3 digits by a zero), Y09 a table fact, Y10 96 ÷ 4 and DR09 85 ÷ 4 (2 digits by 1), C08 804 ÷ 4
    (3 by 1): their rows say so, and none is drawn past them (8644 × 0, 167 × 417, 4424 ÷ 7 were). Y09 and Y10 are also
    on MUL.FACTS and DIV.2D1D, whose levels already drew them that size: there they draw what they drew before."""
    want = {"Y04": (3, 1), "Y10": (2, 1), "DR09": (2, 1), "C08": (3, 1)}
    for case, sizes in want.items():
        for it in _of(case, 12):
            got = (len(str(it.spec["a"])), len(str(it.spec["b"])))
            assert (tuple(sorted(got, reverse=True)) if case == "Y04" else got) == sizes, (case, it.spec)
            assert taxonomy.matches(CASES[case]["match"], it.fmt, tags.derive(it)), (case, it.spec)
    assert CASES["Y09"]["match"].get("fact") == "YES", CASES["Y09"]["match"]
    for it in _of("Y09", 12):
        assert tags.derive(it)["fact"] == "YES", it.spec
    new = ("fact", "operand_1_digits", "operand_2_digits")
    for case, code in {"Y09": "MUL.FACTS", "Y10": "DIV.2D1D"}.items():
        before = {
            **CASES,
            case: {**CASES[case], "match": {k: v for k, v in CASES[case]["match"].items() if k not in new}},
        }
        check = {**SETS[code]["difficulty"]["Advance"]["check"], "cases": [case]}
        drawn = []
        for rows in (CASES, before):
            matches = cases.on_level(check, {c: row["match"] for c, row in rows.items()})
            drawn.append(
                [
                    it.item_id
                    for _, it in draw.level(random.Random(5), check, matches, SETS[code]["rung_code"], 12)
                ]
            )
        assert drawn[0] == drawn[1] and len(drawn[0]) == 12, (case, code)


def test_no_tick_is_answered_by_guessing():
    """A true-or-false, a sign and a comparison are right one way as often as the other, in every place they are asked:
    9 ÷ 0 = 0 alone would be false every time, and a child ticking false every time would score it all."""
    for case in ("Y07", "Y08", "Y13", "Y14", "Y16"):
        places = {}
        for it in _of(case, 60, seed=11):
            for t in _ticks(it):
                places.setdefault(t.rid, Counter())[t.answer] += 1
        for rid, seen in places.items():
            assert max(seen.values()) / sum(seen.values()) <= 0.7, (case, rid, seen)


def test_every_question_names_a_mistake_its_wrong_answer_shows():
    """Every question of every MD.EQUALITY level names at least one mistake, each a row of the vocabulary; and a
    comparison of two equal sums (+ and −) names the one changed number seen and its partner's change missed."""
    rows = {code for code, _ in VOCAB}
    for level, cs in LEVELS.items():
        for _, it in _level(level, 4 * len(cs)):
            named = {c for r in it.responses for c in r.misconceptions}
            assert named and named <= rows, (level, it.spec, named)
    rng, equal = random.Random(3), 0
    while equal < 20:
        try:
            it = EQ.equation(rng, "R16", "Conceptual", "COMPARE")
        except RuntimeError:
            continue
        (t,) = it.responses
        if t.answer == "=":
            equal += 1
            assert set(t.misconceptions) == {"M_APPLIES_COMPENSATION_ONE"}, (it.spec, t.misconceptions)


def test_the_three_new_mistakes_are_rows_drafted_for_achal():
    """÷ 0 read as 0, a remainder left out of its check, and a bigger divisor taken to give a bigger answer are rows of
    division's, each with what to do about it, and on MD.EQUALITY's list."""
    for code in NEW:
        row = next(r for r in ROWS if r["code"] == code)
        assert row["op"] == "÷" and row["name"] and row["repair_hint"] and "md4b2" in row["source"], row
        assert code in _equality()["misconception_codes"], code


def test_the_document_pairs_each_true_or_false_with_its_other():
    """The drafted document is corrected at its source: each true-or-false is asked beside its other, so the answers
    it shows are one true and one false; and the three new mistakes are in its table of mistakes for Achal to correct."""
    assert DOC["Y07"]["example"] == "9 ÷ 0 = 0 and 0 ÷ 9 = 0" and DOC["Y07"]["answer"] == "false and true"
    assert (
        DOC["Y08"]["example"] == "12 ÷ 3 = 3 ÷ 12 and 12 × 3 = 3 × 12"
        and DOC["Y08"]["answer"] == "false and true"
    )
    assert (
        DOC["Y16"]["example"] == "7 × 6 = 6 × 7 and 9 − 4 = 4 − 9"
        and DOC["Y16"]["answer"] == "true and false"
    )
    table = (ROOT / "docs/design/multiplication-division-taxonomy.md").read_text()
    assert all(f"{code} (new)" in table for code in NEW), [c for c in NEW if f"{c} (new)" not in table]


# ------------------------------------------------------------------------------------------- skills, scenarios, paper


def test_a_right_answer_counts_for_equations_and_the_operation():
    """A right equation counts for missing numbers in equations (NUM.OPS.05), reasoning and the operations it uses; = read
    as "the answer comes next" against equations, a division slip against division."""
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == R)
    it = _of("Y12", 1)[0]
    used = skills.used(it.fmt, it.spec, it.stem, rung["skill_codes"], RULES)
    assert used[0] == "NUM.OPS.05" and {"NUM.OPS.03", "NUM.OPS.04"} <= set(used), used
    assert skills.charges(it.fmt, it.spec, it.stem, used, ["M_EQUALS_MEANS_ANSWER"], VOCAB, RULES) == {
        "M_EQUALS_MEANS_ANSWER": "NUM.OPS.05"
    }


def _every_level():
    return [it for level, cs in LEVELS.items() for _, it in _level(level, 4 * len(cs))]


def test_a_scenario_works_out_every_equation_from_its_sentence():
    """The scenarios' own check works out every box and tick from the sentence printed: MD.EQUALITY's, and + and −
    equations' and missing numbers among three numbers, where it worked out none. One changed answer is found wrong."""
    made = list(_every_level())
    rng = random.Random(7)
    for shape in (
        "MISSING_SIGN",
        "MISSING_SIGNS",
        "BALANCE_SAME_OP",
        "BALANCE_TWO_OPS",
        "SAME_BOTH_SIDES",
        "TRUE_FALSE",
        "COMPARE",
    ):
        for _ in range(6):
            try:
                made.append(EQ.equation(rng, "R16", "Conceptual", shape))
            except RuntimeError:
                continue
    for it in made:
        assert scenarios._answer_is_right(it) is True, (
            it.fmt,
            it.spec,
            [(r.label, r.answer) for r in it.responses],
        )
        r = next(x for x in it.responses if x.kind in ("digits", "tick"))
        other = next(o for o in r.options if o != r.answer) if r.kind == "tick" else str(int(r.answer) + 1)
        bad = [dataclasses.replace(x, answer=other) if x is r else x for x in it.responses]
        assert scenarios._answer_is_right(dataclasses.replace(it, responses=bad)) is False, it.spec


def test_every_box_is_where_the_printed_key_says_it_is(tmp_path):
    """A sheet of every case, printed through Chromium as a paper is: the key's geometry holds each sentence's own box,
    room for every digit of its answer, and each tick's own options, so the reader finds every one."""
    its = _every_level()
    key = render.render_sheet(Sheet("CS00D4B2", "G4", "Hard", 1, "W1", its), tmp_path)
    boxes = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    opts = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "tick")
    for it in its:
        for r in it.responses:
            if r.kind == "digits":
                assert boxes[(it.item_id, r.rid)] >= len(r.answer), (
                    it.spec,
                    r.rid,
                    boxes[(it.item_id, r.rid)],
                )
            elif r.kind == "tick":
                assert opts[(it.item_id, r.rid)] == len(r.options), (
                    it.spec,
                    r.rid,
                    opts[(it.item_id, r.rid)],
                )


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def test_every_box_and_tick_is_marked_against_its_own_key():
    """Each box and tick marked by itself: its own key is right, and each wrong value named for it names its mistake."""
    for it in _every_level():
        for r in it.responses:
            if r.kind not in ("digits", "tick"):
                continue
            stored = {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}
            assert marking.mark(it.spec, stored, _wrote(r.answer))[0] == "correct", (it.spec, r.rid)
            for code, wrong in r.misconceptions.items():
                status, codes, _ = marking.mark(it.spec, stored, _wrote(str(wrong)))
                assert status == "wrong" and code in codes, (it.spec, r.rid, code, wrong)


def test_every_level_fills_each_case_as_often_as_it_asks():
    """A case is covered when the bank holds as many of it as its row asks (12 where it names none); each level, filled
    as the bank fills it, holds every case it lists that often, every question distinct."""
    for level, d in _equality()["difficulty"].items():
        got = _level(level, d["min_items"])
        held = Counter(c for c, _ in got)
        assert len({it.item_id for _, it in got}) == len(got), level
        for c in d["check"]["cases"]:
            assert held[c] >= CASES[c].get("min_items", 12), (level, c, held[c])
