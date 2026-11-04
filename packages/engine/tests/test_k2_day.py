"""M1-06 part 2: the educator's day, her week and one period (goals/m1-06b-educator-timetable.yaml, `/timetable/*`).
Rows are loaded from the school's own text into a K2 class made for the test (placeholder educator, no children read);
the database is the local copy, rolled back."""

import json
import os

import pytest

from engine.core import db
from engine.w2_print import k2_timetable_load as ld
from tests.test_k2_timetable_load import CAL_CSV, FN10, FRAME_CSV, VOCAB, planner_csv
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
        " materials) values (%s, 'ACT-K2-TSMELL', 'K2', 'Block Room', 'Smelling Bottles', '77', 'Tell smells apart',"
        " 'smells', 'matches', 'sorts', 'bottles')",
        (k["tenant"],),
    )
    planner = ld.read_planner_csv(planner_csv(("Fortnight 10", FN10)), VOCAB)
    plan = ld.link_activities(
        ld.build(
            ld.read_frame_csv(FRAME_CSV, VOCAB), planner, ld.read_calendar_csv(CAL_CSV, VOCAB), VOCAB, 10, 10
        ),
        ld.activity_names(conn),
    )
    ld.apply(conn, plan, ld.Target("K2", section, "2031-32", db.tenant_slug()))
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


def test_a_period_whose_line_names_an_activity_carries_the_activity_and_its_levels(world):
    day = call(world, "day", day="2026-11-23").json()
    linked = [p for p in day["periods"] if p["activity"]]
    assert linked and linked[0]["activity"]["code"] == "ACT-K2-TSMELL"
    one = call(
        world, "period", class_id=world["k"]["class"], day="2026-11-23", period_id=linked[0]["period_id"]
    ).json()
    assert one["activity_detail"]["levels"] == {"0": "", "1": "smells", "2": "matches", "3": "sorts"}
    assert one["plan_lines"]


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
