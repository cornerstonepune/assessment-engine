"""The K2 educator's materials list: built by code from the planned activities, edited by her, every change kept
(goals/m1-10-materials-list.yaml; task M1-10; D-070, D-071). Rows are placeholders made inside the test and rolled back."""

import datetime as dt
import os

import psycopg
import pytest

from engine.core import db
from engine.w2_print import materials_list as ml
from tests import materials_rows as m

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

D1, D2, D3 = m.MON, m.MON + dt.timedelta(days=1), m.MON + dt.timedelta(days=8)
END = m.MON + dt.timedelta(days=13)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def s(conn):
    return m.school(conn)


def _build(conn, s, period="fortnight", lo=m.MON, hi=END):
    return ml.build(conn, s["class"], period, lo, hi)


def _lines(conn, lid):
    return conn.execute(
        "select l.*, i.name from materials_line l join material_item i using (tenant_id) where i.code = l.material_code"
        " and l.list_id = %s and l.removed_at is null order by l.needed_on, i.name",
        (lid,),
    ).fetchall()


def test_a_material_needed_twice_is_one_line_with_the_sum_under_the_day_it_is_first_needed(conn, s):
    a, b = s["acts"][:2]
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, a, clay, 2)
    m.needs(conn, s, b, clay, 3)
    m.planned(conn, s, D3, b)
    m.planned(conn, s, D1, a)
    [line] = _lines(conn, _build(conn, s))
    assert (line["quantity"], line["unit"], line["needed_on"], line["activity_code"]) == (5, "packet", D1, a)
    got = conn.execute(
        "select activity_code, on_date from materials_line_source where line_id = %s order by on_date",
        (line["id"],),
    ).fetchall()
    assert [(r["activity_code"], r["on_date"]) for r in got] == [(a, D1), (b, D3)]


def test_a_quantity_the_sheet_does_not_give_stays_empty_and_poisons_the_sum_it_is_in(conn, s):
    a, b = s["acts"][:2]
    glue = m.item(conn, s, "Glue", "bottle")
    m.needs(conn, s, a, glue, 2)
    m.needs(conn, s, b, glue, None)
    m.planned(conn, s, D1, a)
    m.planned(conn, s, D2, b)
    [line] = _lines(conn, _build(conn, s))
    assert line["quantity"] is None


def test_only_this_class_this_range_and_planned_sessions_count(conn, s):
    a, b, c = s["acts"][:3]
    paper = m.item(conn, s, "Paper")
    for act in (a, b, c):
        m.needs(conn, s, act, paper, 1)
    other = conn.execute(
        "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
        " select tenant_id, campus_id, academic_year_id, 'K2', 'T-other' from school_class where id = %s returning id",
        (s["class"],),
    ).fetchone()["id"]
    m.planned(conn, s, D1, a)  # counts
    m.planned(conn, s, D2, b, planned_=False)  # not planned: does not
    m.planned(conn, s, D2, c, klass=other)  # another class: does not
    m.planned(conn, s, m.MON + dt.timedelta(days=30), c)  # outside the range: does not
    [line] = _lines(conn, _build(conn, s))
    assert line["quantity"] == 1


def test_the_list_reads_grouped_by_day_by_week_and_by_fortnight(conn, s):
    a, b = s["acts"][:2]
    x, y = m.item(conn, s, "Xylophone"), m.item(conn, s, "Yarn", home="school", unit_value=40)
    m.needs(conn, s, a, x, 1)
    m.needs(conn, s, b, y, 2)
    m.planned(conn, s, D1, a)
    m.planned(conn, s, D3, b)
    lid = _build(conn, s)
    by_day = ml.read(conn, lid, "day")
    assert [g["label"] for g in by_day["groups"]] == [
        f"{D1:%a} {D1.day} {D1:%b}",
        f"{D3:%a} {D3.day} {D3:%b}",
    ]
    assert len(ml.read(conn, lid, "week")["groups"]) == 2
    [fn] = ml.read(conn, lid, "fortnight")["groups"]
    assert fn["label"] == "Fortnight 910" and len(fn["lines"]) == 2
    by_name = {ln["item"].split()[0]: ln for ln in fn["lines"]}
    assert by_name["Xylophone"]["tracked"] is False and by_name["Yarn"]["tracked"] is True
    assert by_name["Yarn"]["home"] == "school" and by_name["Xylophone"]["activity"]["code"] == a


