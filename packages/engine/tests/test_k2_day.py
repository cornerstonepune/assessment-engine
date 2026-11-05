"""M1-06 part 2: the educator's day, her week and one period (goals/m1-06b-educator-timetable.yaml, `/timetable/*`).
Rows are loaded from the school's own text into a K2 class made for the test (placeholder educator, no children read);
the database is the local copy, rolled back."""

import json
import os
from dataclasses import replace

import pytest

from engine.core import db
from engine.w2_print import k2_timetable_load as ld
from engine.w2_print import k2_timetable_sql as sq
from tests.test_k2_timetable_load import CAL_CSV, FRAME_CSV, PLANNER_CSV, REPO, SPANS, VOCAB
from tests.voice_rows import a_k2_class

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def world(conn, monkeypatch):
    """A K2 class with Fortnight 10 loaded, its educator, the switch on, and the app wired to this connection."""
    from fastapi.testclient import TestClient

    from engine.api import deps
    from engine.api.app import app

    k = a_k2_class(conn)
    section = conn.execute("select section from school_class where id = %s", (k["class"],)).fetchone()[
        "section"
    ]
    conn.execute(
        "insert into activity (tenant_id, code, band, strand, name, sheet_no, objective, level_1, level_2, level_3,"
        " materials) values (%s, 'ACT-K2-TCLAY', 'K2', 'Clay', 'Placeholder counting game', '77', 'Tell smells apart',"
        " 'smells', 'matches', 'sorts', 'bottles')",
        (k["tenant"],),
    )
    read = ld.read_planner_csv(PLANNER_CSV, VOCAB)
    halves = [
        (block, replace(one, lines={**one.lines, "math": ["Placeholder counting game" if x == "Addition - orally" else x for x in one.lines["math"]]}))
        for block, one in read.halves[10]
    ]  # fmt: skip
    planner = replace(read, halves={10: halves})
    frame = ld.read_frame_csv(FRAME_CSV, VOCAB, SPANS)
    plan = ld.build(frame, planner, ld.read_calendar_csv(CAL_CSV, VOCAB), VOCAB, 10, 10)
    sq.apply(conn, plan, ld.Target("K2", section, "2031-32", db.tenant_slug()))
    conn.execute(
        "insert into config (tenant_id, key, value, description) values (%s, 'educator.timetable_enabled', 'true', 't')"
        " on conflict (tenant_id, key) do update set value = 'true'",
        (k["tenant"],),
    )
    monkeypatch.setenv("ENGINE_KEY", "k")
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    try:
        with TestClient(app, headers={"X-Engine-Key": "k"}) as client:
            yield {"client": client, "k": k, "conn": conn}
    finally:
        app.dependency_overrides.clear()


def call(w, path, **body):
    body.setdefault("actor", w["k"]["email"])
    return w["client"].post(f"/timetable/{path}", json=body)


def test_the_day_is_her_classes_periods_in_time_order_with_what_the_plan_says(world):
    r = call(world, "day", day="2026-11-23").json()
    assert r["class"]["id"] == world["k"]["class"] and r["kind"] == "teaching" and r["week"] == "A"
    assert r["fortnight"]["number"] == 10 and len(r["periods"]) == 15
    starts = [p["starts_at"] for p in r["periods"]]
    assert starts == sorted(starts) and starts[0] == "08:30"
    phonics = next(p for p in r["periods"] if p["starts_at"] == "09:40")
    assert phonics["subject"] == "phonics" and phonics["line"] and phonics["line"] in phonics["text"]


def test_a_holiday_is_said_with_its_reason_and_has_no_sessions(world):
    r = call(world, "day", day="2026-11-24").json()
    assert r["kind"] == "holiday" and "Guru Nanak" in r["note"] and r["periods"] == []


def test_the_week_is_five_days_and_a_holiday_stays_in_it(world):
    r = call(world, "week", week_of="2026-11-26").json()
    assert (
        r["week_of"] == "2026-11-23"
        and r["week"] == "A"
        and [d["weekday"] for d in r["days"]] == [1, 2, 3, 4, 5]
    )
    assert next(d for d in r["days"] if d["weekday"] == 2)["kind"] == "holiday"


