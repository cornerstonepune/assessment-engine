"""The written methods of division, printed step by step (goals/md3d-division-methods.yaml).

Every calculation of DIV.2D1D's and DIV.3D1D's Easy to Hard levels is printed in each method its level lists, in fair
shares (assumption A1): in a line, partitioning the number divided, chunking, short division with each exchange written
small, and long division. Every step and total is worked out here from the question's own numbers — the parts divided,
the lots taken away, the remainder exchanged, the digit brought down — never read back from the code that made it."""

import dataclasses
import json
import os
import pathlib
import random
from collections import Counter

import pytest

from engine.assess import divide_methods as DVM
from engine.assess import draw, placing, render, skills, stale, tags, taxonomy, verify
from engine.assess import operations as O
from engine.assess.items import Item, item
from engine.assess.pick import Sheet
from engine.core import db
from engine.w3_read import marking

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase" / "seed"
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
RULES = {k.split(".", 1)[1]: v for k, v in CONFIG.items() if k.startswith("skills.")}
VOCAB = {
    (m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code"))
    for m in json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
}
SKILLS = ("DIV.2D1D", "DIV.3D1D")
STRAIGHT = ("Easy", "Medium", "Hard")
PLACES = ("ones", "tens", "hundreds")
LAYOUT = (
    "column_grid"  # the division layout: the quotient's boxes over the number divided, one over every digit
)


def _check(skill, level):
    return SETS[skill]["difficulty"][level]["check"]


def _matches(check):
    codes = [*check["cases"], *check.get("methods", [])]
    return {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in codes}


def _drawn(skill, level, n, seed=3, cases=None):
    """[(case, question)] of one level, drawn as the bank draws it."""
    check = _check(skill, level) | ({"cases": cases} if cases else {})
    got = draw.level(random.Random(seed), check, _matches(check), SETS[skill]["rung_code"], n)
    assert len(got) == n, (skill, level, len(got))
    return got


def _method(it):
    return tags.derive(it)["method"]


def _keys(it):
    return {r.rid: r.answer for r in it.responses}


def _box(it, rid):
    return next(r for r in it.responses if r.rid == rid)


def _steps(it):
    """Every step's key in order: every box but the answer's, its remainder's and an exchange's."""
    return [r.answer for r in it.responses if r.rid not in ("ans", "rem") and not r.rid.startswith("x")]


# ------------------------------------------------------------------------------- each method worked here


def _parts(a, b):
    """72 ÷ 4 → [40, 32]: the most tens of lots of the divisor, then the rest."""
    first = a // (10 * b) * 10 * b
    return [first, a - first]


def _takes(a, b):
    """96 ÷ 4 → [(20, 80, 16), (4, 16, 0)]: for each place of the quotient, largest first, the lots of the divisor that
    place is worth, what they take away, and what is left. A place worth nothing takes nothing."""
    q, left, out = str(a // b), a, []
    for i, d in enumerate(q):
        lots = int(d) * 10 ** (len(q) - 1 - i)
        if lots:
            left -= lots * b
            out.append((lots, lots * b, left))
    return out


def _exchanges(a, b):
    """72 ÷ 4 → [(1, 3)]: before which digit (its place from the left) a remainder is written small, and how much; a
    digit that divides exactly passes nothing on, and the last digit passes on the remainder itself."""
    out, r = [], 0
    for i, d in enumerate(str(a)[:-1]):
        r = (r * 10 + int(d)) % b
        if r:
            out.append((i + 1, r))
    return out


def _cycles(a, b):
    """516 ÷ 4 → [(5, 4, 11), (11, 8, 36), (36, 36, 0)]: each number divided in turn, what its quotient digit times the
    divisor takes away, and what is left with the next digit brought down (the last: the remainder). The first is the
    number's leading digits, as few as reach the divisor."""
    s, k = str(a), 1
    while int(s[:k]) < b and k < len(s):
        k += 1
    partial, out = int(s[:k]), []
    for nxt in [*s[k:], None]:
        product = partial // b * b
        after = (partial - product) * 10 + int(nxt) if nxt is not None else partial - product
        out.append((partial, product, after))
        partial = after
    return out


# ------------------------------------------------------------------------------- the levels


def test_every_level_prints_each_calculation_in_every_method_it_lists():
    """A1: Easy to Hard print each calculation in every written method the document lists for the skill, in fair shares —
    each case's questions dealt evenly over the methods — and every question is still one of its level's cases. Each
    skill prints in a line too (A2, "division prints in a line by default"): DIV.2D1D's line is D02, DIV.3D1D's D15."""
    listed = {s: SETS[s]["difficulty"]["Easy"]["check"].get("methods") for s in SKILLS}
    assert listed == {"DIV.2D1D": ["D02", "G21", "G22", "G23"], "DIV.3D1D": ["D15", "G22", "G23", "G24"]}
    assert _check("DIV.2D1D", "Easy")["cases"] == ["D01"], (
        "D02 is the line every Easy calculation is printed in"
    )
    for skill in SKILLS:
        for level in STRAIGHT:
            check = _check(skill, level)
            assert check.get("methods") == listed[skill], (skill, level)
            ways = [CASES[m]["match"]["method"] for m in check["methods"]]
            each = len(ways) * 2
            per_case = {c: Counter() for c in check["cases"]}
            for case, it in _drawn(skill, level, len(check["cases"]) * each):
                assert verify.dimension_problems(tags.derive(it), check, it.fmt, _matches(check)) == [], (
                    it.spec
                )
                per_case[case][_method(it)] += 1
            for case, counts in per_case.items():
                assert counts == dict.fromkeys(ways, 2), (skill, level, case, counts)


# ------------------------------------------------------------------------------- each method, step by step


def test_partitioning_divides_each_part_then_adds():
    """72 ÷ 4 is 40 ÷ 4 = □ and 32 ÷ 4 = □, then 72 ÷ 4 = □: the most tens of lots of the divisor, then the rest. A part
    that leaves a remainder has a box for it after "r", as the total does (85 ÷ 4: 5 ÷ 4 = 1 r 1, 21 r 1)."""
    it = DVM.make("PARTITION_DIVIDEND", 72, 4, "R44")
    assert (it.fmt, it.spec["method"], it.spec["op"]) == ("partitioning", "PARTITION_DIVIDEND", "÷")
    assert [(r.label, r.answer) for r in it.responses] == [
        ("40 ÷ 4 =", "10"),
        ("32 ÷ 4 =", "8"),
        ("72 ÷ 4 =", "18"),
    ]
    it = DVM.make("PARTITION_DIVIDEND", 85, 4, "R44")
    assert [(r.rid, r.label, r.answer) for r in it.responses] == [
        ("s1", "80 ÷ 4 =", "20"),
        ("s2", "5 ÷ 4 =", "1"),
        ("s2r", "r", "1"),
        ("ans", "85 ÷ 4 =", "21"),
        ("rem", "r", "1"),
    ]
    for a, b in ((96, 4), (91, 7), (75, 4), (62, 3), (99, 9)):
        it = DVM.make("PARTITION_DIVIDEND", a, b, "R44")
        p = _parts(a, b)
        assert [r.label for r in it.responses if r.rid in ("s1", "s2")] == [f"{x} ÷ {b} =" for x in p], (a, b)
        assert _keys(it)["s1"] == str(p[0] // b) and _keys(it)["s2"] == str(p[1] // b), (a, b)
        assert _keys(it).get("s2r") == (str(p[1] % b) if p[1] % b else None), (a, b)
        assert (_keys(it)["ans"], _keys(it).get("rem")) == (str(a // b), str(a % b) if a % b else None), (
            a,
            b,
        )


def test_chunking_takes_away_the_lots_of_each_place_then_the_rest():
    """96 ÷ 4: take 20 × 4 = 80, 16 left; take 4 × 4 = 16, 0 left; the lots added, 24. For each place of the quotient,
    largest first, three boxes: the lots, what they take away, what is left; the last left is the remainder."""
    it = DVM.make("CHUNKING", 96, 4, "R44")
    assert (it.fmt, it.spec["method"]) == ("chunking", "CHUNKING")
    assert _steps(it) == ["20", "80", "16", "4", "16", "0"]
    assert (_keys(it)["ans"], _keys(it).get("rem")) == ("24", None)
    for a, b, want in (
        (516, 4, [(100, 400, 116), (20, 80, 36), (9, 36, 0)]),
        (457, 3, [(100, 300, 157), (50, 150, 7), (2, 6, 1)]),
        (804, 4, [(200, 800, 4), (1, 4, 0)]),
    ):
        assert _takes(a, b) == want
        it = DVM.make("CHUNKING", a, b, "R45")
        assert _steps(it) == [str(x) for take in want for x in take], (a, b)
        assert (_keys(it)["ans"], _keys(it).get("rem")) == (str(a // b), str(a % b) if a % b else None)
    for a, b in ((72, 4), (91, 7), (85, 4), (588, 3), (279, 3), (618, 6)):
        assert _steps(DVM.make("CHUNKING", a, b, "R45")) == [str(x) for t in _takes(a, b) for x in t], (a, b)


def test_short_division_writes_each_exchange_small():
    """In the division layout each remainder exchanged into the next digit is a small box of its own before that digit,
    keyed by the remainder: 72 ÷ 4 exchanges 3 into the ones; 588 ÷ 3, 2 into the tens and 1 into the ones; 156 ÷ 4,
    the 1 it could not divide into the tens, then 3 into the ones. A division with no exchange has none, and a division
    in a line writes none."""
    for a, b in ((72, 4), (588, 3), (156, 4), (84, 4), (804, 4), (85, 4), (457, 3)):
        it = verify.division(a, b, "R44", "column")
        got = [(r.rid, r.label, r.answer) for r in it.responses if r.rid.startswith("x")]
        want = [
            (f"x{k}", f"exchanged into the {PLACES[len(str(a)) - 1 - at]}", str(v))
            for k, (at, v) in enumerate(_exchanges(a, b), start=1)
        ]
        assert got == want, (a, b)
        assert it.spec.get("exchanged", []) == [at for at, _ in _exchanges(a, b)], (a, b)
        assert (_keys(it)["ans"], _keys(it).get("rem")) == (str(a // b), str(a % b) if a % b else None)
        assert not any(r.rid.startswith("x") for r in verify.division(a, b, "R44").responses), (a, b)
    assert [
        r.answer for r in verify.division(588, 3, "R45", "column").responses if r.rid.startswith("x")
    ] == ["2", "1"]


def test_long_division_divides_multiplies_takes_away_and_brings_down():
    """516 ÷ 4: 5 ÷ 4 = 1, 1 × 4 = 4 taken from 5 leaves 1, the 1 brought down makes 11; 2 × 4 = 8 taken from 11 leaves 3,
    the 6 brought down makes 36; 9 × 4 = 36 leaves 0. Each product a box, each number left with its digit brought down
    a box, the quotient on top; a first digit smaller than the divisor joins the next (279 ÷ 3 starts at 27)."""
    it = DVM.make("LONG_DIVISION", 516, 4, "R45")
    assert (it.fmt, it.spec["method"]) == ("long_division", "LONG_DIVISION")
    assert _steps(it) == ["4", "11", "8", "36", "36", "0"]
    assert (_keys(it)["ans"], _keys(it).get("rem")) == ("129", None)
    for a, b, want in (
        (457, 3, ["3", "15", "15", "7", "6", "1"]),
        (279, 3, ["27", "9", "9", "0"]),
        (804, 4, ["8", "0", "0", "4", "4", "0"]),
        (618, 6, ["6", "1", "0", "18", "18", "0"]),
    ):
        assert [str(x) for _, product, after in _cycles(a, b) for x in (product, after)] == want, (a, b)
        it = DVM.make("LONG_DIVISION", a, b, "R45")
        assert _steps(it) == want, (a, b)
        assert (_keys(it)["ans"], _keys(it).get("rem")) == (str(a // b), str(a % b) if a % b else None)


# ------------------------------------------------------------------------------- the mistakes, worked from the numbers


def test_a_quotients_zero_left_out_is_named_on_the_part_and_on_the_total():
    """40 ÷ 4 written 1 is the zero left out of the quotient (M_DIV_QUOTIENT_ZERO_DROPPED), and the total it makes
    (1 + 8 = 9 for 72 ÷ 4) is named the same; so are 20 lots of 4 written 2, and the lots added as 2 + 4 = 6."""
    it = DVM.make("PARTITION_DIVIDEND", 72, 4, "R44")
    assert _box(it, "s1").misconceptions["M_DIV_QUOTIENT_ZERO_DROPPED"] == 1
    assert _box(it, "ans").misconceptions["M_DIV_QUOTIENT_ZERO_DROPPED"] == 9
    it = DVM.make("CHUNKING", 96, 4, "R44")
    assert _box(it, "s1").misconceptions["M_DIV_QUOTIENT_ZERO_DROPPED"] == 2
    assert _box(it, "ans").misconceptions["M_DIV_QUOTIENT_ZERO_DROPPED"] == 6


def test_one_group_short_is_named_where_the_lots_are_chosen():
    """A long division's product one group short (2 × 4 written as 1 × 4 = 4) leaves too much to take away, as a
    remainder not less than the divisor does (M_DIV_REMAINDER_TOO_BIG); so does chunking's lots one of its place short
    (20 lots of 4 written 10)."""
    it = DVM.make("LONG_DIVISION", 516, 4, "R45")
    assert _box(it, "s3").misconceptions["M_DIV_REMAINDER_TOO_BIG"] == 4
    assert _box(it, "s5").misconceptions["M_DIV_REMAINDER_TOO_BIG"] == 32
    it = DVM.make("CHUNKING", 96, 4, "R44")
    assert _box(it, "s1").misconceptions["M_DIV_REMAINDER_TOO_BIG"] == 10
    assert _box(it, "s4").misconceptions["M_DIV_REMAINDER_TOO_BIG"] == 3


def test_an_exchange_names_its_own_divisions_remainder_slips():
    """72 ÷ 4's exchange is 7 ÷ 4's remainder: the 7 carried whole, nothing divided, is one group short
    (M_DIV_REMAINDER_TOO_BIG, 7); its quotient written in its place is the two swapped (M_DIV_SWAPPED, 1)."""
    x1 = _box(verify.division(72, 4, "R44", "column"), "x1")
    assert x1.misconceptions == {"M_DIV_REMAINDER_TOO_BIG": 7, "M_DIV_SWAPPED": 1}


def test_a_digit_not_brought_down_is_named():
    """516 ÷ 4's 11 written 1 and its 36 written 3 leave a digit where it was (M_DIV_BRING_DOWN_MISSED); the last number
    left has nothing to bring down."""
    it = DVM.make("LONG_DIVISION", 516, 4, "R45")
    assert _box(it, "s2").misconceptions["M_DIV_BRING_DOWN_MISSED"] == 1
    assert _box(it, "s4").misconceptions["M_DIV_BRING_DOWN_MISSED"] == 3
    assert "M_DIV_BRING_DOWN_MISSED" not in _box(it, "s6").misconceptions


def test_a_step_that_multiplies_or_takes_away_names_its_slips_and_counts_against_that_operation():
    """A product is a small multiplication and a number left a small subtraction: each names that operation's own slips
    (2 × 4 one row out in the table; 11 − 8 taken smaller from larger, 17, then the 6 brought down, 176), never "the
    wrong operation", whose name on a division is the division's. A wrong step showing a slip counts against the
    operation it is made in (assumption A11): long division and chunking multiply and take away, and use both.
    Partitioning's answers, and chunking's lots, are tens and ones put together, which never carries: neither uses
    addition."""
    it = DVM.make("LONG_DIVISION", 516, 4, "R45")
    assert "M_MUL_ROW_OUT" in _box(it, "s3").misconceptions
    assert _box(it, "s4").misconceptions["M_SMALL_FROM_LARGE"] == 176
    assert not any("M_WRONG_OP" in r.misconceptions for r in it.responses if r.rid not in ("ans", "rem"))
    for method, a, b, ops in (
        ("LONG_DIVISION", 516, 4, ["NUM.OPS.04", "NUM.OPS.03", "NUM.OPS.02"]),
        ("CHUNKING", 516, 4, ["NUM.OPS.04", "NUM.OPS.03", "NUM.OPS.02"]),
        ("PARTITION_DIVIDEND", 72, 4, ["NUM.OPS.04"]),
    ):
        it = DVM.make(method, a, b, "R45")
        assert skills.used(it.fmt, it.spec, it.stem, ["NUM.OPS.04"], RULES) == ops, method
    it = DVM.make("LONG_DIVISION", 516, 4, "R45")
    used = skills.used(it.fmt, it.spec, it.stem, ["NUM.OPS.04"], RULES)
    codes = ["M_SMALL_FROM_LARGE", "M_FACT_PM1", "M_MUL_ROW_OUT", "M_DIV_BRING_DOWN_MISSED"]
    assert skills.charges(it.fmt, it.spec, it.stem, used, codes, VOCAB, RULES) == {
        "M_SMALL_FROM_LARGE": "NUM.OPS.02",
        "M_FACT_PM1": "NUM.OPS.02",
        "M_MUL_ROW_OUT": "NUM.OPS.03",
        "M_DIV_BRING_DOWN_MISSED": "NUM.OPS.04",
    }


# ------------------------------------------------------------------------------- printed, read and marked


def _all_methods():
    return [
        DVM.make("PARTITION_DIVIDEND", 72, 4, "R44"),
        DVM.make("PARTITION_DIVIDEND", 85, 4, "R44"),
        DVM.make("CHUNKING", 96, 4, "R44"),
        DVM.make("CHUNKING", 457, 3, "R45"),
        DVM.make("LONG_DIVISION", 516, 4, "R45"),
        DVM.make("LONG_DIVISION", 279, 3, "R45"),
        verify.division(588, 3, "R45", "column"),
        verify.division(85, 4, "R44", "column"),
    ]


def test_every_step_is_where_the_printed_key_says_it_is(tmp_path):
    """A sheet of every method, printed through Chromium as a paper is: the key's geometry holds each box, as many as
    its key has digits — the quotient in the division layout one over every digit of the number divided — so the reader
    finds every one, an exchange's among them."""
    its = _all_methods()
    key = render.render_sheet(Sheet("CS00D3D0", "G4", "Easy", 1, "W1", its), tmp_path)
    boxes = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    for it in its:
        for r in it.responses:
            want = len(str(it.spec["a"])) if (it.fmt == LAYOUT and r.rid == "ans") else len(r.answer)
            assert boxes[(it.item_id, r.rid)] == want, (it.fmt, it.spec["a"], r.rid)


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def test_every_step_is_marked_against_its_own_key():
    """Each box marked by itself: its own key is right, and each wrong value predicted for it names its mistake."""
    for it in _all_methods():
        for r in it.responses:
            stored = {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}
            assert marking.mark(it.spec, stored, _wrote(r.answer))[0] == "correct", (it.fmt, r.rid)
            for code, wrong in r.misconceptions.items():
                status, codes, _ = marking.mark(it.spec, stored, _wrote(str(wrong)))
                assert status == "wrong" and code in codes, (it.fmt, r.rid, code, wrong)


def test_a_division_layout_printed_before_its_exchanges_were_read_leaves_the_bank():
    """A division stored in its layout before its exchanges had boxes cannot read 72 ÷ 4's 3: a key problem, so the
    refill retires it and draws another. Printed with its boxes it is a question of its own, so the one retired never
    stops the bank drawing 72 ÷ 4 again. One with nothing to exchange (84 ÷ 4) is the question it was."""
    it = verify.division(72, 4, "R44", "column")
    today = [dataclasses.asdict(r) for r in it.responses]
    assert stale.key_problems(it.fmt, it.spec, today) == []
    old = {k: v for k, v in it.spec.items() if k != "exchanged"}
    before = [r for r in today if not r["rid"].startswith("x")]
    assert stale.key_problems(it.fmt, old, before) == ["printed before its exchanges had boxes: x1"]
    assert item(it.template, "R44", it.signal, it.fmt, "", old, []).item_id != it.item_id
    plain = verify.division(84, 4, "R44", "column")
    assert "exchanged" not in plain.spec
    assert stale.key_problems(plain.fmt, plain.spec, [dataclasses.asdict(r) for r in plain.responses]) == []


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_a_level_filled_before_it_listed_methods_is_topped_up_in_each(conn):
    """A level the bank filled when it printed a case only in a line and in the division layout holds none of a method
    it lists since, as live's does: topped up to the size it is, each method gets its share of the case, and a second
    top-up adds nothing. (A question once in the bank, even retired, is never drawn again: DIV.3D1D's Easy has numbers
    to spare.)"""
    from engine.w1_bank import refill

    def held():
        rows = conn.execute(
            "select tags ->> 'method' as m from item where status = 'active' and skill_set_code = 'DIV.3D1D'"
            " and difficulty = 'Easy'"
        )
        return Counter(r["m"] for r in rows)

    conn.execute(
        "update item set status = 'retired' where skill_set_code = 'DIV.3D1D' and difficulty = 'Easy'"
        " and tags ->> 'method' in ('CHUNKING', 'LONG_DIVISION')"
    )
    before = held()
    assert set(before) <= {"LINE", "SHORT_DIVISION"}, before
    size = sum(before.values())
    assert refill.top_up(conn, "DIV.3D1D", "Easy", size) > 0
    after = held()
    methods = [CASES[m]["match"]["method"] for m in _check("DIV.3D1D", "Easy")["methods"]]
    assert all(after[m] >= k for m, k in zip(methods, draw.split(size, len(methods)), strict=True)), after
    assert refill.top_up(conn, "DIV.3D1D", "Easy", size) == 0


def test_a_written_division_keyed_by_a_rule_since_changed_leaves_the_bank():
    """A stored written division whose box names a slip today's rules no longer give, or leaves out one they now name,
    is a key problem: the refill retires it and draws another, never changing a printed key in place."""
    for method, a, b in (("PARTITION_DIVIDEND", 72, 4), ("CHUNKING", 516, 4), ("LONG_DIVISION", 457, 3)):
        it = DVM.make(method, a, b, "R45")
        today = [dataclasses.asdict(r) for r in it.responses]
        assert stale.key_problems(it.fmt, it.spec, today) == [], method
        moved = [today[0] | {"misconceptions": {**today[0]["misconceptions"], "M_ONE_ADDED": -1}}, *today[1:]]
        assert stale.key_problems(it.fmt, it.spec, moved) == [
            "keyed by a mistake rule since corrected: M_ONE_ADDED"
        ], method


def test_a_written_division_that_cannot_set_out_its_numbers_is_refused_and_never_drawn():
    """Partitioning needs tens of lots and a rest (35 ÷ 4 has no ten lots, 80 ÷ 4 no rest); every written division here
    divides by one digit, never by 0 or 1. Asked for one it cannot set out, a method says so, as every kind refuses numbers
    it cannot use, and the drawer passes those numbers over."""
    for method, a, b in (
        ("PARTITION_DIVIDEND", 35, 4),
        ("PARTITION_DIVIDEND", 80, 4),
        ("CHUNKING", 84, 0),
        ("LONG_DIVISION", 84, 1),
        ("LONG_DIVISION", 408, 12),
        ("HALVING", 96, 4),
    ):
        with pytest.raises(O.CannotMake):
            DVM.make(method, a, b, "R44")
    drawn = [it for _, it in _drawn("DIV.2D1D", "Hard", 24) if it.spec.get("method") == "PARTITION_DIVIDEND"]
    assert drawn and all(it.spec["a"] // it.spec["b"] >= 10 for it in drawn)


def test_a_written_division_is_placed_where_its_calculation_in_a_line_is():
    """Placed as a child's answer is placed (`assess/placing.py`), a written division lands where the same numbers in a
    line land: its own skill, at a straight level. Advance is for the kinds that are not a calculation."""
    sets, matches = list(SETS.values()), {c: x["match"] for c, x in CASES.items()}
    placed = 0
    for skill in SKILLS:
        for level in STRAIGHT:
            for _, it in _drawn(skill, level, 24):
                if it.fmt not in DVM.KINDS.values():
                    continue
                line = Item(
                    "x", "x", it.rung, [], "P", "bare_sum", False, "", {**it.spec, "layout": "horizontal"}, []
                )
                home = placing.place(it.fmt, tags.derive(it), sets, matches)
                as_line = placing.place("bare_sum", tags.derive(line), sets, matches)
                assert home and home[0]["code"] == skill and home[1] in STRAIGHT, (
                    skill,
                    level,
                    it.fmt,
                    it.spec,
                )
                assert (home[0]["code"], home[1]) == (as_line[0]["code"], as_line[1]), (it.fmt, it.spec)
                placed += 1
    assert placed >= 60, placed


def test_every_mistake_the_methods_name_is_a_row_and_on_its_skills_list():
    """The methods' mistakes are rows of the vocabulary and on the lists of the skills whose questions name them."""
    rows = {code for code, _ in VOCAB}
    for skill in SKILLS:
        named = set()
        for level in STRAIGHT:
            check = _check(skill, level)
            n = len(check["cases"]) * len(check["methods"]) * 2
            named |= {c for _, it in _drawn(skill, level, n) for r in it.responses for c in r.misconceptions}
        assert named <= rows, (skill, named - rows)
        assert named <= set(SETS[skill]["misconception_codes"]), (
            skill,
            named - set(SETS[skill]["misconception_codes"]),
        )


def test_the_document_prints_a_division_in_a_line_and_halving_is_mental_maths_alone():
    """Corrected at the source (`research/md_rows.py`, `research/md_taxonomy.py`): every column skill prints in a line
    (A2), so DIV.3D1D has D15 as DIV.2D1D has D02; chunking takes the lots of each place, so a 3-digit division is three
    takes at most, not one for every ten lots (588 ÷ 3 would have been nineteen); and halving, which A1 does not list as
    a written method, is MD.MENTAL's alone, as doubling is — one home, never two."""
    d15 = CASES["D15"]["match"]
    assert (d15["method"], d15["operand_1_digits"], d15["operand_2_digits"]) == ("LINE", 3, 1), d15
    assert DOC["D15"]["placed_in"] == ["DIV.3D1D:method"], DOC["D15"]["placed_in"]
    assert DOC["D02"]["placed_in"] == ["DIV.2D1D:method"], DOC["D02"]["placed_in"]
    # beside doubling at Grade 2, as the school's objective has them (LO-G2-0498, goals/md4a-mental-methods.yaml)
    assert DOC["G25"]["placed_in"] == ["MD.MENTAL:Easy"], DOC["G25"]["placed_in"]
    assert DOC["G06"]["placed_in"] == ["MD.MENTAL:Easy"], DOC["G06"]["placed_in"]
    assert {CASES[c]["match"]["fmt"] for c in ("G21", "G22", "G24")} == {
        "partitioning",
        "chunking",
        "long_division",
    }
    assert "take 20 × 4, take 4 × 4" in DOC["G22"]["example"], DOC["G22"]
    assert max(len(_takes(a, b)) for a in range(100, 1000) for b in range(2, 10) if a // b >= 100) == 3
