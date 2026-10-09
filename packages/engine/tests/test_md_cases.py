"""The multiplication and division taxonomy as rows the bank is counted against (goals/md1-taxonomy-rows.yaml).

The addition and subtraction document became rows a case at a time (test_taxonomy.py): a case is a combination of
tags, code measures the tags, and a case holds its own example. These hold the second document to the same three
things, and add what two documents need: a question is a case of the taxonomy of its own operations only, and every
tag a case reads is a dimension row naming its values.
"""

import itertools
import json
import os
import pathlib

import pytest
from typer.testing import CliRunner

from engine.assess import operations as O
from engine.assess import tags, taxonomy
from engine.assess.items import Item
from engine.core import db
from engine.w1_bank import cases

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = json.loads((ROOT / "supabase/seed/taxonomy_cases.json").read_text())["taxonomy_cases"]
DOC = json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
DIMENSIONS = {
    d["name"]: d
    for d in json.loads((ROOT / "supabase/seed/case_dimensions.json").read_text())["case_dimensions"]
}
ALL = {c["code"]: c for c in SEED}
MD = {code: c for code, c in ALL.items() if c.get("taxonomy") == "MUL_DIV"}


def measure(fmt, spec, rung="R9"):
    return tags.derive(Item("x", "x", rung, [], "P", fmt, False, "", spec, []))


def holds(case, example):
    return taxonomy.matches(case["match"], example["fmt"], measure(example["fmt"], example["spec"]))


def two(op, a, b, layout="horizontal"):
    return measure(
        "column_grid" if layout == "column" else "bare_sum", {"a": a, "b": b, "op": op, "layout": layout}
    )


# ---------------------------------------------------------------------------------------------- the document


def test_every_case_of_the_drafted_document_is_a_row_as_drafted():
    """The 247 cases the engine drafted for Achal, each a row with the document's own words and example, and every
    straight calculation's answer recomputed here from the row's own numbers, not read from the document."""
    assert sorted(MD) == sorted(c["code"] for c in DOC) and len(MD) == 247
    computed = 0
    for d in DOC:
        row = MD[d["code"]]
        assert (row["section"], row["label"], row["example_text"]) == (
            str(d["section"]),
            d["label"],
            d["example"],
        )
        assert row["section_name"], d["code"]
        sp = row["example"]["spec"]
        if row["example"]["fmt"] in ("bare_sum", "column_grid") and "method" not in sp:
            q, r = (
                O.divide(sp["a"], sp["b"])
                if O.sign(sp["op"]) == "÷"
                else (O.compute(sp["op"], sp["a"], sp["b"]), 0)
            )
            assert d["answer"] == (f"{q} r {r}" if r else str(q)), d["code"]
            computed += 1
    assert computed >= 100, f"only {computed} answers recomputed"


