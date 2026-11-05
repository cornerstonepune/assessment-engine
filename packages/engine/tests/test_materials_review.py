"""A waiting note cleared by a person, and the two things she can approve so the next note needs no one (task M1-16,
brick 2): a word that means a catalogue item (`material_alias`) and a unit that converts to the item's own
(`material_unit_conversion`). Clearing goes through `materials_list.add`, so a cleared note is a line like any other and
the note keeps who cleared it. Code never invents a conversion: only an approved row converts. Placeholder rows only,
rolled back."""

import os

import pytest

from engine.core import db
from engine.w2_print import materials_intake as mi
from engine.w2_print import materials_list as ml
from engine.w2_print import materials_review as rv
from tests import materials_rows as m

needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
CAT = [{"code": "MAT-1", "name": "Pen", "unit": "piece"}]


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _waiting(conn, s, lid, text="some pens", reason="the note gives no quantity"):
    return conn.execute(
        "insert into materials_note_review (tenant_id, list_id, text, reason, who) values (%s, %s, %s, %s, %s)"
        " returning id",
        (s["tenant"], lid, text, reason, s["staff"]),
    ).fetchone()["id"]


def _lines(conn, lid):
    return [(ln["material_code"], ln["quantity"]) for g in ml.read(conn, lid)["groups"] for ln in g["lines"]]


# ── the pure rule: an approved conversion is the only thing that lets a different unit be confirmed ──────────────────


def test_a_unit_that_is_not_the_catalogues_still_waits_when_no_conversion_is_approved():
    r = {"text": "2 dozen pens", "item_code": "MAT-1", "quantity": 2, "unit": "dozen"}
    got = mi.check_reading(r, CAT, "2 dozen pens")
    assert got.status == "needs_person" and "unit" in got.reason


def test_an_approved_conversion_makes_two_dozen_twenty_four_pieces():
    r = {"text": "2 dozen pens", "item_code": "MAT-1", "quantity": 2, "unit": "dozen"}
    got = mi.check_reading(r, CAT, "2 dozen pens", {("MAT-1", "dozen"): 12.0})
    assert (got.status, got.item_code, got.quantity, got.unit) == ("confirmed", "MAT-1", 24.0, "piece")


def test_a_conversion_for_another_item_or_unit_does_not_apply():
    r = {"text": "2 box pens", "item_code": "MAT-1", "quantity": 2, "unit": "box"}
    got = mi.check_reading(r, CAT, "2 box pens", {("MAT-1", "dozen"): 12.0, ("MAT-2", "box"): 10.0})
    assert got.status == "needs_person"


def test_a_conversion_applies_only_if_the_unit_is_in_the_notes_own_words():
    r = {
        "text": "2 pens",
        "item_code": "MAT-1",
        "quantity": 2,
        "unit": "dozen",
    }  # the model claimed a unit nobody wrote
    got = mi.check_reading(r, CAT, "2 pens", {("MAT-1", "dozen"): 12.0})
    assert got.status == "needs_person" and "unit" in got.reason
    r = {"text": "2 dozens pens", "item_code": "MAT-1", "quantity": 2, "unit": "dozen"}
    assert mi.check_reading(r, CAT, "2 dozens pens", {("MAT-1", "dozen"): 12.0}).quantity == 24.0
    r = {"text": "2 boxes of pens", "item_code": "MAT-1", "quantity": 2, "unit": "box"}
    assert mi.check_reading(r, CAT, "2 boxes of pens", {("MAT-1", "box"): 10.0}).quantity == 20.0


def test_a_converted_quantity_carries_no_float_noise():
    r = {"text": "0.7 dozen pens", "item_code": "MAT-1", "quantity": 0.7, "unit": "dozen"}
    assert mi.check_reading(r, CAT, "0.7 dozen pens", {("MAT-1", "dozen"): 12.0}).quantity == 8.4
    r = {"text": "3 tens", "item_code": "MAT-1", "quantity": 3, "unit": "ten"}
    assert mi.check_reading(r, CAT, "3 tens", {("MAT-1", "ten"): 0.1}).quantity == 0.3


