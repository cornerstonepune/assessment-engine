"""M1-06 part 2: loading the school's own tabs into the six tables (goals/m1-06b-educator-timetable.yaml).

Inputs are the tabs exactly as the Sheets connector returned them on 2026-11-04 (`supabase/seed/k2_tabs_2026_11_04/`, no
child data): the Time table (merged cells filled across what they cover), the Monthly Planner, the Pre-Primary calendar.
The database tests run inside a transaction that is rolled back, on a K2 class made for the test."""

import csv
import io
import json
import os
import re
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from engine.core import db
from engine.w2_print import k2_timetable as tt
from engine.w2_print import k2_timetable_load as ld
from engine.w2_print import k2_timetable_sql as sq
from tests.voice_rows import a_k2_class

REPO = Path(__file__).resolve().parents[3]
TABS = REPO / "supabase/seed/k2_tabs_2026_11_04"
VOCAB = tt.Vocabulary.from_config(
    next(
        c["value"]
        for c in json.loads((REPO / "supabase/seed/config.json").read_text())["config"]
        if c["key"] == "timetable.vocabulary"
    )
)
FRAME_CSV, PLANNER_CSV, CAL_CSV = (
    (TABS / n).read_text() for n in ("frame.csv", "planner.csv", "calendar.csv")
)
SPANS = json.loads((TABS / "frame_spans.json").read_text())


def loaded(first=10, last=10, undecided=None, planner=None):
    planner = planner or ld.read_planner_csv(PLANNER_CSV, VOCAB)
    frame = ld.read_frame_csv(FRAME_CSV, VOCAB, SPANS)
    return ld.build(frame, planner, ld.read_calendar_csv(CAL_CSV, VOCAB), VOCAB, first, last, undecided)


def test_the_calendar_gives_fortnight_dates_and_the_school_holidays():
    cal = ld.read_calendar_csv(CAL_CSV, VOCAB)
    assert cal.fortnights[10] == (date(2026, 11, 23), date(2026, 12, 6)) and cal.fortnights[11][0] == date(
        2026, 12, 7
    )
    assert (
        cal.days[date(2026, 11, 24)].kind == "holiday" and "Guru Nanak" in cal.days[date(2026, 11, 24)].note
    )
    assert cal.days[date(2026, 11, 17)].kind == "holiday"
    assert {d for d, c in cal.days.items() if c.kind == "holiday" and date(2027, 1, 1) <= d <= date(2027, 3, 28) and d.weekday() < 5} == {
        date(2027, 1, 1), date(2027, 1, 15), date(2027, 2, 19), date(2027, 3, 10), date(2027, 3, 22), date(2027, 3, 26)
    }  # fmt: skip


def test_a_holiday_for_other_grades_only_is_not_a_holiday_here_and_a_tentative_one_says_so():
    cal = ld.read_calendar_csv(CAL_CSV, VOCAB)
    assert cal.days[date(2027, 1, 26)].kind == "teaching"
    assert (
        cal.days[date(2027, 3, 10)].kind == "holiday"
        and "tentative" in cal.days[date(2027, 3, 10)].note.lower()
    )


def test_fortnight_ten_is_two_rows_one_per_month_block_and_each_week_takes_its_own_block_s_row():
    """A fortnight straddles two months, so the Monthly Planner lists it under each month's heading. Week A takes the
    first block's row, week B the second's; every line says which block it came from. (Settled by the school's owner.)"""
    p = ld.read_planner_csv(PLANNER_CSV, VOCAB)
    assert 10 not in p.plans and p.conflicts == []
    assert [b for b, _ in p.halves[10]] == ["November", "December"]
    nov, dec = (plan for _, plan in p.halves[10])
    assert nov != dec
    load = loaded()
    entries = {(e.key, e.ord): e for e in load.plan_entries}
    for key in {*nov.lines, *dec.lines}:
        after = len(nov.lines.get(key, []))
        for i, text in enumerate(nov.lines.get(key, []), 1):
            assert (entries[key, i].text, entries[key, i].block) == (text, "November")
        for i, text in enumerate(dec.lines.get(key, []), after + 1):
            assert (entries[key, i].text, entries[key, i].block) == (text, "December")
    blocks = set()
    for s in load.sessions:
        if s.key and s.ord:
            blocks.add(entries[s.key, s.ord].block)
            assert entries[s.key, s.ord].block == ("November" if s.day < date(2026, 11, 30) else "December")
    assert blocks == {"November", "December"}  # Mon 30 Nov is a November day in week B: it stays in week B
    assert [n for n, _ in load.split] == [10]


