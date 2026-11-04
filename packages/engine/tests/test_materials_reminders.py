"""The materials list's reminders (task M1-10; D-070: "2 weeks before and 1 week before"; D-072: a date that is not a
working day moves to the last working day before it; M1-09 design: if that day has passed, at once). Pure dates, no
database: the lead times and the holidays are handed in, as the settings and the calendar hand them in live."""

import datetime as dt

from engine.w2_print import materials_reminders as r

VACATION = {dt.date(2026, 11, 4) + dt.timedelta(days=i) for i in range(14)}  # 4-17 Nov 2026
FIRST = dt.date(2026, 11, 23)  # FN10, a Monday


def test_two_weeks_and_one_week_before_the_first_day_a_material_is_needed():
    got = r.reminder_dates(FIRST, [2, 1], today=dt.date(2026, 10, 1), holidays=set())
    assert [(x.weeks_before, x.due_on) for x in got] == [
        (2, dt.date(2026, 11, 9)),
        (1, dt.date(2026, 11, 16)),
    ]
    assert not any(x.at_once for x in got)


def test_a_date_in_the_vacation_moves_to_the_last_working_day_before_it():
    got = r.reminder_dates(FIRST, [2, 1], today=dt.date(2026, 10, 1), holidays=VACATION)
    assert [x.due_on for x in got] == [
        dt.date(2026, 11, 3),
        dt.date(2026, 11, 3),
    ]  # Tuesday, before the break


def test_a_weekend_moves_to_the_friday_before():
    got = r.reminder_dates(dt.date(2026, 12, 21), [2], today=dt.date(2026, 10, 1), holidays=set())
    assert got[0].due_on == dt.date(2026, 12, 7)  # 7 Dec is a Monday: stays
    got = r.reminder_dates(dt.date(2026, 12, 19), [2], today=dt.date(2026, 10, 1), holidays=set())
    assert got[0].due_on == dt.date(2026, 12, 4)  # 5 Dec is a Saturday: Friday 4 Dec


def test_a_day_already_past_is_sent_at_once_today_and_says_so():
    got = r.reminder_dates(FIRST, [2, 1], today=dt.date(2026, 11, 4), holidays=VACATION)
    assert [x.due_on for x in got] == [dt.date(2026, 11, 4)] * 2
    assert all(x.at_once for x in got)


def test_a_day_that_is_today_is_not_late():
    got = r.reminder_dates(FIRST, [2], today=dt.date(2026, 11, 9), holidays=set())
    assert got[0].due_on == dt.date(2026, 11, 9) and not got[0].at_once


def test_the_lead_times_are_the_settings_not_two_and_one():
    got = r.reminder_dates(FIRST, [3, 2, 1], today=dt.date(2026, 10, 1), holidays=set())
    assert [x.weeks_before for x in got] == [3, 2, 1]
