"""Every question in the bank on a numbered worksheet (ADR 0026, goals/s3-worksheet-library.yaml).

The deal is pure and tested on made-up levels of the sizes the bank really holds; building, checking
and retiring run on the local copy of the database in a transaction that is rolled back.
"""

import os
from collections import Counter

import pytest

from engine.core import db
from engine.w2_print import library

KINDS = ["bare_sum", "column_grid", "missing_number", "word_1step"]


def level(n, kinds=KINDS):
    return [{"id": f"q{i:03d}", "item_key": f"K-{i:03d}", "fmt": kinds[i % len(kinds)]} for i in range(n)]


def uses(sheets):
    return Counter(q["id"] for s in sheets for q in s)


def test_216_questions_make_18_worksheets_and_no_question_is_on_two():
    sheets = library.deal(level(216), 12, KINDS, library.worksheets_needed(216, 12))
    assert len(sheets) == 18
    assert all(len(s) == 12 for s in sheets)
    assert set(uses(sheets).values()) == {1}


def test_145_questions_make_13_worksheets_each_question_used_once_or_twice():
    sheets = library.deal(level(145), 12, KINDS, library.worksheets_needed(145, 12))
    assert len(sheets) == 13
    assert len(uses(sheets)) == 145 and set(uses(sheets).values()) <= {1, 2}


def test_a_grade_1_level_of_24_makes_10_worksheets_each_question_used_five_times():
    sheets = library.deal(level(24), 12, KINDS, library.worksheets_needed(24, 12))
    assert len(sheets) == 10
    assert set(uses(sheets).values()) == {5}


@pytest.mark.parametrize("n", [22, 24, 35, 40, 43, 44, 45, 54, 80, 107, 145, 216])
def test_every_worksheet_holds_twelve_different_questions_and_use_is_even(n):
    sheets = library.deal(level(n), 12, KINDS, library.worksheets_needed(n, 12))
    assert len(sheets) >= 10
    assert all(len(s) == 12 and len({q["id"] for q in s}) == 12 for s in sheets)
    counts = uses(sheets)
    assert len(counts) == n, "every question is on a worksheet"
    assert max(counts.values()) - min(counts.values()) <= 1
    assert len({frozenset(q["id"] for q in s) for s in sheets}) == len(sheets), "no two worksheets alike"


def test_each_worksheet_holds_every_kind_in_its_fair_share():
    questions = (
        level(55, ["bare_sum"])
        + level(55, ["column_grid"])
        + level(53, ["missing_number"])
        + level(53, ["word_1step"])
    )
    for i, q in enumerate(questions):
        q["id"], q["item_key"] = f"q{i:03d}", f"K-{i:03d}"
    for s in library.deal(questions, 12, KINDS, 18):
        kinds = Counter(q["fmt"] for q in s)
        assert all(2 <= kinds[k] <= 4 for k in KINDS), kinds


def test_a_worksheet_prints_its_questions_grouped_by_kind_in_the_skills_own_order():
    order = ["word_1step", "bare_sum", "column_grid", "missing_number"]
    for s in library.deal(level(216), 12, order, 18):
        ranks = [order.index(q["fmt"]) for q in s]
        assert ranks == sorted(ranks)


def test_the_deal_is_the_same_every_time():
    a = library.deal(level(107), 12, KINDS, 10)
    b = library.deal(list(reversed(level(107))), 12, KINDS, 10)
    assert [[q["id"] for q in s] for s in a] == [[q["id"] for q in s] for s in b]


def test_a_level_too_small_for_one_worksheet_gets_none():
    assert library.worksheets_needed(11, 12) == 0


# ---------------------------------------------------------------- on the local copy

needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _unit(conn, code="SUB.2D2D", d="Hard"):
    return conn.execute(
        "select id, code, variant, item_ids from sheet_template where source = 'library'"
        " and skill_set_code = %s and difficulty = %s and retired_at is null order by variant",
        (code, d),
    ).fetchall()


@needs_db
def test_building_makes_every_level_ready_and_building_again_changes_nothing(conn):
    conn.execute("delete from sheet_template where source = 'library'")  # from nothing; rolled back after
    first = library.build(conn)
    levels = conn.execute("select count(*) as n from skill_set, jsonb_object_keys(difficulty)").fetchone()[
        "n"
    ]
    assert first["made"] >= levels * 10
    units, problems = library.check(conn)
    assert problems == {}
    assert units == levels
    assert library.build(conn) == {"made": 0, "retired": 0}


@needs_db
def test_a_removed_question_retires_its_worksheet_and_a_new_one_carries_the_rest(conn):
    library.build(conn)
    before = _unit(conn)
    sheet = before[3]
    gone = sheet["item_ids"][5]
    conn.execute("update item set status = 'retired' where id = %s", (gone,))
    assert library.build(conn) == {"made": 1, "retired": 1}
    after = _unit(conn)
    assert sheet["code"] not in {s["code"] for s in after}
    new = [s for s in after if s["code"] not in {b["code"] for b in before}]
    assert len(new) == 1 and gone not in new[0]["item_ids"]
    assert set(sheet["item_ids"]) - {gone} <= set(new[0]["item_ids"])
    assert library.check(conn)[1] == {}


@needs_db
def test_a_worksheet_already_printed_for_a_child_is_retired_never_changed(conn):
    library.build(conn)
    sheet = _unit(conn)[0]
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id) values (%s, 'CSTEST01', %s)",
        (tenant, sheet["id"]),
    )
    conn.execute("update item set status = 'retired' where id = %s", (sheet["item_ids"][0],))
    library.build(conn)
    kept = conn.execute(
        "select item_ids, retired_at from sheet_template where id = %s", (sheet["id"],)
    ).fetchone()
    assert kept["item_ids"] == sheet["item_ids"] and kept["retired_at"] is not None