def test_fortnight_ten_makes_the_rows_the_sheets_say():
    load = loaded()
    assert len(load.fortnights) == 1 and len(load.periods) == 15 and len(load.slots) == 150
    days = {d: k for d, k, _ in load.school_days}
    assert (
        len(days) == 10
        and days[date(2026, 11, 24)] == "holiday"
        and list(days.values()).count("teaching") == 9
    )
    frame = ld.read_frame_csv(FRAME_CSV, VOCAB, SPANS)
    teaching = [d for d, k in days.items() if k == "teaching"]
    want = sum(
        1
        for d in teaching
        for c in frame.cells
        if c.week == ("A" if d < date(2026, 11, 30) else "B")
        and c.weekday == d.isoweekday()
        and c.kind != "empty"
    )
    assert len(load.sessions) == want and all(s.day != date(2026, 11, 24) for s in load.sessions)
    halves = ld.read_planner_csv(PLANNER_CSV, VOCAB).halves[10]
    assert len(load.plan_entries) == sum(len(v) for _, plan in halves for v in plan.lines.values())


def test_afternoon_times_are_written_as_the_afternoon_from_the_vocabulary_row_not_from_code():
    starts = [p.start for p in loaded().periods]
    assert "13:15" in starts and "12:40" in starts and not any(x.startswith("01") for x in starts)


def test_a_day_two_sources_disagree_about_gets_no_session_and_a_note_a_person_will_read():
    why = "the Graph tab says Fortnight 10 ends 7 Dec; the calendar says Fortnight 11 starts 7 Dec"
    load = loaded(10, 11, undecided={date(2026, 12, 7): why})
    assert (
        all(s.day != date(2026, 12, 7) for s in load.sessions) and (date(2026, 12, 7), why) in load.undecided
    )
    assert any(d == date(2026, 12, 7) and note.startswith("undecided") for d, _, note in load.school_days)


def test_a_fortnight_that_does_not_start_on_a_monday_is_a_conflict_and_loads_nothing():
    rows = list(csv.reader(io.StringIO(CAL_CSV)))
    for i, r in enumerate(rows):
        if r[0] == "Monday, November 23, 2026":
            label, rows[i][1] = r[1], ""
        if r[0] == "Tuesday, November 24, 2026":
            tue = i
    rows[tue][1] = label
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    load = ld.build(
        ld.read_frame_csv(FRAME_CSV, VOCAB, SPANS), ld.read_planner_csv(PLANNER_CSV, VOCAB),
        ld.read_calendar_csv(out.getvalue(), VOCAB), VOCAB, 10, 10,
    )  # fmt: skip
    assert load.fortnights == [] and load.sessions == [] and [n for n, _ in load.conflicts if n == 10]


# ---- what the planner reader keeps, exactly


def _source_rows():
    """Every Fortnight row of the planner, as the sheet has it: (number, row index among those listed, its ten cells)."""
    seen: dict[int, int] = {}
    for r in csv.reader(io.StringIO(PLANNER_CSV)):
        if m := re.match(VOCAB.planner_row, r[0].strip()):
            n = int(m.group(1))
            seen[n] = seen.get(n, 0) + 1
            yield n, seen[n], (r + [""] * 11)[1:11]


def _flat(text: str) -> str:
    return " ".join(text.replace('"', "").split())


def test_every_planner_line_is_the_schools_own_words_and_none_of_them_is_dropped_for_fortnights_10_to_17():
    p = ld.read_planner_csv(PLANNER_CSV, VOCAB)
    for n, k, cells in _source_rows():
        if n < 10:
            continue
        plan = p.halves[n][k - 1][1] if n in p.halves else p.plans[n]
        source = _flat("\n".join(cells))
        kept = [_flat(line) for lines in plan.lines.values() for line in lines]
        assert all(line in source for line in kept), f"FN{n} row {k}: text the school did not write"
        for raw in "\n".join(cells).split("\n"):
            opened, rest = tt.heading_of(_flat(raw), VOCAB)
            want = re.sub(r"^\d+\.\s*", "", _flat(rest if opened else raw))
            if want and not (opened and not rest):
                assert any(want in line for line in kept), f"FN{n} row {k}: {want!r} was dropped"