def test_a_changed_quantity_is_kept_with_who_and_when_and_survives_a_rebuild(conn, s):
    a = s["acts"][0]
    pen = m.item(conn, s, "Pen")
    m.needs(conn, s, a, pen, 4)
    m.planned(conn, s, D1, a)
    lid = _build(conn, s)
    [line] = _lines(conn, lid)
    ml.set_quantity(conn, line["id"], 6, s["staff"])
    edit = conn.execute("select * from materials_line_edit where line_id = %s", (line["id"],)).fetchone()
    assert (edit["kind"], edit["who"], edit["before"]["quantity"], edit["after"]["quantity"]) == (
        "quantity",
        s["staff"],
        4,
        6,
    )
    conn.execute("update activity_material set quantity = 9 where activity_code = %s", (a,))
    [again] = _lines(conn, _build(conn, s))
    assert again["id"] == line["id"] and again["quantity"] == 6


def test_a_removed_line_is_kept_in_the_edit_table_and_does_not_come_back(conn, s):
    a = s["acts"][0]
    tape = m.item(conn, s, "Tape")
    m.needs(conn, s, a, tape, 1)
    m.planned(conn, s, D1, a)
    lid = _build(conn, s)
    [line] = _lines(conn, lid)
    ml.remove(conn, line["id"], s["staff"])
    assert _lines(conn, lid) == []
    assert [
        r["kind"]
        for r in conn.execute("select kind from materials_line_edit where line_id = %s", (line["id"],))
    ] == ["remove"]
    _build(conn, s)
    assert _lines(conn, lid) == []


def test_a_line_the_plan_no_longer_needs_goes_but_an_edited_one_stays(conn, s):
    a, b = s["acts"][:2]
    p, q = m.item(conn, s, "Plate"), m.item(conn, s, "Queen bead")
    m.needs(conn, s, a, p, 1)
    m.needs(conn, s, b, q, 1)
    m.planned(conn, s, D1, a)
    m.planned(conn, s, D2, b)
    lid = _build(conn, s)
    by = {ln["material_code"]: ln for ln in _lines(conn, lid)}
    ml.set_quantity(conn, by[q]["id"], 3, s["staff"])
    conn.execute("delete from activity_material where activity_code in (%s, %s)", (a, b))
    left = {ln["material_code"] for ln in _lines(conn, _build(conn, s))}
    assert left == {q}


def test_an_educator_adds_a_line_only_from_the_catalogue(conn, s):
    a = s["acts"][0]
    bell = m.item(conn, s, "Bell", "piece")
    lid = _build(conn, s)
    line = ml.add(conn, lid, bell, 2, D2, a, s["staff"])
    row = conn.execute("select * from materials_line where id = %s", (line,)).fetchone()
    assert (row["source"], row["quantity"], row["unit"], row["needed_on"]) == ("educator", 2, "piece", D2)
    assert conn.execute(
        "select kind, who from materials_line_edit where line_id = %s", (line,)
    ).fetchone() == {"kind": "add", "who": s["staff"]}
    with pytest.raises(ml.NotInCatalogue):
        ml.add(conn, lid, "MAT-NOPE", 1, D2, a, s["staff"])


def test_a_new_item_is_a_catalogue_entry_with_no_home_and_no_value_waiting_for_a_person(conn, s):
    code = ml.propose_item(conn, s["tenant"], "Feather duster", "piece", s["staff"])
    row = conn.execute("select * from material_item where code = %s", (code,)).fetchone()
    assert (row["name"], row["home"], row["unit_value"]) == ("Feather duster", None, None)
    waiting = conn.execute(
        "select state, who from material_item_proposal where material_code = %s", (code,)
    ).fetchall()
    assert [(w["state"], w["who"]) for w in waiting] == [("needs_person", s["staff"])]
    assert (
        ml.propose_item(conn, s["tenant"], "  feather DUSTER ", "piece", s["staff"]) == code
    )  # the same, not a second
    assert (
        conn.execute(
            "select count(*) as n from material_item_proposal where material_code = %s", (code,)
        ).fetchone()["n"]
        == 1
    )


def test_a_line_names_its_activity_by_id_code_and_name(conn, s):
    a = s["acts"][0]
    pen = m.item(conn, s, "Pen")
    m.needs(conn, s, a, pen, 1)
    m.planned(conn, s, D1, a)
    [line] = ml.read(conn, _build(conn, s))["groups"][0]["lines"]
    assert set(line["activity"]) == {"id", "code", "name"} and line["activity"]["code"] == a


def test_the_read_says_whether_it_was_sent_and_whether_the_team_has_it(conn, s):
    from engine.w2_print import materials_send as send

    a = s["acts"][0]
    pen = m.item(conn, s, "Pen")
    m.needs(conn, s, a, pen, 1)
    m.planned(conn, s, D1, a)
    lid = _build(conn, s)
    assert ml.read(conn, lid)["last_send"] is None
    out = send.send(conn, lid, "whatsapp", s["staff"])
    assert ml.read(conn, lid)["last_send"]["team_has_it"] is False
    send.team_has_it(conn, out["send_id"], s["staff"])
    got = ml.read(conn, lid)["last_send"]
    assert (got["send_id"], got["route"], got["team_has_it"]) == (out["send_id"], "whatsapp", True)