@pytest.mark.parametrize(
    "op,a,b,layout,key,want",
    [
        # the fact: its table is the first number, its group the easiest table holding it within ten rows
        ("×", 7, 8, "horizontal", "fact_table", 7),
        ("×", 8, 3, "horizontal", "fact_group", "3-4"),
        ("×", 8, 3, "horizontal", "fact_swapped", "YES"),
        ("×", 3, 8, "horizontal", "fact_swapped", "NO"),
        ("×", 7, 0, "horizontal", "fact_group", "0-1"),
        ("×", 45, 10, "horizontal", "fact", "NO"),
        ("÷", 56, 7, "horizontal", "fact_table", 7),
        ("÷", 144, 12, "horizontal", "fact", "YES"),
        ("÷", 91, 7, "horizontal", "fact", "NO"),
        # place value: a power of ten, or round numbers whose fact is a table fact
        ("×", 45, 100, "horizontal", "place_value_factor", "X100"),
        ("×", 30, 4, "horizontal", "place_value_factor", "MULTIPLE_OF_TEN_ONE"),
        ("×", 300, 6, "horizontal", "place_value_factor", "MULTIPLE_OF_HUNDRED_ONE"),
        ("×", 20, 40, "horizontal", "place_value_factor", "MULTIPLE_OF_TEN_BOTH"),
        ("×", 30, 4, "horizontal", "scaled_fact", "YES"),
        ("×", 230, 4, "horizontal", "scaled_fact", "NO"),
        ("×", 50, 4, "horizontal", "fact_zero", "YES"),
        ("×", 30, 4, "horizontal", "fact_zero", "NO"),
        ("÷", 4500, 100, "horizontal", "place_value_factor", "X100"),
        ("÷", 200, 4, "horizontal", "fact_zero", "YES"),
        ("÷", 120, 4, "horizontal", "fact_zero", "NO"),
        ("÷", 840, 4, "horizontal", "scaled_fact", "NO"),
        # a 1-digit multiplier, column by column from the ones
        ("×", 56, 3, "column", "regroup_at", "ONES"),
        ("×", 23, 3, "column", "regrouping", "NONE"),
        ("×", 357, 4, "column", "regroup_at", "ONES+TENS"),
        ("×", 13, 4, "column", "carry_size", "ONE"),
        ("×", 19, 5, "column", "carry_size", "MORE_THAN_ONE"),
        ("×", 18, 6, "column", "knock_on", "YES"),
        ("×", 56, 3, "column", "knock_on", "NO"),
        ("×", 506, 7, "column", "carry_into_zero", "YES"),
        ("×", 302, 3, "column", "carry_into_zero", "NO"),
        ("×", 3, 21, "horizontal", "regrouping", "NONE"),
        ("×", 42, 3, "column", "answer_digit_change", "FULL"),
        ("×", 23, 3, "column", "answer_digit_change", "ONE_FEWER"),
        ("×", 230, 4, "column", "zero_pattern", "TRAILING"),
        ("×", 302, 3, "column", "zero_pattern", "INTERNAL"),
        ("×", 1008, 6, "column", "zero_pattern", "MULTIPLE"),
        ("×", 25, 4, "column", "zero_pattern", "ANSWER_ZERO"),
        ("×", 125, 8, "column", "answer_round", "YES"),
        ("×", 18, 6, "column", "answer_round", "NO"),
        # a 2-digit multiplier: a row per digit, and the rows added
        ("×", 21, 13, "column", "row_regrouping", "NONE"),
        ("×", 16, 12, "column", "row_regrouping", "SOME"),
        ("×", 36, 24, "column", "row_regrouping", "ALL"),
        ("×", 47, 23, "column", "partial_sum_regrouping", "SINGLE"),
        ("×", 52, 34, "column", "partial_sum_regrouping", "NONE"),
        ("×", 23, 40, "column", "partial_products", 1),
        ("×", 213, 102, "column", "partial_products", 2),
        ("×", 23, 40, "column", "multiplier_zero", "TRAILING"),
        ("×", 213, 102, "column", "multiplier_zero", "INTERNAL"),
        # short division, left to right
        ("÷", 72, 4, "column", "regroup_at", "TENS"),
        ("÷", 588, 3, "column", "regroup_at", "HUNDREDS+TENS"),
        ("÷", 936, 3, "column", "regrouping", "NONE"),
        ("÷", 279, 3, "column", "first_digit_smaller", "YES"),
        ("÷", 279, 3, "column", "answer_digit_change", "ONE_FEWER"),
        ("÷", 804, 4, "column", "quotient_zero", "MIDDLE"),
        ("÷", 840, 4, "column", "quotient_zero", "END"),
        ("÷", 8016, 8, "column", "quotient_zero", "MULTIPLE"),
        ("÷", 702, 6, "column", "quotient_zero", "NONE"),
        ("÷", 91, 7, "column", "divisor_group", "6-9"),
        ("÷", 72, 4, "column", "divisor_group", "3-4"),
        ("÷", 702, 6, "column", "zero_pattern", "INTERNAL"),
        ("÷", 84, 4, "column", "remainder", "NONE"),
        ("÷", 17, 5, "column", "remainder", "SOME"),
        ("÷", 47, 6, "column", "remainder", "LARGEST"),
        ("÷", 3, 5, "column", "remainder", "DIVIDEND_SMALLER"),
        ("÷", 162, 18, "column", "estimate_corrected", "YES"),
        ("÷", 84, 21, "column", "estimate_corrected", "NO"),
        ("÷", 84, 12, "column", "estimate_corrected", "YES"),  # 12 to 10 suggests 8; 8 × 12 = 96 is too big
        # how it is laid out, and the method a layout is
        ("×", 34, 6, "column", "method", "COLUMNS"),
        ("×", 34, 26, "column", "method", "LONG_MULTIPLICATION"),
        ("×", 34, 26, "horizontal", "method", "LINE"),
        ("÷", 72, 4, "column", "method", "SHORT_DIVISION"),
        ("÷", 408, 12, "column", "method", "LONG_DIVISION"),
        ("÷", 7, 7, "horizontal", "equal_operands", "YES"),
        ("÷", 8, 1, "horizontal", "one_operand", "SECOND"),
        ("÷", 0, 5, "horizontal", "zero_operand", "FIRST"),
    ],
)
def test_tags_measure_what_the_document_means_for_times_and_divide(op, a, b, layout, key, want):
    t = two(op, a, b, layout)
    assert t[key] == want, (op, a, b, key, t.get(key))
    assert t["operation"] == O.NAMES[O.sign(op)] and t["taxonomy"] == "MUL_DIV"


