"""Loading the school's own tabs into the six timetable tables (M1-06 part 2).

Reading is pure: the Time table tab, the Monthly Planner tab and the Pre-Primary calendar tab, each as the CSV a person
exports from it, become a `Load` (the rows of `fortnight`, `school_day`, `period`, `timetable_slot`, `plan_entry` and
`session` for Fortnight N to M). The rows come from `k2_timetable.generate`; nothing here writes a line the school did
not. Writing is one list of INSERT statements, all `on conflict do nothing`, so it is the same whether `apply` runs it
on a copy or `sql_file` hands it to a person to run on live; run twice, the second adds nothing.
A day or fortnight two sources disagree about, and a planner line with no period, are listed, never chosen.
"""

import csv
import io
import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

from engine.core import db
from engine.w2_print import k2_timetable as tt


@dataclass(frozen=True)
class CalDay:
    kind: str  # teaching | holiday
    note: str | None


@dataclass(frozen=True)
class Calendar:
    days: dict[date, CalDay]
    fortnights: dict[int, tuple[date, date]]
    conflicts: list[tuple[int, str]]


@dataclass(frozen=True)
class Planner:
    plans: dict[int, tt.Plan]
    conflicts: list[tuple[int, str]]


@dataclass(frozen=True)
class Period:
    ord: int
    start: str
    end: str
    label: str
    fixed: bool


@dataclass(frozen=True)
class PlanEntry:
    fortnight: int
    key: str
    ord: int
    text: str
    activity_code: str | None = None


@dataclass(frozen=True)
class Session:
    day: date
    start: str
    subject: str | None
    text: str
    key: str | None
    ord: int | None


@dataclass(frozen=True)
class Target:
    grade: str
    section: str
    year: str
    tenant: str


@dataclass(frozen=True)
class Load:
    fortnights: list[tuple[int, date, date]] = field(default_factory=list)
    school_days: list[tuple[date, str, str | None]] = field(default_factory=list)
    periods: list[Period] = field(default_factory=list)
    slots: list[tuple[str, int, str, str, str | None, str]] = field(
        default_factory=list
    )  # week, weekday, start, kind, subject, text
    plan_entries: list[PlanEntry] = field(default_factory=list)
    sessions: list[Session] = field(default_factory=list)
    no_slot: list[tuple[int, str, str]] = field(default_factory=list)
    undecided: list[tuple[date, str]] = field(default_factory=list)
    missing_plan: list[tuple[int, str]] = field(default_factory=list)
    conflicts: list[tuple[int, str]] = field(default_factory=list)


def _rows(text: str) -> list[list[str]]:
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]


def _cells(row: list[str], lo: int, hi: int) -> list[str]:
    return [(row[i] if i < len(row) else "") for i in range(lo, hi)]


def read_frame_csv(text: str, vocab: tt.Vocabulary) -> tt.Frame:
    """The Time table tab: a time in the first column, week A in columns B to F, week B in I to M."""
    rows = []
    for r in _rows(text):
        m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*(?:-\s*(\d{1,2}):(\d{2}))?\s*$", r[0])
        if m:
            h, mi, h2, mi2 = m.groups()
            time = f"{int(h):02d}:{mi}" + (f" - {int(h2):02d}:{mi2}" if h2 else "")
            rows.append({"time": time, "A": _cells(r, 1, 6), "B": _cells(r, 8, 13)})
    return tt.read_frame(rows, vocab)


def read_planner_csv(text: str, vocab: tt.Vocabulary) -> Planner:
    """The Monthly Planner tab: a row `Fortnight N` and a cell for each heading. A fortnight listed twice is a conflict
    for a person and loads neither row."""
    seen: dict[int, list[list[str]]] = {}
    for r in _rows(text):
        m = re.match(vocab.planner_row, r[0].strip())
        if m:
            seen.setdefault(int(m.group(1)), []).append(_cells(r, 1, 8))
    plans = {n: tt.read_plan_row(rows[0], n, vocab) for n, rows in seen.items() if len(rows) == 1}
    return Planner(
        plans,
        [
            (n, "listed twice in the Monthly Planner: neither row is loaded")
            for n, rows in sorted(seen.items())
            if len(rows) > 1
        ],
    )


def _day_of(cell: str) -> date | None:
    try:
        return datetime.strptime(cell.strip(), "%A, %B %d, %Y").date()
    except ValueError:
        return None


