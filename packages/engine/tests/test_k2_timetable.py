"""M1-06: the K2 timetable generated from the plans. Written before the code (goals/m1-06-plan-today.yaml).

The inputs are the school's own text, read from the K2 planning sheet on 2026-11-04 (no child data in them):
the two-week frame `F.N - Time table 26-27` and the Fortnight 10 row of `Monthly Planner 2026-27`.
Counts below are what the sheet shows; the frame's empty cells are the school's, left empty for a person to fill.
"""

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from engine.w2_print import k2_timetable as tt

FIX = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[3]
FRAME_ROWS = json.loads((FIX / "k2_frame_fn_2026_27.json").read_text())["rows"]
VOCAB = tt.Vocabulary.from_config(
    next(
        c["value"]
        for c in json.loads((REPO / "supabase/seed/config.json").read_text())["config"]
        if c["key"] == "timetable.vocabulary"
    )
)
PLAN_ROW = json.loads((FIX / "k2_planner_fn10_2026_27.json").read_text())

FN10_DAYS = [
    date(2026, 11, 23) + timedelta(d) for d in range(14) if (date(2026, 11, 23) + timedelta(d)).weekday() < 5
]


def frame():
    return tt.read_frame(FRAME_ROWS, VOCAB)


def plan():
    return tt.read_plan_row(PLAN_ROW["cells"], PLAN_ROW["fortnight"], VOCAB)


def test_the_frame_is_fifteen_rows_by_two_weeks_of_five_days():
    cells = frame().cells
    assert len(cells) == 15 * 10
    assert {c.week for c in cells} == {"A", "B"} and {c.weekday for c in cells} == {1, 2, 3, 4, 5}


def test_seven_rows_are_fixed_every_day_and_eight_are_subject_slots():
    cells = frame().cells
    fixed = {c.start for c in cells if c.kind == "fixed"}
    assert len(fixed) == 7
    assert len({c.start for c in cells if c.kind != "fixed"}) == 8


def test_the_empty_cells_are_kept_empty_for_a_person_eight_in_week_a_and_three_in_week_b():
    empty = Counter(c.week for c in frame().cells if c.kind == "empty")
    assert empty == {"A": 8, "B": 3}


def test_week_b_periods_per_subject_are_counted_from_the_timetable_itself():
    n = Counter(c.subject for c in frame().cells if c.week == "B" and c.kind in ("subject", "specialist"))
    assert (n["math"], n["english"], n["reading"], n["story"], n["phonics"], n["hindi"]) == (5, 4, 4, 3, 2, 2)
    assert (n["general_awareness"], n["me_time"], n["rhymes"], n["music"], n["music_guest"]) == (
        2,
        2,
        2,
        1,
        1,
    )


def test_physical_education_and_guest_music_are_marked_as_led_by_a_specialist():
    spec = {c.subject for c in frame().cells if c.kind == "specialist"}
    assert spec == {"pe", "music_guest"}


def test_a_planner_row_is_split_by_its_own_headings():
    p = plan()
    assert p.fortnight == 10
    assert [s for s in p.lines["stories"]] == ["Kisan aur bhalu", "Walking together"]
    assert p.lines["block_room"] == ["Smelling Bottles"]
    assert p.lines["gross_motor"] == ["Walking Backward On Toes/Heels"]
    assert p.lines["brave_day"] == ["Try something you think is difficult"]


def test_stories_follow_last_years_hand_filled_pattern_item_one_in_week_a_item_two_in_week_b():
    d = tt.generate(frame(), plan(), FN10_DAYS, VOCAB)
    story = {(c.week, c.weekday): c.text for c in d.cells if c.subject == "story"}
    assert all("Kisan aur bhalu" in t for (w, _), t in story.items() if w == "A")
    assert all("Walking together" in t for (w, _), t in story.items() if w == "B")


def test_every_filled_line_is_a_planner_line_of_its_own_subject_never_written_by_the_system():
    p, d = plan(), tt.generate(frame(), plan(), FN10_DAYS, VOCAB)
    allowed = {line for lines in p.lines.values() for line in lines}
    for c in d.cells:
        if c.source:
            assert c.source in allowed, f"{c.date} {c.start}: {c.source!r} is not a planner line"
            assert c.source in c.text


def test_every_planner_line_is_placed_or_listed_as_having_no_slot():
    p, d = plan(), tt.generate(frame(), plan(), FN10_DAYS, VOCAB)
    placed = {c.source for c in d.cells if c.source}
    unplaced = {line for lines in p.lines.values() for line in lines} - placed
    assert unplaced == {line for _, line in d.no_slot}
    assert {s for s, _ in d.no_slot} >= {"block_room", "gross_motor"}


def test_a_holiday_leaves_no_cell_and_the_other_days_keep_their_weekday():
    day_off = date(2026, 11, 25)
    d = tt.generate(frame(), plan(), [x for x in FN10_DAYS if x != day_off], VOCAB)
    assert day_off not in {c.date for c in d.cells}
    thu = [c for c in d.cells if c.date == date(2026, 11, 26) and c.start == "09:40"]
    assert thu and thu[0].kind == "empty"


def test_an_unchanged_week_regenerates_identically_and_one_changed_line_changes_only_its_cells():
    a, b = tt.generate(frame(), plan(), FN10_DAYS, VOCAB), tt.generate(frame(), plan(), FN10_DAYS, VOCAB)
    assert tt.changed(a, b) == []
    cells = list(PLAN_ROW["cells"])
    cells[1] = cells[1].replace("Addition - orally", "Addition - with beads")
    c = tt.generate(frame(), tt.read_plan_row(cells, 10, VOCAB), FN10_DAYS, VOCAB)
    diff = tt.changed(a, c)
    assert diff and all(x.subject.startswith("math") for x in diff)


def test_the_generator_never_reads_where_names_are_kept():
    src = Path(tt.__file__).read_text()
    assert "pii" not in src
