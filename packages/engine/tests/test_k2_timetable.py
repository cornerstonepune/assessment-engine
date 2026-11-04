"""M1-06: the K2 timetable generated from the plans (goals/m1-06-plan-today.yaml). The inputs are the school's own tabs,
exactly as the Sheets connector returned them on 2026-11-04 (`supabase/seed/k2_tabs_2026_11_04/`): the Time table, the
Monthly Planner, the calendar. They hold no child data. Fortnight 10 is listed twice in the planner; where a test needs one
row it says which (row 2, the December block)."""

import json
from collections import Counter
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from engine.w2_print import k2_timetable as tt
from engine.w2_print import k2_timetable_load as ld

REPO = Path(__file__).resolve().parents[3]
TABS = REPO / "supabase/seed/k2_tabs_2026_11_04"
VOCAB = tt.Vocabulary.from_config(
    next(
        c["value"]
        for c in json.loads((REPO / "supabase/seed/config.json").read_text())["config"]
        if c["key"] == "timetable.vocabulary"
    )
)
SPANS = json.loads((TABS / "frame_spans.json").read_text())
FRAME = ld.read_frame_csv((TABS / "frame.csv").read_text(), VOCAB, SPANS)
PLAN = ld.read_planner_csv((TABS / "planner.csv").read_text(), VOCAB).halves[10][1][
    1
]  # the December block's row
DAYS = [
    date(2026, 11, 23) + timedelta(d) for d in range(14) if (date(2026, 11, 23) + timedelta(d)).weekday() < 5
]


def test_the_frame_is_fifteen_rows_by_two_weeks_of_five_days():
    cells = FRAME.cells
    assert len(cells) == 15 * 10
    assert {c.week for c in cells} == {"A", "B"} and {c.weekday for c in cells} == {1, 2, 3, 4, 5}


def test_seven_rows_are_fixed_every_day_and_eight_are_subject_slots():
    assert len({c.start for c in FRAME.cells if c.kind == "fixed"}) == 7
    assert len({c.start for c in FRAME.cells if c.kind != "fixed"}) == 8


def test_cells_the_school_merged_across_the_week_are_filled_for_every_day():
    for row in ("09:10", "11:45"):  # fruit break, lunch: merged Monday to Friday in week B
        b = [c for c in FRAME.cells if c.week == "B" and c.start == row]
        assert len(b) == 5 and all(c.kind == "fixed" and c.text for c in b), row


def test_an_activity_merged_over_two_periods_is_one_and_the_second_period_takes_no_line():
    carried = {(c.week, c.weekday, c.start) for c in FRAME.cells if c.continues}
    assert carried == {(w, wd, s) for w in "AB" for wd, s in ((5, "10:40"), (3, "11:20"), (2, "12:40"))}
    d = tt.generate(FRAME, PLAN, DAYS, VOCAB)
    assert all(
        c.source is None for c in d.cells if c.kind != "header" and (c.week, c.weekday, c.start) in carried
    )


def test_the_cells_the_school_left_empty_stay_empty_for_a_person():
    empty = [c for c in FRAME.cells if c.kind == "empty"]
    assert len(empty) == 6 and {c.week for c in empty} == {"A"}


def test_week_b_periods_per_subject_are_counted_from_the_timetable_itself():
    n = Counter(c.subject for c in FRAME.cells if c.week == "B" and c.kind in ("subject", "specialist"))
    assert (n["math"], n["english"], n["reading"], n["story"], n["phonics"], n["hindi"]) == (5, 4, 4, 3, 2, 2)
    assert (n["general_awareness"], n["me_time"], n["rhymes"], n["music"], n["music_guest"], n["art"]) == (
        2,
        2,
        2,
        1,
        1,
        2,
    )


def test_physical_education_and_guest_music_are_marked_as_led_by_a_specialist():
    assert {c.subject for c in FRAME.cells if c.kind == "specialist"} == {"pe", "music_guest"}


def test_the_december_row_of_fortnight_ten_is_split_by_its_own_headings():
    assert PLAN.fortnight == 10
    assert PLAN.lines["stories"] == ["Kisan aur bhalu", "Walking together"]
    assert PLAN.lines["block_room"] == ["Smelling Bottles"]
    assert PLAN.lines["gross_motor"] == ["Walking Backward On Toes/Heels"]
    assert PLAN.lines["brave_day"] == ["Try something you think is difficult"]


def test_stories_follow_last_years_hand_filled_pattern_item_one_in_week_a_item_two_in_week_b():
    d = tt.generate(FRAME, PLAN, DAYS, VOCAB)
    story = {(c.week, c.weekday): c.text for c in d.cells if c.subject == "story" and c.source}
    assert story and all("Kisan aur bhalu" in t for (w, _), t in story.items() if w == "A")
    assert all("Walking together" in t for (w, _), t in story.items() if w == "B")


def test_every_filled_line_is_a_planner_line_of_its_own_subject_never_written_by_the_system():
    allowed = {line for lines in PLAN.lines.values() for line in lines}
    for c in tt.generate(FRAME, PLAN, DAYS, VOCAB).cells:
        if c.source:
            assert c.source in allowed and c.source in c.text, f"{c.date} {c.start}: {c.source!r}"


def test_every_planner_line_is_placed_or_listed_as_having_no_slot():
    d = tt.generate(FRAME, PLAN, DAYS, VOCAB)
    placed = {c.source for c in d.cells if c.source}
    assert {line for lines in PLAN.lines.values() for line in lines} - placed == {
        line for _, line in d.no_slot
    }
    assert {s for s, _ in d.no_slot} >= {"block_room", "gross_motor"}


def test_a_holiday_leaves_no_cell_and_the_other_days_keep_their_weekday():
    off = date(2026, 11, 25)
    d = tt.generate(FRAME, PLAN, [x for x in DAYS if x != off], VOCAB)
    assert off not in {c.date for c in d.cells}
    thu = [c for c in d.cells if c.date == date(2026, 11, 26) and c.start == "09:40"]
    assert thu and thu[0].kind == "empty"


def test_an_unchanged_week_regenerates_identically_and_one_changed_line_changes_only_its_cells():
    a, b = tt.generate(FRAME, PLAN, DAYS, VOCAB), tt.generate(FRAME, PLAN, DAYS, VOCAB)
    assert tt.changed(a, b) == []
    edited = replace(
        PLAN,
        lines={
            **PLAN.lines,
            "math": [x.replace("Addition - orally", "Addition - with beads") for x in PLAN.lines["math"]],
        },
    )
    diff = tt.changed(a, tt.generate(FRAME, edited, DAYS, VOCAB))
    assert diff and all(x.subject == "math" for x in diff)


def test_a_day_two_sources_disagree_about_gets_no_line_and_is_listed():
    held = {date(2026, 12, 4): "the sheet's Fortnight 10 and 11 dates disagree"}
    d = tt.generate(FRAME, PLAN, DAYS, VOCAB, undecided=held)
    assert date(2026, 12, 4) not in {c.date for c in d.cells} and d.undecided == [
        (date(2026, 12, 4), held[date(2026, 12, 4)])
    ]
    assert {c.week for c in d.cells if c.date == date(2026, 12, 1)} == {"B"}


def test_the_generator_never_reads_where_names_are_kept():
    assert "pii" not in Path(tt.__file__).read_text()