def test_music_and_dance_routines_and_the_column_the_school_titled_value_education_are_kept_where_they_belong():
    p = ld.read_planner_csv(PLANNER_CSV, VOCAB).plans[16]
    assert "Samaaroh practice" in p.lines["music"] and not any("Samaaroh" in x for x in p.lines["clay"])
    assert any("Survey peers" in x for x in p.lines["routines"]) and not any(
        "Survey" in x for x in p.lines["prayer"]
    )
    assert any(
        "International Women's Day" in x for x in p.lines["value_education"]
    )  # the school put its events there


def test_no_planner_line_keeps_a_stray_quotation_mark_from_the_cell():
    p = ld.read_planner_csv(PLANNER_CSV, VOCAB)
    for n in range(10, 18):
        for plan in [p.plans[n]] if n in p.plans else [pl for _, pl in p.halves[n]]:
            for lines in plan.lines.values():
                assert not any(x.startswith('"') or x.endswith('"') for x in lines)


# ---- the SQL


def test_the_sql_is_the_same_every_time_and_every_insert_is_safe_to_run_again():
    target = ld.Target("K2", "A", "2026-27", "cornerstone")
    a, b = sq.statements(loaded(), target), sq.statements(loaded(), target)
    assert a == b
    inserts = [s for s in a if s.lstrip().lower().startswith("insert")]
    assert inserts and all("on conflict" in s.lower() and "do nothing" in s.lower() for s in inserts)
    text = "\n".join(a).lower()
    assert "pii" not in text and "child_id" not in text


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
    # school days belong to the campus, not the class: any already loaded for these dates are not added again
    had = conn.execute(
        "select count(*) n from school_day where on_date between '2026-11-23' and '2026-12-06'"
    ).fetchone()["n"]
    first = sq.apply(conn, loaded(), target)
    assert first == {
        "fortnight": 1, "school_day": 10 - had, "period": first["period"], "timetable_slot": 150,
        "plan_entry": first["plan_entry"], "session": len(loaded().sessions),
    }  # fmt: skip
    assert sq.apply(conn, loaded(), target) == {t: 0 for t in first}


@needs_db
def test_a_class_that_is_not_there_stops_the_load_before_it_writes_anything(conn):
    with pytest.raises(sq.NoSuchClass):
        sq.apply(conn, loaded(), ld.Target("K2", "no-such-section", "2031-32", db.tenant_slug()))


@needs_db
def test_the_sql_file_applied_gives_the_same_rows_as_apply(conn):
    k, target = a_target(conn)
    conn.execute("savepoint s")
    want = sq.apply(conn, loaded(), target)
    conn.execute("rollback to savepoint s")
    for stmt in sq.statements(loaded(), target):
        conn.execute(stmt)
    got = conn.execute("select count(*) n from session where school_class_id = %s", (k["class"],)).fetchone()[
        "n"
    ]
    assert got == want["session"]


@needs_db
def test_a_line_names_an_activity_only_when_it_is_exactly_one_and_the_sql_is_the_one_that_says(conn):
    k, target = a_target(conn)
    for code, name in (
        ("ACT-K2-T1", "Placeholder counting game"),
        ("ACT-K2-T2", "Twin placeholder"),
        ("ACT-K2-T3", "twin  PLACEHOLDER"),
    ):
        conn.execute(
            "insert into activity (tenant_id, code, band, strand, name) values (%s, %s, 'K2', 'Maths', %s)",
            (k["tenant"], code, name),
        )
    base = ld.read_planner_csv(PLANNER_CSV, VOCAB).halves[10][1][1]
    math = [
        {
            "Addition - orally": "Placeholder counting game",
            "Writing number 41-50 on square notebook": "Twin placeholder",
        }.get(x, x)
        for x in base.lines["math"]
    ]
    planner = ld.Planner({10: replace(base, lines={**base.lines, "math": math})}, [])
    sq.apply(conn, loaded(planner=planner), target)
    linked = {
        r["text"]: r["code"]
        for r in conn.execute(
            "select pe.text, a.code from plan_entry pe left join activity a on a.id = pe.activity_id"
            " where pe.school_class_id = %s and pe.text in ('Placeholder counting game', 'Twin placeholder')",
            (k["class"],),
        ).fetchall()
    }
    assert linked == {
        "Placeholder counting game": "ACT-K2-T1",
        "Twin placeholder": None,
    }  # two twins: never guessed
    assert sq.linked(conn) >= 1


