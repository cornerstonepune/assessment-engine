"""The month build (task M1-16, brick 1; D-072: the list goes out once every class's has been made). One command builds
every class's list for the month and then the school's, and says which classes it is short of: a class with no plan to
build from, and a class whose plan asks for no materials. Without it the school list sums only the classes whose
educator happened to tap Build, and says nothing about the rest. Placeholder rows made in the test's transaction. Written
before the code."""

import datetime as dt
import os

import pytest

from engine.core import db
from engine.w2_print import materials_consolidate as mc
from engine.w2_print import materials_inventory as inv
from engine.w2_print import materials_list as ml
from engine.w2_print import materials_month as mm
from tests import materials_rows as m

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

LO, HI = m.MON, m.MON + dt.timedelta(days=27)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _planned_class(conn, s, section, activity, qty):
    """A class with one session of `activity` on the first Monday, whose activity asks for `qty` clay."""
    klass = m.another_class(conn, s, section)
    clay = s.get("clay") or m.item(conn, s, "Clay", "packet")
    s["clay"] = clay
    m.needs(conn, s, activity, clay, qty)
    m.planned(conn, s, LO, activity, klass=klass)
    return klass


def test_every_class_with_a_plan_gets_a_list_and_the_school_list_sums_them(conn):
    s = m.school(conn)
    one = _planned_class(conn, s, "T-one", s["acts"][0], 2)
    two = _planned_class(conn, s, "T-two", s["acts"][1], 3)
    got = mm.build_month(conn, s["tenant"], LO, HI)
    assert {r["class_id"] for r in got["built"]} == {one, two}
    [line] = [x for x in mc.read(conn, got["consolidated_id"])["lines"] if x["material_code"] == s["clay"]]
    assert line["quantity"] == 5


def test_a_class_with_no_plan_is_named_and_gets_no_list(conn):
    s = m.school(conn)
    planned = _planned_class(conn, s, "T-one", s["acts"][0], 2)
    bare = m.another_class(conn, s, "T-bare")
    got = mm.build_month(conn, s["tenant"], LO, HI)
    assert [r["class_id"] for r in got["no_plan"]] == [bare, s["class"]] or {
        r["class_id"] for r in got["no_plan"]
    } == {bare, s["class"]}
    assert {r["class_id"] for r in got["built"]} == {planned}
    assert (
        conn.execute(
            "select count(*) as n from materials_list where school_class_id = %s", (bare,)
        ).fetchone()["n"]
        == 0
    )
    assert all(r["class"] for r in got["no_plan"])  # named, so a person can read it


def test_a_class_whose_plan_asks_for_no_materials_is_named_as_such(conn):
    s = m.school(conn)
    _planned_class(conn, s, "T-one", s["acts"][0], 2)
    dry = m.another_class(conn, s, "T-dry")
    m.planned(conn, s, LO, s["acts"][2], klass=dry)  # an activity that needs nothing
    got = mm.build_month(conn, s["tenant"], LO, HI)
    assert [r["class_id"] for r in got["no_materials"]] == [dry]


def test_a_class_of_a_grade_with_no_activities_is_not_expected_to_have_a_plan(conn):
    s = m.school(conn)
    _planned_class(conn, s, "T-one", s["acts"][0], 2)
    other = m.another_class(conn, s, "T-other", grade="G10")
    got = mm.build_month(conn, s["tenant"], LO, HI)
    assert other not in {r["class_id"] for r in got["no_plan"]}


def test_building_the_month_again_with_nothing_changed_changes_nothing(conn):
    s = m.school(conn)
    _planned_class(conn, s, "T-one", s["acts"][0], 2)
    first = mm.build_month(conn, s["tenant"], LO, HI)
    lists = conn.execute("select count(*) as n from materials_list").fetchone()["n"]
    second = mm.build_month(conn, s["tenant"], LO, HI)
    assert second["consolidated_id"] == first["consolidated_id"]
    assert (
        mc.read(conn, second["consolidated_id"])["build"]
        == mc.read(conn, first["consolidated_id"])["build"]
        == 1
    )
    assert conn.execute("select count(*) as n from materials_list").fetchone()["n"] == lists


def test_the_text_sent_to_the_inventory_person_names_the_classes_not_in_the_list_it_was_built_from(conn):
    s = m.school(conn)
    _planned_class(conn, s, "T-one", s["acts"][0], 2)
    m.another_class(conn, s, "T-bare")
    got = mm.build_month(conn, s["tenant"], LO, HI)
    out = inv.send(conn, got["consolidated_id"], s["staff"])
    note = [ln for ln in out["text"].splitlines() if ln.startswith("Not included")]
    assert len(note) == 1 and "T-bare" in note[0] and "nothing from them" in note[0]
    assert "T-one" not in note[0]


def test_the_footer_matches_the_lines_even_if_a_plan_changes_after_the_build(conn):
    s = m.school(conn)
    _planned_class(conn, s, "T-one", s["acts"][0], 2)
    late = m.another_class(conn, s, "T-late")
    got = mm.build_month(conn, s["tenant"], LO, HI)
    m.needs(conn, s, s["acts"][1], s["clay"], 4)
    m.planned(conn, s, LO, s["acts"][1], klass=late)  # a plan appears after the build, and is not rebuilt
    note = [
        ln
        for ln in inv.send(conn, got["consolidated_id"], s["staff"])["text"].splitlines()
        if ln.startswith("Not included")
    ]
    assert len(note) == 1 and "T-late" in note[0]  # still not in the lines above it


def test_a_month_with_no_class_short_has_no_not_included_line(conn):
    s = m.school(conn)
    m.needs(conn, s, s["acts"][0], m.item(conn, s, "Clay", "packet"), 2)
    m.planned(conn, s, LO, s["acts"][0])
    got = mm.build_month(conn, s["tenant"], LO, HI)
    assert not [
        ln
        for ln in inv.send(conn, got["consolidated_id"], s["staff"])["text"].splitlines()
        if ln.startswith("Not included")
    ]
    assert ml.read  # the class's own list was made by the month build, not by the test


def test_sessions_on_days_no_fortnight_covers_are_named_for_that_and_not_as_a_dry_plan(conn):
    s = m.school(conn)
    _planned_class(conn, s, "T-one", s["acts"][0], 2)
    stray = m.another_class(conn, s, "T-stray")
    m.needs(conn, s, s["acts"][1], s["clay"], 1)
    m.planned(
        conn, s, m.MON + dt.timedelta(days=20), s["acts"][1], klass=stray
    )  # fortnight 910 ends on day 13
    got = mm.build_month(conn, s["tenant"], LO, HI)
    assert [r["class_id"] for r in got["no_fortnight"]] == [stray]
    assert stray not in {r["class_id"] for r in got["no_materials"]}


def test_a_range_wider_than_a_month_is_refused_before_anything_is_built(conn):
    s = m.school(conn)
    _planned_class(conn, s, "T-one", s["acts"][0], 2)
    with pytest.raises(ValueError, match="one month"):
        mm.build_month(conn, s["tenant"], LO, LO + dt.timedelta(days=400))
    assert (
        conn.execute(
            "select count(*) as n from materials_list where school_class_id <> %s", (s["class"],)
        ).fetchone()["n"]
        == 0
    )
