"""The school's consolidated materials list for a month (goals/m1-16-materials-consolidated.yaml; task M1-16; D-074:
"the system collates requirements from all the teachers"). Built by code from every class's list (M1-10), summed per
catalogue item, each line showing where it comes from, every later change shown as a change. Placeholder rows made in the
test's own transaction and rolled back. Written before the code: these fail until `materials_consolidate` exists."""

import datetime as dt
import os

import pytest

from engine.core import db
from engine.w2_print import materials_consolidate as mc
from engine.w2_print import materials_list as ml
from tests import materials_rows as m

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

LO, HI = m.MON, m.MON + dt.timedelta(days=27)  # a month of four weeks


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _second_class(conn, s):
    return conn.execute(
        "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
        " select tenant_id, campus_id, academic_year_id, 'K2', 'T-two' from school_class where id = %s returning id",
        (s["class"],),
    ).fetchone()["id"]


def _two_classes_needing_clay(conn, s):
    """Class one needs 2 packets of clay on Monday (activity a); class two needs 3 on Tuesday (activity b)."""
    a, b = s["acts"][:2]
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, a, clay, 2)
    m.needs(conn, s, b, clay, 3)
    two = _second_class(conn, s)
    m.planned(conn, s, LO, a)
    m.planned(conn, s, LO + dt.timedelta(days=1), b, klass=two)
    one_list = ml.build(conn, s["class"], "fortnight", LO, HI)
    two_list = ml.build(conn, two, "fortnight", LO, HI)
    return clay, two, one_list, two_list


def test_two_classes_needing_one_item_make_one_line_with_the_total_and_where_it_comes_from(conn):
    s = m.school(conn)
    clay, two, _, _ = _two_classes_needing_clay(conn, s)
    got = mc.read(conn, mc.build(conn, s["tenant"], LO, HI))
    [line] = [x for x in got["lines"] if x["material_code"] == clay]
    assert (line["quantity"], line["unit"]) == (5, "packet")
    assert {(f["class_id"], tuple(f["activity_codes"]), f["quantity"]) for f in line["from"]} == {
        (s["class"], (s["acts"][0],), 2),
        (two, (s["acts"][1],), 3),
    }


def test_a_class_that_gives_no_quantity_makes_the_total_unknown_not_a_smaller_number(conn):
    s = m.school(conn)
    a, b = s["acts"][:2]
    glue = m.item(conn, s, "Glue", "bottle")
    m.needs(conn, s, a, glue, 2)
    m.needs(conn, s, b, glue, None)
    two = _second_class(conn, s)
    m.planned(conn, s, LO, a)
    m.planned(conn, s, LO, b, klass=two)
    ml.build(conn, s["class"], "fortnight", LO, HI)
    ml.build(conn, two, "fortnight", LO, HI)
    [line] = [
        x for x in mc.read(conn, mc.build(conn, s["tenant"], LO, HI))["lines"] if x["material_code"] == glue
    ]
    assert line["quantity"] is None and line["to_confirm"] is True


def test_a_removed_line_and_a_day_outside_the_month_are_not_in_the_list(conn):
    s = m.school(conn)
    a, b = s["acts"][:2]
    tape, chalk = m.item(conn, s, "Tape"), m.item(conn, s, "Chalk")
    m.needs(conn, s, a, tape, 1)
    m.needs(conn, s, b, chalk, 1)
    m.planned(conn, s, LO, a)
    m.planned(conn, s, HI + dt.timedelta(days=10), b)
    lid = ml.build(conn, s["class"], "fortnight", LO, HI + dt.timedelta(days=14))
    [line] = [ln for g in ml.read(conn, lid)["groups"] for ln in g["lines"] if ln["material_code"] == tape]
    ml.remove(conn, line["line_id"], s["staff"])
    codes = {x["material_code"] for x in mc.read(conn, mc.build(conn, s["tenant"], LO, HI))["lines"]}
    assert tape not in codes and chalk not in codes