def test_building_the_same_range_again_gives_the_same_list(conn, s):
    a = s["acts"][0]
    pen = m.item(conn, s, "Pen")
    m.needs(conn, s, a, pen, 1)
    m.planned(conn, s, D1, a)
    assert _build(conn, s) == _build(conn, s)


def test_who_may_edit_is_the_roles_the_school_names_for_the_timetable(conn, s):
    import json

    assert ml.may_edit(conn, s["staff"], s["class"], dt.date(2031, 1, 1)) is True
    conn.execute(
        "insert into config (tenant_id, key, value, description) values (%s, 'educator.timetable_roles', %s, 't')"
        " on conflict (tenant_id, key) do update set value = excluded.value",
        (s["tenant"], json.dumps(["coordinator"])),
    )
    assert ml.may_edit(conn, s["staff"], s["class"], dt.date(2031, 1, 1)) is False


def test_the_edit_table_cannot_be_changed(conn, s):
    a = s["acts"][0]
    cup = m.item(conn, s, "Cup")
    m.needs(conn, s, a, cup, 1)
    m.planned(conn, s, D1, a)
    [line] = _lines(conn, _build(conn, s))
    ml.set_quantity(conn, line["id"], 2, s["staff"])
    with pytest.raises(psycopg.Error):
        conn.execute("update materials_line_edit set who = who")


def test_building_never_touches_the_catalogue_or_invents_a_rupee_value(conn, s):
    a = s["acts"][0]
    dye = m.item(conn, s, "Dye")
    m.needs(conn, s, a, dye, 1)
    m.planned(conn, s, D1, a)
    _build(conn, s)
    row = conn.execute("select home, unit_value from material_item where code = %s", (dye,)).fetchone()
    assert row == {"home": None, "unit_value": None}


def test_two_sessions_of_one_activity_on_a_day_add_twice_and_the_sources_add_up_to_the_quantity(conn, s):
    a = s["acts"][0]
    glue = m.item(conn, s, "Glue", "bottle")
    m.needs(conn, s, a, glue, 2)
    m.planned(conn, s, D1, a)
    m.planned(conn, s, D1, a)
    [line] = _lines(conn, _build(conn, s))
    sources = conn.execute(
        "select quantity from materials_line_source where line_id = %s", (line["id"],)
    ).fetchall()
    assert line["quantity"] == 4 and sum(r["quantity"] for r in sources) == 4


def test_a_quantity_cannot_be_set_on_a_removed_line(conn, s):
    a = s["acts"][0]
    tape = m.item(conn, s, "Tape")
    m.needs(conn, s, a, tape, 1)
    m.planned(conn, s, D1, a)
    [line] = _lines(conn, _build(conn, s))
    ml.remove(conn, line["id"], s["staff"])
    with pytest.raises(ml.LineRemoved):
        ml.set_quantity(conn, line["id"], 3, s["staff"])
    assert [
        r["kind"]
        for r in conn.execute("select kind from materials_line_edit where line_id = %s", (line["id"],))
    ] == ["remove"]


def test_the_read_says_when_the_list_has_changed_since_it_was_sent(conn, s):
    from engine.w2_print import materials_send as send

    a = s["acts"][0]
    pen = m.item(conn, s, "Pen")
    m.needs(conn, s, a, pen, 1)
    m.planned(conn, s, D1, a)
    lid = _build(conn, s)
    send.send(conn, lid, "whatsapp", s["staff"])
    assert ml.read(conn, lid)["last_send"]["changed"] is False
    [line] = _lines(conn, lid)
    ml.set_quantity(conn, line["id"], 7, s["staff"])
    assert ml.read(conn, lid)["last_send"]["changed"] is True
    send.send(conn, lid, "whatsapp", s["staff"])
    assert ml.read(conn, lid)["last_send"]["changed"] is False


def test_the_grant_window_is_the_day_the_school_gives_not_the_servers(conn, s):
    staff = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (s["tenant"], s["campus"])
    ).fetchone()["id"]
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, valid_to, granted_by)"
        " values (%s, %s, 'cover_educator', %s, '2031-06-10', '2031-06-12', 'test')",
        (s["tenant"], staff, s["class"]),
    )
    day = dt.date(2031, 6, 10)
    assert ml.may_edit(conn, staff, s["class"], day) is True
    assert ml.may_edit(conn, staff, s["class"], day - dt.timedelta(days=1)) is False
    assert ml.may_edit(conn, staff, s["class"], dt.date(2031, 6, 13)) is False