def read_calendar_csv(text: str, vocab: tt.Vocabulary) -> Calendar:
    """The Pre-Primary calendar tab: date, fortnight label, events, school holidays. A holiday marked for other grades
    only is not one here; a tentative one is, and says so."""
    days: dict[date, CalDay] = {}
    fortnights: dict[int, tuple[date, date]] = {}
    conflicts: list[tuple[int, str]] = []
    for r in _rows(text):
        day = _day_of(r[0])
        if not day:
            continue
        label, holiday = _cells(r, 1, 2)[0], _cells(r, 3, 4)[0].strip()
        if holiday and not any(mark in holiday for mark in vocab.other_grade_marks):
            tentative = any(m in holiday.lower() for m in vocab.tentative_marks)
            days[day] = CalDay(
                "holiday",
                holiday + ("" if not tentative or "tentative" in holiday.lower() else " (tentative)"),
            )
        else:
            days[day] = CalDay("teaching", f"Holiday for other grades only: {holiday}" if holiday else None)
        m = re.match(vocab.fortnight_label, label.strip())
        if m:
            n, end = int(m.group(1)), day + timedelta(days=13)
            fortnights[n] = (day, end)
            said = re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3})", label)
            if said and (int(said[-1][0]), said[-1][1].lower()) != (end.day, end.strftime("%b").lower()):
                conflicts.append(
                    (
                        n,
                        f"the label ends {said[-1][0]} {said[-1][1]}, two weeks from its start is {end:%d %b}",
                    )
                )
    return Calendar(days, fortnights, conflicts)


def _periods(frame: tt.Frame) -> list[Period]:
    seen: dict[str, tuple[str, list[tt.FrameCell]]] = {}
    for c in frame.cells:
        seen.setdefault(c.start, (c.end, []))[1].append(c)
    out = []
    for i, (start, (end, cells)) in enumerate(seen.items(), 1):
        fixed = all(c.kind == "fixed" for c in cells)
        label = next(c.text for c in cells) if fixed else f"{start} - {end}".strip(" -")
        out.append(Period(i, start, end, label, fixed))
    return out


def build(
    frame: tt.Frame, planner: Planner, cal: Calendar, vocab: tt.Vocabulary, first: int, last: int,
    undecided: dict[date, str] | None = None,
) -> Load:  # fmt: skip
    held = undecided or {}
    load = Load(periods=_periods(frame), conflicts=[*planner.conflicts, *cal.conflicts])
    load.slots.extend((c.week, c.weekday, c.start, c.kind, c.subject, c.text) for c in frame.cells)
    for n in range(first, last + 1):
        if n not in cal.fortnights:
            load.conflicts.append((n, "no dates for this fortnight in the calendar: nothing loaded"))
            continue
        start, end = cal.fortnights[n]
        load.fortnights.append((n, start, end))
        window = [start + timedelta(d) for d in range(14) if (start + timedelta(d)).weekday() < 5]
        for d in window:
            cd = cal.days.get(d, CalDay("teaching", None))
            why = held.get(d)
            load.school_days.append((d, cd.kind, f"undecided: {why}" if why else cd.note))
        load.undecided.extend((d, held[d]) for d in window if d in held)
        plan = planner.plans.get(n)
        if plan is None:
            load.missing_plan.append((n, "no row for this fortnight in the Monthly Planner"))
            continue
        teaching = [d for d in window if cal.days.get(d, CalDay("teaching", None)).kind == "teaching"]
        draft = tt.generate(
            frame, plan, teaching, vocab, {d: w for d, w in held.items() if d in teaching}, start
        )
        for key, lines in plan.lines.items():
            load.plan_entries.extend(PlanEntry(n, key, i, text) for i, text in enumerate(lines, 1))
        for c in draft.cells:
            if c.kind in ("header", "empty"):
                continue
            key = vocab.plan_key_of_subject.get(c.subject or "")
            at = plan.lines[key].index(c.source) + 1 if key and c.source else None
            load.sessions.append(Session(c.date, c.start, c.subject, c.text, key if at else None, at))
        load.no_slot.extend((n, k, ln) for k, ln in draft.no_slot)
    return load


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def activity_names(conn: db.Conn, band: str = "K2") -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in conn.execute(
        "select code, name from activity where band = %s order by code", (band,)
    ).fetchall():
        out.setdefault(norm(r["name"]), []).append(r["code"])
    return out


def link_activities(load: Load, names: dict[str, list[str]]) -> Load:
    """A planner line names an activity when its words are exactly one activity's name: by code, never a model. A line
    that fits two activities or none stays plain."""
    entries = [
        replace(
            e,
            activity_code=(names.get(norm(e.text)) or [None])[0]
            if len(names.get(norm(e.text), [])) == 1
            else None,
        )
        for e in load.plan_entries
    ]
    return replace(load, plan_entries=entries)


def summary(load: Load) -> dict[str, int]:
    return {
        "fortnight": len(load.fortnights), "school_day": len(load.school_days), "period": len(load.periods),
        "timetable_slot": len(load.slots), "plan_entry": len(load.plan_entries), "session": len(load.sessions),
    }  # fmt: skip


def fortnight_of(load: Load, day: date) -> int:
    """The fortnight a day falls in."""
    return next(n for n, a, b in load.fortnights if a <= day <= b)