def test_a_period_whose_line_names_an_activity_says_who_it_is_and_shows_its_neighbouring_lines(world):
    week = call(world, "week", week_of="2026-11-23").json()
    found = [
        (d["day"], p)
        for d in week["days"]
        for p in d["periods"]
        if p["activity"] and p["activity"]["code"] == "ACT-K2-TCLAY"
    ]
    assert found, "the placeholder line is on no period this week"
    day, linked = found[0]
    one = call(world, "period", class_id=world["k"]["class"], day=day, period_id=linked["period_id"]).json()
    assert one["activity"]["name"] == "Placeholder counting game" and "activity_detail" not in one
    assert (
        "Placeholder counting game" in one["plan_lines"]
        and one["week"] in ("A", "B")
        and one["fortnight"]["number"] == 10
    )


def test_every_answer_says_the_month_is_not_locked_yet(world):
    day = call(world, "day", day="2026-11-23").json()
    assert day["frozen"] is False and call(world, "week", week_of="2026-11-23").json()["frozen"] is False
    pid = day["periods"][0]["period_id"]
    assert (
        call(world, "period", class_id=world["k"]["class"], day="2026-11-23", period_id=pid).json()["frozen"]
        is False
    )


def test_while_the_switch_is_off_every_call_is_refused(world):
    world["conn"].execute("update config set value = 'false' where key = 'educator.timetable_enabled'")
    for path, extra in (
        ("day", {}),
        ("week", {}),
        ("period", {"class_id": world["k"]["class"], "day": "2026-11-23", "period_id": "x"}),
    ):
        assert call(world, path, **extra).status_code == 403


def test_a_class_she_does_not_hold_is_refused_and_a_stranger_gets_nothing(world):
    other = a_k2_class(world["conn"])
    assert call(world, "day", class_id=other["class"], day="2026-11-23").status_code == 403
    assert call(world, "day", actor="nobody@example.test", day="2026-11-23").status_code in (403, 404)


def test_no_answer_carries_a_child_or_a_name(world):
    text = json.dumps(call(world, "week", week_of="2026-11-23").json()).lower()
    for word in ("child", "roll_no", "birthday", "pii", world["k"]["email"]):
        assert word not in text


def test_the_calls_are_a_fixed_small_number_of_queries(world, monkeypatch):
    seen = []
    real = world["conn"].execute
    monkeypatch.setattr(
        type(world["conn"]),
        "execute",
        lambda self, q, *a, **kw: (seen.append(str(q)), real(q, *a, **kw))[1],
        raising=False,
    )
    call(world, "week", week_of="2026-11-23")
    assert 0 < len(seen) <= 8


def test_the_switch_is_seeded_and_off_and_the_roles_that_see_a_timetable_are_named():
    """The seed says it, so a new school or a fresh copy starts with the timetable off and the roles named."""
    import json
    from pathlib import Path

    rows = {
        c["key"]: c
        for c in json.loads((Path(__file__).resolve().parents[3] / "supabase/seed/config.json").read_text())[
            "config"
        ]
    }
    switch = rows["educator.timetable_enabled"]
    assert switch["value"] is False and switch.get("seed_once") is True
    assert rows["educator.timetable_roles"]["value"] == ["class_teacher", "cover_educator"]


def test_a_day_outside_every_fortnight_has_no_periods_and_no_week(world):
    c = world["conn"]
    campus = c.execute("select campus_id from school_class where id = %s", (world["k"]["class"],)).fetchone()[
        "campus_id"
    ]
    c.execute(
        "insert into school_day (tenant_id, campus_id, on_date, kind) values (%s, %s, '2026-12-08', 'teaching')"
        " on conflict do nothing",
        (world["k"]["tenant"], campus),
    )
    r = call(world, "day", day="2026-12-08").json()
    assert r["kind"] == "teaching" and r["week"] is None and r["fortnight"] is None and r["periods"] == []


def test_a_week_whose_monday_has_no_row_still_names_its_week_and_fortnight(world):
    c = world["conn"]
    c.execute(
        "delete from session where school_day_id in (select id from school_day where on_date = '2026-11-23')"
    )
    c.execute(
        "delete from school_day where on_date = '2026-11-23' and not exists (select 1 from session where school_day_id = school_day.id)"
    )
    r = call(world, "week", week_of="2026-11-23").json()
    assert r["days"][0]["kind"] == "none" and r["week"] == "A" and r["fortnight"]["number"] == 10


def test_while_the_switch_is_off_a_period_call_without_its_fields_is_refused_the_same_way(world):
    world["conn"].execute("update config set value = 'false' where key = 'educator.timetable_enabled'")
    assert call(world, "period").status_code == 403


