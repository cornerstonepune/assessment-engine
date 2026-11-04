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
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

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
    candidates: dict[int, list[tt.Plan]] = field(
        default_factory=dict
    )  # every row of a fortnight listed twice
    chosen: list[tuple[int, str]] = field(default_factory=list)  # which row a person said to use
    blocks: dict[int, list[str]] = field(
        default_factory=dict
    )  # the planner's heading above each row of a fortnight


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


@dataclass(frozen=True)
class Session:
    day: date
    start: str
    subject: str | None
    text: str
    key: str | None
    ord: int | None
    fortnight: int


@dataclass(frozen=True)
class Target:
    grade: str
    section: str
    year: str
    tenant: str
    source: str = "unspecified"  # which planner file the lines came from, for plan_entry.source


@dataclass
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
    chosen: list[tuple[int, str]] = field(default_factory=list)


def _rows(text: str) -> list[list[str]]:
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]


def _cells(row: list[str], lo: int, hi: int) -> list[str]:
    return [(row[i] if i < len(row) else "") for i in range(lo, hi)]


def _hhmm(text: str) -> str:
    h, _, m = text.strip().partition(":")
    return f"{int(h):02d}:{m}"


def read_frame_csv(text: str, vocab: tt.Vocabulary, spans: list[dict] | None = None) -> tt.Frame:
    """The Time table tab: a time in the first column, week A in columns B to F, week B in I to M. Cells the school
    merged are filled across what they cover. `spans` names an activity merged over several periods: the periods after
    the first carry it on and take no planner line of their own."""
    rows = []
    for r in _rows(text):
        m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*(?:-\s*(\d{1,2}):(\d{2}))?\s*$", r[0])
        if m:
            h, mi, h2, mi2 = m.groups()
            time = f"{int(h):02d}:{mi}" + (f" - {int(h2):02d}:{mi2}" if h2 else "")
            rows.append({"time": time, "A": _cells(r, 1, 6), "B": _cells(r, 8, 13)})
    carries = frozenset((s["week"], s["weekday"], _hhmm(p)) for s in spans or [] for p in s["periods"][1:])
    return tt.read_frame(rows, vocab, carries)


def _headed(header: str, text: str, vocab: tt.Vocabulary) -> str:
    """A cell the school left without its own heading takes the heading its column's title implies."""
    first = next((" ".join(line.split()) for line in text.split("\n") if line.strip()), "")
    synthetic = vocab.headless_columns.get(header)
    return f"{synthetic}\n{text}" if synthetic and first and tt.heading_of(first, vocab)[0] is None else text


def read_planner_csv(text: str, vocab: tt.Vocabulary, use_row: dict[int, int] | None = None) -> Planner:
    """The Monthly Planner tab: a row `Fortnight N`, a cell under each column's title. A fortnight listed twice is a
    conflict for a person and loads neither row, unless a person said which (`use_row`, 1 = the first listed); the rows
    not used stay as `candidates`."""
    chosen = use_row or {}
    seen: dict[int, list[list[str]]] = {}
    blocks: dict[int, list[str]] = {}
    headers: dict[int, str] = {}
    block = ""
    for r in _rows(text):
        if m := re.match(vocab.planner_block, r[0].strip()):
            block = m.group(1)
        elif _cell(r, 1).lower() == vocab.planner_header_cell:
            headers = {i: _cell(r, i).lower() for i in range(1, len(r))}
        elif m := re.match(vocab.planner_row, r[0].strip()):
            blocks.setdefault(int(m.group(1)), []).append(block)
            seen.setdefault(int(m.group(1)), []).append(
                [_headed(headers.get(i, ""), _cell(r, i), vocab) for i in range(1, 11)]
            )
    plans, conflicts, candidates, used = {}, [], {}, []
    for n, rows in sorted(seen.items()):
        if len(rows) == 1:
            plans[n] = tt.read_plan_row(rows[0], n, vocab)
            continue
        candidates[n] = [tt.read_plan_row(row, n, vocab) for row in rows]
        if n in chosen:
            plans[n] = candidates[n][chosen[n] - 1]
            used.append(
                (n, f"listed {len(rows)} times in the Monthly Planner: row {chosen[n]} used, as told")
            )
        else:
            conflicts.append(
                (n, f"listed {len(rows)} times in the Monthly Planner and the rows differ: none is loaded")
            )
    return Planner(plans, conflicts, candidates, used, blocks)


def _cell(row: list[str], i: int) -> str:
    return row[i].strip() if i < len(row) else ""


def _day_of(cell: str, vocab: tt.Vocabulary) -> date | None:
    try:
        return datetime.strptime(cell.strip(), vocab.calendar_date_format).date()
    except ValueError:
        return None


