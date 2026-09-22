"""The team's taxonomy, case by case (step 8e onward).

A case is a combination of tags. These tests hold the three things that make the count trustworthy: the
tags measure what the document means (402 − 185 crosses one zero, 1000 − 476 two); every case accepts the
document's own example; and cases the document keeps apart — in columns or in a line, a carry from the
ones or from the tens, the box first or second — are kept apart here too.
"""

import json
import pathlib

import pytest

from engine import cases, db
from engine.assess import tags, taxonomy
from engine.assess.items import Item

SEED = json.loads((pathlib.Path(__file__).resolve().parents[3] / "supabase/seed/taxonomy_cases.json").read_text())
CASES = {c["code"]: c for c in SEED["taxonomy_cases"]}


def measure(fmt, spec, rung="R9"):
    return tags.derive(Item("x", "x", rung, [], "P", fmt, False, "", spec, []))


def two(op, a, b, layout="column"):
    return measure("column_grid" if layout == "column" else "bare_sum", {"a": a, "b": b, "op": op, "layout": layout})


@pytest.mark.parametrize(
    "op,a,b,key,want",
    [
        ("-", 402, 185, "exchange_zeros", 1),
        ("-", 1000, 476, "exchange_zeros", 2),
        ("-", 342, 7, "exchange_zeros", 0),
        ("+", 208, 96, "carry_into_zero", "YES"),
        ("+", 247, 315, "carry_into_zero", "NO"),
        ("-", 1000, 999, "answer_digit_change", "-MULTIPLE"),
        ("-", 44, 44, "answer_digit_change", "ZERO"),
        ("-", 13, 7, "answer_digit_change", "-1"),
        ("+", 96, 8, "answer_digit_change", "+1"),
        ("+", 495, 505, "answer_zeros", "TRAILING"),
        ("-", 705, 201, "answer_zeros", "INTERNAL"),
        ("-", 342, 148, "knock_on", "YES"),
        ("-", 742, 318, "knock_on", "NO"),
        ("+", 608, 715, "regroup_at", "ONES+HUNDREDS"),
        ("+", 61, 42, "regroup_at", "TENS"),
        ("+", 456, 0, "zero_operand", "SECOND"),
        ("+", 405, 302, "zeros_in", "BOTH"),
        ("+", 347, 100, "round_operand", "POWER_OF_TEN"),
        ("-", 503, 498, "difference_small", "YES"),
        ("+", 7, 342, "operand_order", "SHORTER_FIRST"),
    ],
)
def test_tags_measure_what_the_document_means(op, a, b, key, want):
    assert two(op, a, b)[key] == want


def test_tags_three_or_more_numbers_carry_the_largest_column_carry_and_their_lengths():
    t = measure("column_grid", {"addends": [9, 8, 7, 6], "op": "+", "layout": "column"})
    assert (t["carry_max"], t["num_operands"], t["digits_max"]) == (3, 4, 1)
    line = measure("bare_sum", {"addends": [345, 27, 6], "op": "+", "layout": "horizontal"})
    assert (line["presentation"], line["operand_order"], line["alignment_required"]) == ("HORIZONTAL", "MIXED", "YES")


def test_tags_a_missing_number_says_which_number_the_box_hides():
    first = measure("missing_number", {"text": "□ + 5 = 12", "a": 7, "b": 5, "op": "+", "missing": "a"})
    assert (first["unknown_position"], first["unknown_digits"]) == ("FIRST_OPERAND", 1)
    read = measure("missing_number", {"text": "□ − 275 = 418"})
    assert (read["operation"], read["unknown_position"], read["unknown_digits"]) == ("SUB", "FIRST_OPERAND", 3)


def test_tags_a_missing_digit_says_where_the_box_is_and_what_the_numbers_do():
    t = measure("missing_digit", {"a": "□7", "b": "25", "c": "62", "op": "+", "solved": {"a": 37, "b": 25}})
    assert (t["missing_count"], t["missing_place"], t["missing_in"], t["regrouping"]) == (1, "TENS", "FIRST", "SINGLE")


@pytest.mark.parametrize("code", sorted(CASES))
def test_every_case_accepts_the_documents_own_example(code):
    c = CASES[code]
    ex = c["example"]
    assert taxonomy.matches(c["match"], ex["fmt"], measure(ex["fmt"], ex["spec"])), c["example_text"]


@pytest.mark.parametrize(
    "one,other",
    [
        ("A01", "A03"),  # in columns, in a line
        ("A19", "A21"),  # a carry from the ones, from the tens
        ("A25", "A27"),  # the longer number first, the shorter first
        ("A33", "A35"),  # a ripple that stays 3 digits, one that makes a new digit
        ("A63", "A65"),  # a hundreds carry alone, the ones and tens
        ("S20", "S21"),  # an exchange from the tens, across a zero
        ("S42", "S43"),  # across one zero, across several
        ("S13", "S14"),  # the answer 1 digit, the answer zero
        ("M01", "M02"),  # the box second, the box first
        ("M22", "M23"),  # the number taken away missing, the first number missing
        ("W01", "W03"),  # the result unknown, the start unknown
        ("X03", "X04"),  # a forgotten carry, a carry in the wrong column
    ],
)
def test_twin_cases_the_document_keeps_apart_are_kept_apart(one, other):
    for a, b in ((one, other), (other, one)):
        ex = CASES[a]["example"]
        assert not taxonomy.matches(CASES[b]["match"], ex["fmt"], measure(ex["fmt"], ex["spec"])), f"{a}'s example is also {b}"


def test_matches_reads_lists_ranges_and_alternatives():
    t = {"operation": "ADD", "digits_max": 4}
    assert taxonomy.matches({"operation": ["ADD", "SUB"], "digits_max": {"gte": 4}}, "bare_sum", t)
    assert not taxonomy.matches({"digits_max": {"lte": 3}}, "bare_sum", t)
    assert taxonomy.matches([{"fmt": "column_grid"}, {"fmt": "bare_sum"}], "bare_sum", t)
    assert not taxonomy.matches({"regroup_at": "ONES"}, "bare_sum", t)  # a tag it does not carry fails


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_count_reports_every_case_with_its_state(conn):
    rows = cases.count(conn)
    assert len(rows) == len(CASES)
    assert {r["state"] for r in rows} <= {"covered", "thin", "missing"}
    assert all(r["n"] >= r["min_items"] for r in rows if r["state"] == "covered")
