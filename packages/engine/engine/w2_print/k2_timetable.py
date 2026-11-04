"""The K2 timetable, generated from the plans (M1-06). Pure: no database, no network, no model.

Three steps, each a plain function:
  read_frame     the school's two-week frame (which subject sits in which period) -> cells
  read_plan_row  one fortnight of the Monthly Planner -> the lines under each subject heading
  generate       lay the frame over the school's dated days and copy each subject's lines into its periods

A line is only ever copied from the planner, never written. A period the school left empty stays empty; a planner
line with no period is listed in `no_slot`. The same inputs always give the same cells.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Vocabulary:
    """How the school's sheets are read. The words are the `timetable.vocabulary` config row, never code."""

    fixed_rows: tuple[str, ...]
    specialist: frozenset[str]
    subject_phrases: tuple[tuple[str, str], ...]
    plan_key_of_subject: dict[str, str]
    plan_headings: dict[str, str]
    header_keys: tuple[str, ...]
    glue_words: frozenset[str]

    @classmethod
    def from_config(cls, v: dict) -> "Vocabulary":
        return cls(
            tuple(v["fixed_rows"]),
            frozenset(v["specialist"]),
            tuple((p, s) for p, s in v["subject_phrases"]),
            dict(v["plan_key_of_subject"]),
            dict(v["plan_headings"]),
            tuple(v["header_keys"]),
            frozenset(v["glue_words"]),
        )


@dataclass(frozen=True)
class FrameCell:
    week: str
    weekday: int
    start: str
    end: str
    kind: str  # fixed | subject | specialist | empty
    subject: str | None
    text: str


@dataclass(frozen=True)
class Frame:
    cells: list[FrameCell]


@dataclass(frozen=True)
class Plan:
    fortnight: int
    lines: dict[str, list[str]]


@dataclass(frozen=True)
class Filled:
    date: date
    week: str
    weekday: int
    start: str
    kind: str  # fixed | subject | specialist | empty | header
    subject: str | None
    text: str
    source: str | None = None


@dataclass
class Draft:
    cells: list[Filled] = field(default_factory=list)
    no_slot: list[tuple[str, str]] = field(default_factory=list)


def _one_line(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _subject_of(text: str, vocab: Vocabulary) -> str | None:
    low = text.lower()
    if low.startswith(vocab.fixed_rows):
        return None
    for phrase, subject in vocab.subject_phrases:
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            return subject
    return "other"


def read_frame(rows: list[dict], vocab: Vocabulary) -> Frame:
    cells: list[FrameCell] = []
    for row in rows:
        start, _, end = (_one_line(row["time"]) + " - ").partition(" - ")
        for week in ("A", "B"):
            for i, raw in enumerate(row[week]):
                text = _one_line(raw)
                subject = _subject_of(text, vocab) if text else None
                kind = "empty" if not text else "fixed" if subject is None else "subject"
                if subject in vocab.specialist:
                    kind = "specialist"
                cells.append(FrameCell(week, i + 1, start, end.strip(" -"), kind, subject, text))
    return Frame(cells)


def _items(lines: list[str], vocab: Vocabulary) -> list[str]:
    items: list[str] = []
    glue = False
    for line in lines:
        line = _one_line(re.sub(r"^\d+\.\s*", "", line))
        if not line:
            continue
        if glue and items:
            items[-1] = f"{items[-1]} {line}".strip()
        else:
            items.append(line)
        glue = line.endswith(("-", ":")) or line.lower() in vocab.glue_words
    return items


def read_plan_row(cells: list[str], fortnight: int, vocab: Vocabulary) -> Plan:
    sections: dict[str, list[str]] = {}
    for cell in cells:
        key = None
        for raw in cell.split("\n"):
            head = vocab.plan_headings.get(_one_line(raw).rstrip(":").lower())
            if head:
                key = head
                sections.setdefault(key, [])
            elif key and _one_line(raw):
                sections[key].append(raw)
    return Plan(fortnight, {k: _items(v, vocab) for k, v in sections.items()})


def _weeks(days: list[date]) -> dict[date, str]:
    mondays = sorted({d.toordinal() - d.weekday() for d in days})
    if len(mondays) > 2:
        raise ValueError("a fortnight is two weeks; got days from more")
    return {d: "AB"[mondays.index(d.toordinal() - d.weekday())] for d in days}


def _halves(items: list[str]) -> dict[str, list[str]]:
    cut = math.ceil(len(items) / 2)
    return {"A": items[:cut], "B": items[cut:] or items[:cut]}


def _fill_days(
    frame: Frame, plan: Plan, days: list[date], week_of: dict[date, str], vocab: Vocabulary
) -> tuple[list[Filled], set[str]]:
    grid: dict[tuple[str, int], list[FrameCell]] = {}
    for c in frame.cells:
        grid.setdefault((c.week, c.weekday), []).append(c)
    turn: dict[tuple[str, str], int] = {}
    cells: list[Filled] = []
    used: set[str] = set()
    for d in sorted(days):
        week = week_of[d]
        for c in grid.get((week, d.weekday() + 1), []):
            key = vocab.plan_key_of_subject.get(c.subject or "", "")
            half = _halves(plan.lines.get(key, [])).get(week, [])
            source, text = None, c.text
            if half and c.kind in ("subject", "specialist"):
                n = turn.get((week, key), 0)
                turn[(week, key)] = n + 1
                source = half[n % len(half)]
                text = f"{c.text}: {source}"
                used.add(source)
            cells.append(Filled(d, week, c.weekday, c.start, c.kind, c.subject, text, source))
    return cells, used


def _header_cells(
    plan: Plan, days: list[date], week_of: dict[date, str], vocab: Vocabulary
) -> tuple[list[Filled], set[str]]:
    cells: list[Filled] = []
    used: set[str] = set()
    for week in "AB":
        in_week = [d for d in days if week_of[d] == week]
        if not in_week:
            continue
        first = min(in_week)
        for key in vocab.header_keys:
            for line in _halves(plan.lines.get(key, []))[week]:
                cells.append(
                    Filled(first, week, first.weekday() + 1, "00:00", "header", key, f"{key}: {line}", line)
                )
                used.add(line)
    return cells, used


def generate(frame: Frame, plan: Plan, days: list[date], vocab: Vocabulary) -> Draft:
    if any(d.weekday() > 4 for d in days):
        raise ValueError("a school day here is Monday to Friday")
    week_of = _weeks(days)
    cells, used = _fill_days(frame, plan, days, week_of, vocab)
    head, head_used = _header_cells(plan, days, week_of, vocab)
    used |= head_used
    no_slot = [(k, ln) for k, v in plan.lines.items() for ln in v if ln not in used]
    return Draft(cells + head, no_slot)


def changed(old: Draft, new: Draft) -> list[Filled]:
    was = {(c.date, c.start, c.kind, c.subject): c.text for c in old.cells}
    return [c for c in new.cells if was.get((c.date, c.start, c.kind, c.subject)) != c.text]