def test_a_change_an_educator_makes_after_the_build_is_shown_as_a_change(conn):
    s = m.school(conn)
    clay, two, one_list, _ = _two_classes_needing_clay(conn, s)
    cid = mc.build(conn, s["tenant"], LO, HI)
    assert mc.read(conn, cid)["changes"] == []
    [line] = [ln for g in ml.read(conn, one_list)["groups"] for ln in g["lines"]]
    ml.set_quantity(conn, line["line_id"], 4, s["staff"])  # class one now needs 4, not 2
    again = mc.read(conn, mc.build(conn, s["tenant"], LO, HI))
    [change] = again["changes"]
    assert (change["kind"], change["material_code"], change["before"], change["after"]) == (
        "quantity",
        clay,
        5,
        7,
    )
    assert [x["quantity"] for x in again["lines"] if x["material_code"] == clay] == [7]
    # building again with nothing new makes no new build: the change stays the latest, until something else moves
    assert mc.read(conn, mc.build(conn, s["tenant"], LO, HI))["build"] == again["build"]


def test_a_class_dropping_its_need_after_the_build_lowers_the_total_and_shows_as_a_change(conn):
    s = m.school(conn)
    clay, two, one_list, two_list = _two_classes_needing_clay(conn, s)
    mc.build(conn, s["tenant"], LO, HI)
    [line] = [ln for g in ml.read(conn, two_list)["groups"] for ln in g["lines"]]
    ml.remove(conn, line["line_id"], s["staff"])
    [change] = mc.read(conn, mc.build(conn, s["tenant"], LO, HI))["changes"]
    assert (change["kind"], change["material_code"], change["before"], change["after"]) == (
        "quantity",
        clay,
        5,
        2,
    )


def test_a_week_list_inside_a_fortnight_list_of_the_same_class_is_not_counted_twice(conn):
    s = m.school(conn)
    a = s["acts"][0]
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, a, clay, 2)
    m.planned(conn, s, LO, a)
    fortnight = ml.build(conn, s["class"], "fortnight", LO, LO + dt.timedelta(days=13))
    week = ml.build(conn, s["class"], "week", LO, LO + dt.timedelta(days=6))
    got = mc.read(conn, mc.build(conn, s["tenant"], LO, HI))
    [line] = [x for x in got["lines"] if x["material_code"] == clay]
    assert line["quantity"] == 2  # not 4
    assert got["skipped_lists"] == [week] and fortnight not in got["skipped_lists"]


def test_a_class_with_two_lists_in_the_month_has_them_added_not_one_over_the_other(conn):
    s = m.school(conn)
    a, b = s["acts"][:2]
    pen = m.item(conn, s, "Pen", "piece")
    m.needs(conn, s, a, pen, 10)
    m.needs(conn, s, b, pen, 5)
    m.planned(conn, s, LO, a)
    m.planned(conn, s, LO + dt.timedelta(days=14), b)
    ml.build(conn, s["class"], "week", LO, LO + dt.timedelta(days=6))
    ml.build(conn, s["class"], "week", LO + dt.timedelta(days=14), LO + dt.timedelta(days=20))
    cid = mc.build(conn, s["tenant"], LO, HI)
    [line] = [x for x in mc.read(conn, cid)["lines"] if x["material_code"] == pen]
    assert line["quantity"] == 15
    # an identical rebuild is seen as identical even with two activities in a line
    assert mc.build(conn, s["tenant"], LO, HI) == cid and mc.read(conn, cid)["build"] == 1
    [from_] = line["from"]
    assert from_["quantity"] == 15 and sorted(from_["activity_codes"]) == sorted([a, b])


def test_the_lists_skipped_are_the_ones_skipped_when_it_was_built_not_when_it_is_read(conn):
    s = m.school(conn)
    a = s["acts"][0]
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, a, clay, 2)
    m.planned(conn, s, LO, a)
    ml.build(conn, s["class"], "fortnight", LO, LO + dt.timedelta(days=13))
    cid = mc.build(conn, s["tenant"], LO, HI)
    ml.build(conn, s["class"], "week", LO, LO + dt.timedelta(days=6))  # made after the build
    assert mc.read(conn, cid)["skipped_lists"] == []


def test_building_again_with_nothing_changed_adds_no_build_and_no_rows(conn):
    s = m.school(conn)
    _two_classes_needing_clay(conn, s)
    cid = mc.build(conn, s["tenant"], LO, HI)
    counts = lambda: [  # noqa: E731
        conn.execute(f"select count(*) as n from {t} where consolidated_id = %s", (cid,)).fetchone()["n"]
        for t in (
            "materials_consolidated_line",
            "materials_consolidated_source",
            "materials_consolidated_change",
        )
    ]
    before = counts()
    assert mc.build(conn, s["tenant"], LO, HI) == cid
    assert mc.read(conn, cid)["build"] == 1 and counts() == before