def test_a_converted_number_must_still_be_in_the_notes_own_words():
    r = {"text": "dozen pens", "item_code": "MAT-1", "quantity": 1, "unit": "dozen"}
    got = mi.check_reading(r, CAT, "dozen pens", {("MAT-1", "dozen"): 12.0})
    assert got.status == "needs_person" and "number" in got.reason


# ── clearing a waiting note ───────────────────────────────────────────────────────────────────────────────────────────


@needs_db
def test_clearing_a_waiting_note_adds_the_line_and_closes_the_note(conn):
    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    nid = _waiting(conn, s, lid)
    rv.resolve(conn, s["tenant"], nid, pen, 30, m.MON, s["staff"])
    assert _lines(conn, lid) == [(pen, 30)]
    row = conn.execute("select * from materials_note_review where id = %s", (nid,)).fetchone()
    assert (row["state"], row["resolved_by"], row["resolved_code"]) == ("added", s["staff"], pen)
    added = conn.execute(
        "select after from materials_line_edit where list_id = %s and kind = 'add'", (lid,)
    ).fetchone()
    assert added["after"]["via"] == "note_review"  # told apart from a line code confirmed ("note")
    assert row["resolved_at"] is not None and float(row["resolved_quantity"]) == 30.0


@needs_db
def test_a_note_cleared_twice_adds_nothing_the_second_time(conn):
    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    nid = _waiting(conn, s, lid)
    rv.resolve(conn, s["tenant"], nid, pen, 30, m.MON, s["staff"])
    with pytest.raises(rv.NotWaiting):
        rv.resolve(conn, s["tenant"], nid, pen, 99, m.MON, s["staff"])
    assert _lines(conn, lid) == [(pen, 30)]


@needs_db
def test_an_item_already_on_the_list_keeps_the_note_waiting(conn):
    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    ml.add(conn, lid, pen, 5, m.MON, None, s["staff"])
    nid = _waiting(conn, s, lid)
    with pytest.raises(ml.AlreadyOnList):
        rv.resolve(conn, s["tenant"], nid, pen, 30, m.MON, s["staff"])
    assert conn.execute("select state from materials_note_review where id = %s", (nid,)).fetchone()[
        "state"
    ] == ("needs_person")
    assert _lines(conn, lid) == [(pen, 5)]


@needs_db
def test_an_item_not_in_the_catalogue_cannot_clear_a_note(conn):
    s = m.school(conn)
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    nid = _waiting(conn, s, lid)
    with pytest.raises(ml.NotInCatalogue):
        rv.resolve(conn, s["tenant"], nid, "MAT-9999", 3, m.MON, s["staff"])
    assert _lines(conn, lid) == []


@needs_db
def test_dismissing_a_note_closes_it_with_a_reason_and_adds_nothing(conn):
    s = m.school(conn)
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    nid = _waiting(conn, s, lid)
    with pytest.raises(ValueError):
        rv.dismiss(conn, s["tenant"], nid, "  ", s["staff"])
    rv.dismiss(conn, s["tenant"], nid, "not a material", s["staff"])
    row = conn.execute(
        "select state, resolved_by, why from materials_note_review where id = %s", (nid,)
    ).fetchone()
    assert (row["state"], row["resolved_by"], row["why"]) == ("dismissed", s["staff"], "not a material")
    assert _lines(conn, lid) == []


@needs_db
def test_a_note_of_another_school_cannot_be_cleared_or_set_aside(conn):
    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    nid = _waiting(conn, s, lid)
    other = conn.execute("select gen_random_uuid() as id").fetchone()["id"]
    with pytest.raises(rv.NoSuchNote):
        rv.resolve(conn, other, nid, pen, 3, m.MON, s["staff"])
    with pytest.raises(rv.NoSuchNote):
        rv.dismiss(conn, other, nid, "no", s["staff"])
    assert rv.waiting(conn, s["tenant"])[0]["id"] == nid


@needs_db
def test_waiting_lists_only_this_schools_open_notes_oldest_first(conn):
    s = m.school(conn)
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    a, b = _waiting(conn, s, lid, "first"), _waiting(conn, s, lid, "second")
    rv.dismiss(conn, s["tenant"], a, "no", s["staff"])
    assert [w["text"] for w in rv.waiting(conn, s["tenant"])] == ["second"]
    assert [w["id"] for w in rv.waiting(conn, s["tenant"])] == [b]


