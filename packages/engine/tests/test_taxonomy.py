"""The team's taxonomy, case by case (step 8e onward).

A case is a combination of tags. These tests hold the three things that make the count trustworthy: the
tags measure what the document means (402 − 185 crosses one zero, 1000 − 476 two); every case accepts the
document's own example; and cases the document keeps apart — in columns or in a line, a carry from the
ones or from the tens, the box first or second — are kept apart here too.
"""

import json
import os
import pathlib

import pytest

from engine.assess import tags, taxonomy
from engine.assess.items import Item
from engine.core import db
from engine.w1_bank import cases

SEED = json.loads(
    (pathlib.Path(__file__).resolve().parents[3] / "supabase/seed/taxonomy_cases.json").read_text()
)
CASES = {c["code"]: c for c in SEED["taxonomy_cases"]}


def measure(fmt, spec, rung="R9"):
    return tags.derive(Item("x", "x", rung, [], "P", fmt, False, "", spec, []))


def two(op, a, b, layout="column"):
    return measure(
        "column_grid" if layout == "column" else "bare_sum", {"a": a, "b": b, "op": op, "layout": layout}
    )


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
    assert (line["presentation"], line["operand_order"], line["alignment_required"]) == (
        "HORIZONTAL",
        "MIXED",
        "YES",
    )


def test_tags_a_missing_number_says_which_number_the_box_hides():
    first = measure("missing_number", {"text": "□ + 5 = 12", "a": 7, "b": 5, "op": "+", "missing": "a"})
    assert (first["unknown_position"], first["unknown_digits"]) == ("FIRST_OPERAND", 1)
    read = measure("missing_number", {"text": "□ − 275 = 418"})
    assert (read["operation"], read["unknown_position"], read["unknown_digits"]) == (
        "SUB",
        "FIRST_OPERAND",
        3,
    )


def test_tags_a_missing_digit_says_where_the_box_is_and_what_the_numbers_do():
    t = measure("missing_digit", {"a": "□7", "b": "25", "c": "62", "op": "+", "solved": {"a": 37, "b": 25}})
    assert (t["missing_count"], t["missing_place"], t["missing_in"], t["regrouping"]) == (
        1,
        "TENS",
        "FIRST",
        "SINGLE",
    )


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
        assert not taxonomy.matches(CASES[b]["match"], ex["fmt"], measure(ex["fmt"], ex["spec"])), (
            f"{a}'s example is also {b}"
        )


def test_matches_reads_lists_ranges_and_alternatives():
    t = {"operation": "ADD", "digits_max": 4}
    assert taxonomy.matches({"operation": ["ADD", "SUB"], "digits_max": {"gte": 4}}, "bare_sum", t)
    assert not taxonomy.matches({"digits_max": {"lte": 3}}, "bare_sum", t)
    assert taxonomy.matches([{"fmt": "column_grid"}, {"fmt": "bare_sum"}], "bare_sum", t)
    assert not taxonomy.matches({"regroup_at": "ONES"}, "bare_sum", t)  # a tag it does not carry fails


@pytest.fixture
def conn():
    # CI has no database: the tests that need one skip there, the pure ones above still run
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_count_reports_every_case_with_its_state(conn):
    rows = cases.count(conn)
    assert len(rows) == len(CASES)
    assert {r["state"] for r in rows} <= {"covered", "thin", "missing"}
    assert all(r["n"] >= r["min_items"] for r in rows if r["state"] == "covered")


# ---------------------------------------------------------------- 8f: a level made of cases


def test_level_draws_the_same_number_from_each_case_and_every_question_is_its_case():
    import random

    from engine.assess import draw

    check = {"cases": ["A19", "A21", "S20", "S21"]}
    got = draw.level(random.Random(3), check, {c: CASES[c]["match"] for c in check["cases"]}, "R9", 40)
    assert len(got) == 40
    per = {c: [it for code, it in got if code == c] for c in check["cases"]}
    assert {c: len(v) for c, v in per.items()} == {c: 10 for c in check["cases"]}
    for code, it in got:
        assert taxonomy.matches(CASES[code]["match"], it.fmt, tags.derive(it)), (code, it.spec)