def test_a_missing_number_or_digit_in_a_times_or_divide_says_where_it_is():
    first = measure("missing_number", {"text": "□ × 6 = 42"})
    assert (first["operation"], first["unknown_position"], first["unknown_digits"]) == (
        "MUL",
        "FIRST_OPERAND",
        1,
    )
    divisor = measure("missing_number", {"text": "56 ÷ □ = 8"})
    assert (divisor["operation"], divisor["unknown_position"]) == ("DIV", "SECOND_OPERAND")
    left = measure("missing_number", {"text": "38 ÷ 5 = 7 r □"})
    assert (left["operation"], left["unknown_position"], left["remainder"]) == ("DIV", "REMAINDER", "SOME")
    factor = measure("missing_number", {"text": "45 × □ = 4500"})
    assert (factor["unknown_position"], factor["place_value_factor"]) == ("SECOND_OPERAND", "X100")
    digit = measure("missing_digit", {"a": "2□", "b": "4", "c": "92", "op": "×", "solved": {"a": 23, "b": 4}})
    assert (digit["operation"], digit["missing_place"], digit["missing_in"]) == ("MUL", "ONES", "FIRST")


# ---------------------------------------------------------------------------------------------- the cases


def _straight_questions():
    """Every straight × and ÷ a school paper prints up to four digits, in a line and in columns: the questions two
    cases are compared on. Thinned where the numbers run past a thousand, never where a case's property sits."""
    sums = [(a, b) for a in range(1000) for b in range(13)]
    sums += [(a, b) for a in range(10, 100) for b in range(10, 100)]
    sums += [(a, b) for a in range(100, 1000, 7) for b in range(10, 100, 3)]
    sums += [(a, b) for a in range(1000, 10000, 37) for b in range(2, 10)]
    sums += [(a, b) for a in range(10, 1000, 10) for b in (10, 20, 30, 40, 50, 100, 1000)]
    sums += [(a, b) for a in range(1, 1000) for b in (100, 1000)]
    sums += [(a, b) for a in range(10000, 100000, 997) for b in range(2, 10)]
    sums += [(a, b) for a in range(100, 1000, 37) for b in range(100, 1000, 37)]
    divs = [(a, b) for a in range(1000) for b in range(1, 13)]
    divs += [(a, b) for a in range(1000, 10000, 13) for b in range(2, 10)]
    divs += [(a, b) for a in range(100, 10000, 10) for b in (10, 20, 40, 100, 1000)]
    divs += [(a, b) for a in range(100, 1000, 7) for b in range(11, 25)]
    for op, pairs in (("×", sums), ("÷", divs)):
        for a, b in pairs:
            for layout in ("horizontal", "column"):
                yield (
                    "column_grid" if layout == "column" else "bare_sum",
                    {"a": a, "b": b, "op": op, "layout": layout},
                )
    for c in MD.values():
        yield c["example"]["fmt"], c["example"]["spec"]


def test_every_case_holds_its_own_example_and_no_two_hold_the_same_questions():
    """A case is its example's case. Two cases holding exactly the same questions are one case written twice, so
    the count would credit every question to both: a fault in the document, fixed by sharpening one of them. Read
    on every straight question a paper prints, not on the two examples alone — two cases about different things
    (a method and a carry) may each hold the other's example and still be two cases."""
    for code, c in ALL.items():
        assert holds(c, c["example"]), f"{code} does not hold its own example {c['example_text']}"
    straight = {code: c for code, c in MD.items() if c["match"].get("fmt") == ["bare_sum", "column_grid"]}
    read = {}
    for fmt, spec in _straight_questions():
        t = measure(fmt, spec)
        read.setdefault(json.dumps(t, sort_keys=True, default=str), (fmt, t))
    held = {
        code: frozenset(k for k, (fmt, t) in read.items() if taxonomy.matches(c["match"], fmt, t))
        for code, c in straight.items()
    }
    assert all(held.values()), [code for code, h in held.items() if not h]
    twice = [(x, y) for x, y in itertools.combinations(sorted(held), 2) if held[x] == held[y]]
    assert twice == [], f"{len(twice)} pairs of cases hold the same questions: {twice}"
    matches = [json.dumps(c["match"], sort_keys=True) for c in MD.values()]
    assert len(set(matches)) == len(matches), "two cases with one match"