TEACHING = CalDay("teaching", None)


def read_calendar_csv(text: str, vocab: tt.Vocabulary) -> Calendar:
    """The Pre-Primary calendar tab: date, fortnight label, events, school holidays. A holiday marked for other grades
    only is not one here; a holiday the school calls tentative says so in its own words, which are kept."""
    days: dict[date, CalDay] = {}
    fortnights: dict[int, tuple[date, date]] = {}
    conflicts: list[tuple[int, str]] = []
    for r in _rows(text):
        day = _day_of(r[0], vocab)
        if not day:
            continue
        label, holiday = _cell(r, 1), _cell(r, 3)
        for_here = holiday and not any(mark in holiday for mark in vocab.other_grade_marks)
        if for_here:
            days[day] = CalDay("holiday", holiday)
        else:
            days[day] = CalDay("teaching", f"Holiday for other grades only: {holiday}" if holiday else None)
        m = re.match(vocab.fortnight_label, label)
        if m:
            n, end = int(m.group(1)), day + timedelta(days=13)
            fortnights[n] = (day, end)
            said = re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3})", label)
            if said and (int(said[-1][0]), said[-1][1].lower()) != (end.day, end.strftime("%b").lower()):
                d_, mon = said[-1]
                conflicts.append((n, f"the label ends {d_} {mon}, two weeks from its start is {end:%d %b}"))
    return Calendar(days, fortnights, conflicts)


def _h24(start: str, vocab: tt.Vocabulary) -> str:
    """The sheet writes 1:15 for a quarter past one: an hour below the vocabulary row's cut is the afternoon."""
    h = int(start[:2])
    return f"{h + 12 if h < vocab.afternoon_before_hour else h:02d}:{start[3:5]}"


def _periods(frame: tt.Frame, vocab: tt.Vocabulary) -> list[Period]:
    seen: dict[str, tuple[str, list[tt.FrameCell]]] = {}
    for c in frame.cells:
        seen.setdefault(c.start, (c.end, []))[1].append(c)
    out = []
    for i, (start, (end, cells)) in enumerate(seen.items(), 1):
        fixed = all(c.kind == "fixed" for c in cells)
        label = next(c.text for c in cells) if fixed else f"{start} - {end}".strip(" -")
        out.append(Period(i, _h24(start, vocab), _h24(end, vocab) if end else "", label, fixed))
    return out


def build(
    frame: tt.Frame, planner: Planner, cal: Calendar, vocab: tt.Vocabulary, first: int, last: int,
    undecided: dict[date, str] | None = None,
) -> Load:  # fmt: skip
    held = undecided or {}
    load = Load(
        periods=_periods(frame, vocab),
        conflicts=[c for c in [*planner.conflicts, *cal.conflicts] if first <= c[0] <= last],
        chosen=[c for c in planner.chosen if first <= c[0] <= last],
    )
    load.slots.extend(
        (c.week, c.weekday, _h24(c.start, vocab), c.kind, c.subject, c.text) for c in frame.cells
    )
    for n in range(first, last + 1):
        if n not in cal.fortnights:
            load.conflicts.append((n, "no dates for this fortnight in the calendar: nothing loaded"))
            continue
        start, end = cal.fortnights[n]
        if start.weekday() != 0:
            load.conflicts.append((n, f"starts on a {start:%A}, not a Monday: nothing loaded"))
            continue
        load.fortnights.append((n, start, end))
        window = [start + timedelta(d) for d in range(14) if (start + timedelta(d)).weekday() < 5]
        for d in window:
            cd = cal.days.get(d, TEACHING)
            why = held.get(d)
            load.school_days.append((d, cd.kind, f"undecided: {why}" if why else cd.note))
        load.undecided.extend((d, held[d]) for d in window if d in held)
        plan = planner.plans.get(n)
        if plan is None:
            load.missing_plan.append((n, "no row for this fortnight in the Monthly Planner"))
            continue
        teaching = [d for d in window if cal.days.get(d, TEACHING).kind == "teaching"]
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
            load.sessions.append(
                Session(c.date, _h24(c.start, vocab), c.subject, c.text, key if at else None, at, n)
            )
        load.no_slot.extend((n, k, ln) for k, ln in draft.no_slot)
    return load


def summary(load: Load) -> dict[str, int]:
    return {
        "fortnight": len(load.fortnights), "school_day": len(load.school_days), "period": len(load.periods),
        "timetable_slot": len(load.slots), "plan_entry": len(load.plan_entries), "session": len(load.sessions),
    }  # fmt: skip