def test_level_a_case_that_does_not_fix_the_layout_prints_half_in_columns_half_in_a_line():
    import random

    from engine.assess import draw

    got = draw.level(random.Random(5), {"cases": ["P02"]}, {"P02": CASES["P02"]["match"]}, "R9", 20)
    layouts = [it.fmt for _, it in got]
    assert layouts.count("column_grid") == layouts.count("bare_sum") == 10


def test_level_keeps_inside_its_bounds_and_away_from_round_numbers_unless_the_case_is_about_zeros():
    import random

    from engine.assess import draw

    got = draw.level(
        random.Random(9),
        {"cases": ["A01", "A03"], "max_total": 5},
        {c: CASES[c]["match"] for c in ("A01", "A03")},
        "R1",
        12,
    )
    assert got and all(it.spec["a"] + it.spec["b"] <= 5 for _, it in got)
    tens = draw.level(random.Random(9), {"cases": ["A19"]}, {"A19": CASES["A19"]["match"]}, "R5", 60)
    assert all(it.spec["a"] % 10 and it.spec["b"] % 10 for _, it in tens)
    zeros = draw.level(random.Random(9), {"cases": ["SZ6"]}, {"SZ6": CASES["SZ6"]["match"]}, "R10", 12)
    assert len(zeros) == 12  # 1000 − 476 needs a round top number, and the case is about zeros


def test_level_with_quotas_draws_each_case_its_own_shortfall_and_spills_only_what_the_level_needs():
    import random

    from engine.assess import draw

    matches = {c: CASES[c]["match"] for c in ("S01", "S03")}
    # 7 − 7 has only so many; the level already holds its target, so nothing spills onto S01
    full = draw.level(
        random.Random(4), {"cases": ["S01", "S03"]}, matches, "R2", 0, quotas={"S01": 0, "S03": 30}
    )
    assert full and {code for code, _ in full} == {"S03"} and len(full) < 30
    # the level is 10 short: S01 gets its 5, S03 all it has, and nothing is thrown away to make 10
    short = draw.level(
        random.Random(4), {"cases": ["S01", "S03"]}, matches, "R2", 10, quotas={"S01": 5, "S03": 30}
    )
    per = {c: sum(code == c for code, _ in short) for c in ("S01", "S03")}
    assert per == {"S01": 5, "S03": len(full)}


def test_top_up_a_second_time_adds_nothing_when_a_case_has_run_out(conn):
    from engine.w1_bank import refill

    before = conn.execute("select difficulty from skill_set where code = 'SUB.3D.ZERO'").fetchone()[
        "difficulty"
    ]
    # 507 − 8 has hundreds of numbers left; 7 − 7 has nine, all already in the bank
    level = {"words": before["Easy"]["words"], "check": {"cases": ["S20", "S03"]}}
    conn.execute(
        "update skill_set set difficulty = %s where code = 'SUB.3D.ZERO'",
        (json.dumps(dict(before, Easy=level)),),
    )
    total = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = 'SUB.3D.ZERO'"
        " and difficulty = 'Easy'"
    ).fetchone()["n"]
    first = refill.top_up(conn, "SUB.3D.ZERO", "Easy", total + 40)
    assert first >= 40
    assert refill.top_up(conn, "SUB.3D.ZERO", "Easy", total + 40) == 0


def test_fill_cases_fills_a_level_evenly_and_says_which_case_made_each_question(conn):
    from engine.w1_bank import refill

    before = conn.execute("select difficulty from skill_set where code = 'ADD.2D.REG'").fetchone()[
        "difficulty"
    ]
    level = dict(before["Easy"], check={"cases": ["A10", "A11", "A12", "A13"]})
    conn.execute(
        "update skill_set set difficulty = %s where code = 'ADD.2D.REG'",
        (json.dumps(dict(before, Easy=level)),),
    )
    counts, per_case, items = refill.fill_cases(conn, "ADD.2D.REG", "Easy", 20)
    assert counts["accepted"] == 20 and per_case == {"A10": 5, "A11": 5, "A12": 5, "A13": 5}
    stored = conn.execute(
        "select generator, fmt, tags, skill_codes from item where item_key = any(%s)",
        ([it.item_id for it in items],),
    ).fetchall()
    assert len(stored) == 20
    for r in stored:
        assert taxonomy.matches(CASES[r["generator"][5:]]["match"], r["fmt"], r["tags"])
        assert list(r["skill_codes"]) == ["NUM.OPS.01"]
