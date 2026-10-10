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


@pytest.mark.parametrize("kinds", [["equal_groups"], ["tally", "equal_groups"], KINDS])
def test_a_small_levels_worksheets_all_differ(kinds):
    """A level of 13 to 40 questions has more different worksheets than the ten it is dealt, so no two are alike:
    the rehearsal of update-live dealt MUL.GROUPS Medium's 16 questions onto two worksheets the same (2026-10-10),
    and 16 questions dealt onto ten worksheets of twelve repeated one in 6 levels of 300."""
    for n in range(13, 41):
        for prefix in ("K", "EG", "T", "Q", "X"):
            questions = [
                {"id": f"q{i:03d}", "item_key": f"{prefix}-{i:03d}", "fmt": kinds[i % len(kinds)]}
                for i in range(n)
            ]
            sheets = library.deal(questions, 12, kinds, library.worksheets_needed(n, 12))
            assert len({frozenset(q["id"] for q in s) for s in sheets}) == len(sheets), (n, prefix)
            counts = uses(sheets)
            assert len(counts) == n and max(counts.values()) - min(counts.values()) <= 1, (n, prefix)


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


def test_a_patched_worksheet_takes_each_kind_in_its_fair_share():
    """The worksheet a patch makes is filled kind by kind. Filled by use and key alone, its filler came from whichever
    kind's keys sort first (a key starts with its kind's template): on ADD.2D2D's Advance, 221 questions on 19
    worksheets, a retired worksheet holding the level's seven repeated questions left five uncovered, seven of one kind
    filled the rest, and the unfair patch made one reworded story re-deal the whole level."""
    mix = {
        "bare_sum": 34,
        "column_grid": 34,
        "estimate_then_calc": 17,
        "find_mistake": 34,
        "missing_number": 34,
    }
    mix["word_1step"] = 68
    questions = [
        {"id": f"{k}{i}", "item_key": f"{k}-{i:03d}", "fmt": k} for k, m in mix.items() for i in range(m)
    ]
    share, fmt_of = Counter(mix), {q["id"]: q["fmt"] for q in questions}
    uncovered = [
        q for q in questions if q["id"] in {"word_1step0", "find_mistake0", "missing_number0", "word_1step1"}
    ]
    uncovered.append(questions[-1])
    used = Counter({q["id"]: 1 for q in questions if q not in uncovered})
    used.update(q["id"] for q in questions[100:107])  # the seven on two worksheets
    sheet = library.deal(
        uncovered + library._filler(questions, used, uncovered, share, 12), 12, list(mix), 1
    )[0]
    assert len({q["id"] for q in sheet}) == 12 and all(q in sheet for q in uncovered)
    assert not library._unfair([q["id"] for q in sheet], fmt_of, share, len(questions), 12), Counter(
        q["fmt"] for q in sheet
    )
    assert all(used[q["id"]] == 1 for q in sheet if q not in uncovered)  # the least used, as before


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
def test_a_level_with_too_few_questions_for_one_worksheet_is_refused_never_passed_as_empty(conn):
    """Nimish, 2026-09-23: "Everything should have something." A level is on the tree; one with no questions was
    needing no worksheets and so passed the check, and showed a teacher an empty level."""
    library.build(conn)
    conn.execute(
        "update item set status = 'retired' where skill_set_code = 'SUB.2D2D' and difficulty = 'Hard'"
    )
    library.build(conn)
    problems = library.check(conn)[1]
    assert problems["SUB.2D2D Hard"][0].startswith("holds 0 questions, too few for one worksheet")


@needs_db
def test_two_worksheets_alike_are_made_different_by_building_again(conn):
    """What `check` refuses, `build` repairs: a level holding two worksheets of the same questions keeps the first,
    retires the other (never edits it) and is dealt what it lacks."""
    library.build(conn)
    first, second = _unit(conn, "MUL.GROUPS", "Medium")[:2]
    conn.execute("update sheet_template set item_ids = %s where id = %s", (first["item_ids"], second["id"]))
    assert "two worksheets hold the same questions" in library.check(conn)[1]["MUL.GROUPS Medium"]
    assert library.build(conn)["retired"] >= 1
    after = _unit(conn, "MUL.GROUPS", "Medium")
    assert first["code"] in {s["code"] for s in after} and second["code"] not in {s["code"] for s in after}
    assert library.check(conn)[1] == {}


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