# ── aliases and conversions are approved by a person, then used ───────────────────────────────────────────────────────


@needs_db
def test_an_approved_alias_is_given_to_the_model_with_its_item(conn):
    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    rv.approve_alias(conn, s["tenant"], "  Ball Pen ", pen, s["staff"])
    rv.approve_alias(conn, s["tenant"], "ball pen", pen, s["staff"])  # the same word again is the same row
    got = {c["code"]: c for c in mi.catalogue(conn, s["tenant"])}
    assert got[pen]["aliases"] == ["ball pen"]
    assert (
        conn.execute(
            "select count(*) as n from material_alias where tenant_id = %s", (s["tenant"],)
        ).fetchone()["n"]
        == 1
    )


@needs_db
def test_an_alias_cannot_point_at_two_items(conn):
    s = m.school(conn)
    pen, pencil = m.item(conn, s, "Pen", "piece"), m.item(conn, s, "Pencil", "piece")
    rv.approve_alias(conn, s["tenant"], "writer", pen, s["staff"])
    with pytest.raises(rv.AliasTaken):
        rv.approve_alias(conn, s["tenant"], "Writer", pencil, s["staff"])


@needs_db
def test_an_alias_for_an_item_not_in_the_catalogue_is_refused(conn):
    s = m.school(conn)
    with pytest.raises(ml.NotInCatalogue):
        rv.approve_alias(conn, s["tenant"], "writer", "MAT-9999", s["staff"])


@needs_db
def test_an_approved_conversion_is_read_back_and_an_unapproved_unit_is_not(conn):
    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    rv.approve_conversion(conn, s["tenant"], pen, " Dozen ", 12, s["staff"])
    assert mi.conversions(conn, s["tenant"]) == {(pen, "dozen"): 12.0}
    for bad in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            rv.approve_conversion(conn, s["tenant"], pen, "box", bad, s["staff"])
    with pytest.raises(ValueError):
        rv.approve_conversion(
            conn, s["tenant"], pen, "piece", 1, s["staff"]
        )  # the item's own unit needs none


@needs_db
def test_changing_a_conversion_keeps_the_old_one_and_the_latest_is_used(conn):
    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    rv.approve_conversion(conn, s["tenant"], pen, "dozen", 12, s["staff"])
    rv.approve_conversion(conn, s["tenant"], pen, "Dozen", 12, s["staff"])  # the same again adds nothing
    rv.approve_conversion(conn, s["tenant"], pen, "dozen", 10, s["staff"])
    assert mi.conversions(conn, s["tenant"]) == {(pen, "dozen"): 10.0}
    rows = conn.execute("select factor from material_unit_conversion order by approved_at").fetchall()
    assert [float(r["factor"]) for r in rows] == [12.0, 10.0]
    with pytest.raises(Exception, match="append|forbid|not allowed|cannot"):
        conn.execute("update material_unit_conversion set factor = 1")


@needs_db
def test_a_note_in_dozens_is_confirmed_only_after_a_person_approved_the_conversion(conn, monkeypatch):
    from engine.adapters import llm

    s = m.school(conn)
    pen = m.item(conn, s, "Pen", "piece")
    lid = ml.build(conn, s["class"], "fortnight", m.MON, m.MON)
    reading = {"text": "2 dozen pens", "item_code": pen, "quantity": 2, "unit": "dozen"}
    monkeypatch.setattr(llm, "generate", lambda *a, **k: {"people_visible": False, "readings": [reading]})
    first = mi.read_note(conn, lid, "2 dozen pens", s["staff"], m.MON)
    assert [r.status for r in first] == ["needs_person"] and _lines(conn, lid) == []
    rv.approve_conversion(conn, s["tenant"], pen, "dozen", 12, s["staff"])
    second = mi.read_note(conn, lid, "2 dozen pens", s["staff"], m.MON)
    assert [r.status for r in second] == ["confirmed"] and _lines(conn, lid) == [(pen, 24)]
