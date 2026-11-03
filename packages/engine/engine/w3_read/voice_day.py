"""The day a K2 spoken note is about (task M1-01): the date the educator says at the start of the day's first note.

She may say a weekday ("Wednesday", "Budhvar"), a date ("3rd November"), "today" or "yesterday"; the words are rows
(`supabase/seed/voice_template.json`, `days`). The date is read against the day the note reached us and is never later
than that day. Anything else before "Activity" is "could not read".
"""

import datetime as dt
import re
from dataclasses import dataclass

ORDINAL = re.compile(r"^(\d{1,2})(st|nd|rd|th)$")


@dataclass(frozen=True)
class Days:
    weekdays: dict[str, int]
    months: dict[str, int]
    today: frozenset[str]
    yesterday: frozenset[str]
    filler: frozenset[str]  # words that may stand beside a date ("the", "date") and the template's own filler

    @classmethod
    def from_rows(cls, rows: dict, filler: set[str]) -> "Days":
        return cls(
            weekdays=dict(rows["weekday"]),
            months=dict(rows["month"]),
            today=frozenset(rows["today"]),
            yesterday=frozenset(rows["yesterday"]),
            filler=frozenset(rows["filler"]) | frozenset(filler),
        )


def _day_word(w: str, days: Days) -> tuple[str, int] | None:
    if w in days.today:
        return "today", 0
    if w in days.yesterday:
        return "yesterday", 0
    if w in days.weekdays:
        return "weekday", days.weekdays[w]
    if w in days.months:
        return "month", days.months[w]
    m = ORDINAL.match(w)
    if w.isdecimal() or m:
        return "number", int(m.group(1) if m else w)
    return None


def read_day(words: list[tuple[str, str]], days: Days) -> tuple[tuple | None, list[str]]:
    """(lower-cased word, as written) before "Activity" → the day she said, if any, and what could not be read:
    ("today",), ("yesterday",), ("weekday", 0-6) or ("date", day, month)."""
    said: dict[str, int] = {}
    problems = []
    for w, written in words:
        hit = _day_word(w, days)
        if hit and hit[0] not in said:
            said[hit[0]] = hit[1]
        elif hit or w not in days.filler:
            problems.append(f"could not read '{written}'")
    if "month" in said and "number" in said:
        return ("date", said["number"], said["month"]), problems
    if "month" in said or "number" in said:
        return None, [*problems, "could not read the date: a day and a month are both needed"]
    for kind in ("today", "yesterday"):
        if kind in said:
            return (kind,), problems
    return (("weekday", said["weekday"]) if "weekday" in said else None), problems


def taught_on(day: tuple | None, received: dt.date) -> dt.date | None:
    """The date she said, read against the day the note reached us; never later than that day."""
    if day is None or day[0] == "today":
        return received
    if day[0] == "yesterday":
        return received - dt.timedelta(days=1)
    if day[0] == "weekday":
        return received - dt.timedelta(days=(received.weekday() - day[1]) % 7)
    try:
        said = dt.date(received.year, day[2], day[1])
    except ValueError:
        return None
    return said if said <= received else said.replace(year=received.year - 1)