def _six_sums(conn):
    """A library worksheet of six sums of its own — the bank need not be on the copy — and its code."""
    import dataclasses
    import json
    import random

    from engine.assess import items

    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    rung = conn.execute("select code from rung order by code limit 1").fetchone()["code"]  # any: layout only
    rng, ids = random.Random(7), []
    made = [items.bare_sum(rng, "R5", "Procedural", "+", 2, 2, [0, 1]) for _ in range(40)]
    for q in [q for q in made if len(q.responses[0].answer) == 2][:6]:
        ids.append(conn.execute(
            "insert into item (tenant_id, item_key, template, rung_code, signal, fmt, stem, spec, responses)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
            (tenant, f"T-{q.item_id}", q.template, rung, q.signal, "bare_sum", q.stem or "", json.dumps(q.spec),
             json.dumps([dataclasses.asdict(r) for r in q.responses])),
        ).fetchone()["id"])  # fmt: skip
    code = "R5-T01"
    conn.execute(
        "insert into sheet_template (tenant_id, band, week, variant, source, code, skill_set_code, difficulty,"
        " item_ids) values (%s, 'G2', 'library', 98, 'library', %s, 'ADD.2D2D', 'Easy', %s)",
        (tenant, code, ids),
    )
    return code


@needs_db
def test_a_worksheet_prints_in_every_layout_the_school_has_printed_and_today_s_by_default(
    conn, tmp_path, monkeypatch
):
    """A 23 Sep copy of a worksheet printed three boxes an answer; today the same worksheet prints two. Both are
    drawn, each where only its own layout is kept, so one is never served as the other (goals/s18)."""
    import json

    monkeypatch.setattr(library, "PDF_DIR", tmp_path)
    code = _six_sums(conn)
    names = [x["name"] for x in library.layouts(conn)]
    printed = library.printed(conn, code)
    assert list(printed) == names[::-1] and library.pdf(conn, code) == printed[names[-1]]

    def boxes_for_first_answer(pdf):
        cells = json.loads(pdf.with_suffix(".key.json").read_text())["geometry"]
        first = next(c["item"] for c in cells if c.get("kind") != "work")
        return sum(1 for c in cells if c["item"] == first and c.get("kind") != "work")

    assert boxes_for_first_answer(printed["2026-09-21"]) == 3
    assert boxes_for_first_answer(printed[names[-1]]) == 2


def _printed_as(conn, code, d):
    return conn.execute(
        "select id, band from sheet_template where source = 'library' and retired_at is null"
        " and skill_set_code = %s and difficulty = %s",
        (code, d),
    ).fetchall()


@needs_db
def test_a_worksheet_prints_at_its_levels_grade_and_one_printed_at_another_is_replaced(conn):
    """Nimish, 2026-10-06: "Can we incorporate this part additionally for grade 1?" 2-digit + 2-digit with no carry is
    Grade 1 work now, so its worksheets print as Grade 1's — "Grade 1" on the page, Grade 1's bigger boxes — while its
    harder levels stay Grade 2's. A worksheet printed for the grade its level was in before is retired and a new one
    dealt, never edited."""
    library.build(conn)
    easy = _printed_as(conn, "ADD.2D2D", "Easy")
    assert easy and {s["band"] for s in easy} == {"G1"}
    assert {s["band"] for s in _printed_as(conn, "ADD.2D2D", "Hard")} == {"G2"}
    conn.execute("update skill_set set level_band = '{}'::jsonb where code = 'ADD.2D2D'")
    library.build(conn)
    again = _printed_as(conn, "ADD.2D2D", "Easy")
    assert {s["band"] for s in again} == {"G2"}
    assert not {s["id"] for s in easy} & {s["id"] for s in again}
