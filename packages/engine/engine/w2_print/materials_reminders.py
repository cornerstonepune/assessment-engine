"""When the materials list's reminders fall (task M1-10; D-070, D-072). Pure dates: the lead times (a setting) and the
holidays (the school's calendar) are handed in. A reminder is due the given number of weeks before the first day a
material is needed; a day that is not a working day moves to the last working day before it; one already past is due
today, and says so."""

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class Reminder:
    weeks_before: int
    due_on: dt.date
    at_once: bool  # the day it should have gone has passed: it goes today


def last_working_day(on: dt.date, holidays: set[dt.date]) -> dt.date:
    """`on` if it is a school working day, else the closest working day before it (Monday to Friday, not a holiday)."""
    while on.weekday() >= 5 or on in holidays:
        on -= dt.timedelta(days=1)
    return on


def reminder_dates(
    first_needed: dt.date, lead_weeks: list[int], today: dt.date, holidays: set[dt.date]
) -> list[Reminder]:
    out = []
    for weeks in lead_weeks:
        due = last_working_day(first_needed - dt.timedelta(weeks=weeks), holidays)
        late = due < today
        out.append(Reminder(weeks, today if late else due, late))
    return out