def test_every_method_the_document_names_is_a_case_its_tag_measures():
    """Every method the school's objectives name, and the standard ones, is a value of `method`, and a case whose
    example prints that way and holds only questions printed that way."""
    methods = DIMENSIONS["method"]["allowed"]
    assert len(methods) >= 20
    for m in methods:
        mine = [c for c in MD.values() if _fixes(c["match"], "method", m)]
        assert mine, f"no case is about the method {m}"
        for c in mine:
            assert measure(c["example"]["fmt"], c["example"]["spec"])["method"] == m, c["code"]
    grid = {"a": 34, "b": 26, "op": "×", "layout": "column", "method": "GRID"}
    assert measure("column_grid", grid)["method"] == "GRID"
    assert not any(holds(MD[c], {"fmt": "column_grid", "spec": grid}) for c in ("T19", "T22")), (
        "a grid is not the straight calculation in columns or in a line"
    )


def _fixes(match, key, value):
    return any(m.get(key) == value for m in (match if isinstance(match, list) else [match]))


def test_a_question_is_a_case_of_its_own_operations_taxonomy_only():
    """A × odd-or-even question is not R06; an addition word problem is no story about sharing. The tag is read from
    the question's own operations (`skills.operations`), so a story that multiplies then adds is multiplication's."""
    for code, c in ALL.items():
        mine = c.get("taxonomy", "ADD_SUB")
        other = [
            o for o, oc in ALL.items() if oc.get("taxonomy", "ADD_SUB") != mine and holds(oc, c["example"])
        ]
        assert other == [], f"{code}'s example is also {other}"
    odd = measure("odd_even", {"a": 7, "b": 9, "op": "×"})
    assert odd["taxonomy"] == "MUL_DIV" and not holds(
        ALL["R06"], {"fmt": "odd_even", "spec": {"a": 7, "b": 9, "op": "×"}}
    )
    assert measure("odd_even", {"a": 7, "b": 9, "op": "+"})["taxonomy"] == "ADD_SUB"
    assert measure("word_2step", {"a": 3, "b": 12, "c": 5, "ops": ["×", "+"]})["taxonomy"] == "MUL_DIV"
    assert (
        measure("equation", {"text": "6 □ 3 = 18", "shape": "MISSING_SIGN", "ops": ["×", "÷"]})["taxonomy"]
        == "MUL_DIV"
    )
    assert all(c.get("taxonomy") in ("ADD_SUB", "MUL_DIV") for c in SEED)
    for c in SEED:
        for m in c["match"] if isinstance(c["match"], list) else [c["match"]]:
            assert m.get("taxonomy") == c["taxonomy"], f"{c['code']} does not name its own taxonomy"


def test_every_tag_a_case_reads_is_a_dimension_row_with_its_values():
    """The dimension rows are the words every case is written in, for both documents: a case reading a tag no row
    names, or a value its row does not allow, is caught here rather than matching nothing for ever."""
    for c in SEED:
        for m in c["match"] if isinstance(c["match"], list) else [c["match"]]:
            for key, want in m.items():
                if key == "fmt":
                    continue
                assert key in DIMENSIONS, f"{c['code']} reads {key}, which no dimension row names"
                allowed = {str(v) for v in DIMENSIONS[key]["allowed"]}
                values = want if isinstance(want, list) else [want]
                for v in values:
                    if isinstance(v, dict):
                        assert all(str(n) in allowed for n in v.values()), (c["code"], key, v)
                    else:
                        assert str(v) in allowed, f"{c['code']}: {key}={v} is not a value its row allows"


# ---------------------------------------------------------------------------------------------- the count


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_engine_bank_taxonomy_counts_every_case_of_both_taxonomies(conn):
    rows = cases.count(conn)
    assert sorted(r["code"] for r in rows) == sorted(ALL)
    assert {r["code"]: r["taxonomy"] for r in rows} == {code: c["taxonomy"] for code, c in ALL.items()}
    from engine import cli

    out = CliRunner().invoke(cli.app, ["bank", "taxonomy", "--show", "none"])
    assert out.exit_code == 0, out.output
    for name, n in (("ADD_SUB", len(ALL) - len(MD)), ("MUL_DIV", len(MD))):
        assert f"{name}: {n} cases" in out.output, out.output
