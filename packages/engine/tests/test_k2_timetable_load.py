"""M1-06 part 2: loading the school's own tabs into the six tables (goals/m1-06b-educator-timetable.yaml).

Inputs are the school's text: the frame tab in its own layout, the Fortnight 10 row of the Monthly Planner and an
excerpt of the Pre-Primary calendar (dates, fortnight labels, school holidays). No child data. The database tests run
inside a transaction that is rolled back, on a K2 class made for the test."""

import csv
import io
import json
import os
from datetime import date
from pathlib import Path

import pytest

from engine.core import db
from engine.w2_print import k2_timetable as tt
from engine.w2_print import k2_timetable_load as ld
from tests.voice_rows import a_k2_class

FIX = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[3]
VOCAB = tt.Vocabulary.from_config(
    next(
        c["value"]
        for c in json.loads((REPO / "supabase/seed/config.json").read_text())["config"]
        if c["key"] == "timetable.vocabulary"
    )
)
FRAME_CSV = (FIX / "k2_frame_tab_2026_27.csv").read_text()
CAL_CSV = (FIX / "k2_calendar_excerpt_2026_27.csv").read_text()
FN10 = json.loads((FIX / "k2_planner_fn10_2026_27.json").read_text())["cells"]


def planner_csv(*rows: tuple[str, list[str]]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["K2 - November Planner"])
    w.writerow(["", "Expression", "Critical thinking", "Courage"])
    for label, cells in rows:
        w.writerow([label, *cells])
    return out.getvalue()


def loaded(first=10, last=10, undecided=None):
    planner = ld.read_planner_csv(planner_csv(("Fortnight 10", FN10)), VOCAB)
    return ld.build(
        ld.read_frame_csv(FRAME_CSV, VOCAB),
        planner,
        ld.read_calendar_csv(CAL_CSV, VOCAB),
        VOCAB,
        first,
        last,
        undecided,
    )


def test_the_frame_tab_in_its_own_layout_reads_as_the_same_frame_as_the_cells_did():
    rows = json.loads((FIX / "k2_frame_fn_2026_27.json").read_text())["rows"]
    assert ld.read_frame_csv(FRAME_CSV, VOCAB).cells == tt.read_frame(rows, VOCAB).cells


def test_a_planner_fortnight_listed_twice_is_a_conflict_and_loads_neither():
    p = ld.read_planner_csv(
        planner_csv(("Fortnight 9", FN10), ("Fortnight 9", FN10), ("Fortnight 10", FN10)), VOCAB
    )
    assert set(p.plans) == {10}
    assert [n for n, _ in p.conflicts] == [9]


def test_the_calendar_gives_fortnight_dates_and_the_school_holidays():
    cal = ld.read_calendar_csv(CAL_CSV, VOCAB)
    assert cal.fortnights[10] == (date(2026, 11, 23), date(2026, 12, 6))
    assert cal.fortnights[11][0] == date(2026, 12, 7)
    assert (
        cal.days[date(2026, 11, 24)].kind == "holiday" and "Guru Nanak" in cal.days[date(2026, 11, 24)].note
    )
    assert cal.days[date(2026, 11, 17)].kind == "holiday"


def test_a_holiday_for_other_grades_only_is_not_a_holiday_here_and_a_tentative_one_says_so():
    cal = ld.read_calendar_csv(CAL_CSV, VOCAB)
    assert cal.days[date(2027, 1, 26)].kind == "teaching"
    assert (
        cal.days[date(2027, 3, 10)].kind == "holiday"
        and "tentative" in cal.days[date(2027, 3, 10)].note.lower()
    )


def test_fortnight_ten_makes_the_rows_the_sheets_say():
    load = loaded()
    assert len(load.fortnights) == 1 and len(load.periods) == 15 and len(load.slots) == 150
    days = {d: k for d, k, _ in load.school_days}
    assert (
        len(days) == 10
        and days[date(2026, 11, 24)] == "holiday"
        and list(days.values()).count("teaching") == 9
    )
    assert (
        len(load.sessions) == 125
    )  # 9 teaching days x 15 periods, less the 10 periods the school left empty
    assert all(s.day != date(2026, 11, 24) for s in load.sessions)
    plan = ld.read_planner_csv(planner_csv(("Fortnight 10", FN10)), VOCAB).plans[10]
    assert len(load.plan_entries) == sum(len(v) for v in plan.lines.values())


def test_a_day_two_sources_disagree_about_gets_no_session_and_a_note_a_person_will_read():
    why = "the Graph tab says Fortnight 10 ends 7 Dec; the calendar says Fortnight 11 starts 7 Dec"
    load = loaded(10, 11, undecided={date(2026, 12, 7): why})
    assert all(s.day != date(2026, 12, 7) for s in load.sessions)
    assert (date(2026, 12, 7), why) in load.undecided
    assert [n for n, _ in load.missing_plan] == [11]


def test_the_sql_is_the_same_every_time_and_every_insert_is_safe_to_run_again():
    target = ld.Target("K2", "A", "2026-27", "cornerstone")
    a, b = ld.statements(loaded(), target), ld.statements(loaded(), target)
    assert a == b
    inserts = [s for s in a if s.lstrip().lower().startswith("insert")]
    assert inserts and all("on conflict" in s.lower() and "do nothing" in s.lower() for s in inserts)
    text = "\n".join(a).lower()
    assert "pii" not in text and "child" not in text


def test_a_line_that_names_an_activity_exactly_links_to_it_and_any_other_line_stays_plain():
    names = {"smellingbottles": ["ACT-K2-0001"], "tulipmakingusingcraftpaper": ["ACT-K2-0002", "ACT-K2-0003"]}
    load = ld.link_activities(loaded(), names)
    linked = {e.text: e.activity_code for e in load.plan_entries if e.activity_code}
    assert linked == {"Smelling Bottles": "ACT-K2-0001"}  # the tulip line names two activities: never guessed


needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def a_target(conn):
    k = a_k2_class(conn)
    row = conn.execute("select section from school_class where id = %s", (k["class"],)).fetchone()
    return k, ld.Target("K2", row["section"], "2031-32", db.tenant_slug())


@needs_db
def test_loading_twice_adds_nothing_the_second_time_and_counts_are_printed(conn):
    k, target = a_target(conn)
    first = ld.apply(conn, loaded(), target)
    assert first == {
        "fortnight": 1, "school_day": 10, "period": first["period"], "timetable_slot": 150,
        "plan_entry": first["plan_entry"], "session": 125,
    }  # fmt: skip
    assert ld.apply(conn, loaded(), target) == {t: 0 for t in first}


@needs_db
def test_a_class_that_is_not_there_stops_the_load_before_it_writes_anything(conn):
    with pytest.raises(ld.NoSuchClass):
        ld.apply(conn, loaded(), ld.Target("K2", "no-such-section", "2031-32", db.tenant_slug()))


@needs_db
def test_the_sql_file_applied_gives_the_same_rows_as_apply(conn):
    k, target = a_target(conn)
    conn.execute("savepoint s")
    want = ld.apply(conn, loaded(), target)
    conn.execute("rollback to savepoint s")
    for stmt in ld.statements(loaded(), target):
        conn.execute(stmt)
    got = conn.execute(
        "select count(*) n from session s join school_class c on c.id = s.school_class_id where c.id = %s",
        (k["class"],),
    ).fetchone()["n"]
    assert got == want["session"]
