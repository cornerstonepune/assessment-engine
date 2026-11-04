"""The day a K2 spoken note is about (engine/w3_read/voice_day.py), read from typed transcripts."""

from engine.w3_read import voice_day
from engine.w3_read import voice_note as vn


def test_the_date_at_the_start_of_the_days_first_note_is_read_and_never_lands_in_the_future():
    import datetime as dt

    thursday = dt.date(2026, 11, 5)
    assert vn.read("Wednesday. Activity 7. Above 3.").day == ("weekday", 2)
    assert voice_day.taught_on(("weekday", 2), thursday) == dt.date(2026, 11, 4)
    assert voice_day.taught_on(("weekday", 3), thursday) == thursday
    assert vn.read("3rd November. Activity 7. Above 3.").day == ("date", 3, 11)
    assert voice_day.taught_on(("date", 3, 11), thursday) == dt.date(2026, 11, 3)
    assert voice_day.taught_on(("date", 30, 12), thursday) == dt.date(
        2025, 12, 30
    )  # said in Nov: last December
    assert vn.read("Budhvar. Activity 7. Above 3.").day == ("weekday", 2)
    assert voice_day.taught_on(None, thursday) == thursday  # no day said: the day it reached us
    assert voice_day.taught_on(("date", 31, 2), thursday) is None


def test_a_date_half_said_is_could_not_read():
    d = vn.read("November. Activity 7. Above 3.")
    assert "could not read the date: a day and a month are both needed" in d.problems


def test_the_problems_about_the_date_are_named_apart_so_picking_the_date_fixes_them():
    d = vn.read("November. Activity 7. Above 3. Below 3.")
    assert d.day_problems == ("could not read the date: a day and a month are both needed",)
    assert set(d.day_problems) < set(d.problems)  # the child in two lists is not about the date
    assert vn.read("Activity 7. Above 3.").day_problems == ()