def _lines(w, monday, subject):
    """The planner lines the week's first period of `subject` with a planner line shows, in order."""
    days = call(w, "week", week_of=monday).json()["days"]
    day, one = next(
        (d["day"], p) for d in days for p in d["periods"] if p["subject"] == subject and p["plan_entry_id"]
    )
    return call(w, "period", class_id=w["k"]["class"], day=day, period_id=one["period_id"]).json()[
        "plan_lines"
    ]


def test_a_fortnight_under_two_months_shows_a_period_only_its_own_weeks_lines(world):
    """Fortnight 10 is listed under November and December: week A takes November's row, week B December's. A period
    shows the lines of its own week's row only, so General Awareness says each of its two lines once. Week A is the
    week of 23 Nov, week B of 30 Nov."""
    assert [x.strip() for x in _lines(world, "2026-11-23", "general_awareness")] == [
        "Insects",
        "lifecycle of a butterfly",
    ]
    assert [x.strip() for x in _lines(world, "2026-11-30", "general_awareness")] == [
        "Insects",
        "lifecycle of a butterfly",
    ]
    (_, a), (_, b) = ld.read_planner_csv(PLANNER_CSV, VOCAB).halves[10]
    assert a.lines["music"] != b.lines["music"], "the two rows' Music differ in the school's text"
    assert _lines(world, "2026-11-23", "music") == a.lines["music"]
    assert _lines(world, "2026-11-30", "music") == b.lines["music"]


def test_a_fortnight_with_a_single_row_still_shows_all_its_lines(conn, world):
    """A fortnight listed once has no week on its lines: every period shows all of them."""
    conn.execute("update plan_entry set week_code = null where school_class_id = %s", (world["k"]["class"],))
    lines = _lines(world, "2026-11-23", "general_awareness")
    assert [x.strip() for x in lines] == ["Insects", "lifecycle of a butterfly"] * 2


def test_the_migration_gives_rows_loaded_before_it_the_week_the_loader_now_writes(conn, world):
    """Rows loaded before week_code existed: the migration's backfill, run on them, gives every line the week the loader
    gives it today, from what was stored (each half's month in `source`, the second half numbered on)."""
    klass = world["k"]["class"]
    weeks = "select plan_key, ord, week_code from plan_entry where school_class_id = %s order by 1, 2"
    written = conn.execute(weeks, (klass,)).fetchall()
    assert {r["week_code"] for r in written} == {"A", "B"}
    conn.execute("update plan_entry set week_code = null where school_class_id = %s", (klass,))
    conn.execute((REPO / "supabase/migrations/20270108090000_plan_entry_week.sql").read_text())
    assert conn.execute(weeks, (klass,)).fetchall() == written


def test_a_period_with_no_end_lasts_until_the_next_one_starts_and_the_days_last_keeps_none(conn, world):
    """The frame gives some periods no end (the bus). The engine says when each ends, once, for every screen: a period
    with no end lasts until the next starts; the day's last keeps none. The day and the period itself agree."""
    conn.execute(
        "update period set ends_at = null where id = (select ts.period_id from timetable_slot ts join period p on"
        " p.id = ts.period_id where ts.school_class_id = %s and p.starts_at = '10:20' limit 1)",
        (world["k"]["class"],),
    )
    periods = call(world, "day", day="2026-11-23").json()["periods"]
    ga = next(p for p in periods if p["starts_at"] == "10:20")
    assert ga["ends_at"] == "10:40"
    assert all(p["ends_at"] for p in periods[:-1]) and periods[-1]["ends_at"] is None
    one = call(
        world, "period", class_id=world["k"]["class"], day="2026-11-23", period_id=ga["period_id"]
    ).json()
    assert one["ends_at"] == "10:40"


def test_each_period_carries_its_own_name_apart_from_its_planner_line(world):
    """A lesson is named by the frame ("Academic 2 General Awareness"), its planner line is `line`; a break by its own
    words. The name is never cut from the joined text, so a line holding ': ' cannot leak into it."""
    periods = call(world, "day", day="2026-11-23").json()["periods"]
    by_start = {p["starts_at"]: p for p in periods}
    assert (
        by_start["10:20"]["name"] == "Academic 2 General Awareness" and by_start["10:20"]["line"] == "Insects"
    )
    assert by_start["10:00"]["name"] == "Reading time"
    assert by_start["11:45"]["name"] == "Lunch + Washroom"
    assert all(p["name"] and (p["line"] or "") not in p["name"] for p in periods if p["line"])
    one = call(
        world,
        "period",
        class_id=world["k"]["class"],
        day="2026-11-23",
        period_id=by_start["10:20"]["period_id"],
    )
    assert one.json()["name"] == "Academic 2 General Awareness"