# ---- the command


def _args(tmp_path, *extra):
    return ["timetable", "load", "--frame", str(TABS / "frame.csv"), "--spans", str(TABS / "frame_spans.json"),
            "--planner", str(TABS / "planner.csv"), "--calendar", str(TABS / "calendar.csv"), "--section", "A", "--grade", "K2",
            "--from", "10", "--to", "11", *extra]  # fmt: skip


def test_apply_with_no_database_stops_and_says_so_while_the_sql_file_needs_none(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from engine.cli import app

    monkeypatch.delenv("DATABASE_URL", raising=False)
    refused = CliRunner().invoke(app, [*_args(tmp_path), "--apply"])
    assert refused.exit_code != 0 and "no database" in refused.output.lower()
    out = tmp_path / "rows.sql"
    wrote = CliRunner().invoke(app, [*_args(tmp_path), "--sql", str(out)])
    assert wrote.exit_code == 0 and out.read_text().count("on conflict do nothing") >= 5


def test_a_fortnight_listed_under_two_months_loads_as_one_file_and_each_line_says_its_block(
    tmp_path, monkeypatch
):
    from typer.testing import CliRunner

    from engine.cli import app

    monkeypatch.delenv("DATABASE_URL", raising=False)
    out = tmp_path / "rows.sql"
    run = CliRunner().invoke(
        app, [*_args(tmp_path), "--sql", str(out), "--undecided", "2026-12-07=graph and calendar disagree"]
    )
    assert run.exit_code == 0, run.output
    assert [p.name for p in tmp_path.glob("rows*.sql")] == ["rows.sql"]
    text = out.read_text()
    assert "(November block)" in text and "(December block)" in text and "insert into session" in text
    assert "week A from the November block" in run.output and "conflict" not in run.output


# ---- privacy: this repository is public, so staff appear by role and never by a typed name

SEED = REPO / "supabase/seed"


def test_no_committed_timetable_file_names_a_member_of_staff_and_the_capture_says_it_redacted():
    named = re.compile(r"\b[A-Z][a-z]+ (?:Sir|Madam|Ma'am)\b")
    files = [
        *TABS.glob("*"),
        *SEED.glob("k2_timetable_fn10_fn17*.sql"),
        *(REPO / "packages/engine/tests/fixtures").glob("k2_timetable_*.json"),
    ]
    assert len(files) >= 8
    assert [f.name for f in files if named.search(f.read_text())] == []
    capture = json.loads((TABS / "capture.json").read_text())
    assert capture["redaction"]["staff_names_replaced_by_role"] >= 1 and "name" not in capture["redaction"]


def test_the_sql_header_checksums_are_of_the_raw_committed_bytes():
    import hashlib

    head = (SEED / "k2_timetable_fn10_fn17.sql").read_text()
    for name in ("frame.csv", "planner.csv", "calendar.csv"):
        want = hashlib.sha256((TABS / name).read_bytes()).hexdigest()
        assert f"-- source {name}: sha256 {want}" in head, name


# ---- before and after counts (the server run prints them)


@needs_db
def test_the_counts_after_a_load_are_what_the_class_holds_and_a_second_load_leaves_them_as_they_were(conn):
    k, target = a_target(conn)
    first = sq.apply(conn, loaded(), target)
    after = sq.counts(conn)
    assert after["session"] == first["session"] == len(loaded().sessions) and after["timetable_slot"] == 150
    assert sq.apply(conn, loaded(), target) == dict.fromkeys(first, 0) and sq.counts(conn) == after


def test_the_report_prints_the_rows_before_and_after_when_there_is_a_database(capsys):
    from engine.w2_print import cli_timetable as cli

    plan = loaded()
    added = {t: n for t, n in ld.summary(plan).items()}
    after = {t: n + 5 for t, n in added.items()}
    cli._report(plan, (added, after), 3, True, "heading")
    out = capsys.readouterr().out
    assert "before" in out and "after" in out
    n, after_n = added["session"], after["session"]
    assert re.search(rf"session\s+{n}\s+{n}\s+{after_n - n}\s+{after_n}\b", out), out
