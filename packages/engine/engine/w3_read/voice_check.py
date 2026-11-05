"""How well the K2 voice reader reads (task M1-01, step 5): drafted notes scored against what the educator says they
said, field by field, so the first 20 real notes can be measured (observation model section 8). And a replay: a
typed transcript read against a class exactly as a recording's would be, with no recording and no speech service.

Neither prints a transcript, a name or a recording: only note ids, field names, roll numbers and counts.

The expected file is JSON, a list with one entry per note:
  {"note_id": "...", "activity": "ACT-K2-0002", "above": ["3"], "below": [], "not_willing": [], "absent": ["4"],
   "rest": true}
A list left out is expected empty; `rest` left out is expected false.
"""

import datetime as dt
from dataclasses import dataclass, field

from engine.core import db
from engine.w3_read import voice_intake

FIELDS = ("activity", *voice_intake.LISTS, "rest")


def read_back(found: voice_intake.Resolved) -> dict:
    """What the reader made of a note, in the expected file's own shape."""
    rest = found.draft.line("rest")
    out: dict = {"activity": found.activity, "rest": bool(rest and rest.said)}
    for section in voice_intake.LISTS:
        out[section] = sorted(str(n) for n in found.numbers(section))
    return out


def _expected(entry: dict) -> dict:
    out = {"activity": entry.get("activity"), "rest": bool(entry.get("rest", False))}
    for section in voice_intake.LISTS:
        out[section] = sorted(str(n) for n in entry.get(section, []))
    return out


@dataclass
class Score:
    notes: int = 0
    whole: int = 0  # notes read right in every field
    unread: int = 0  # notes the reader could not read (a problem it raised)
    missing: list[str] = field(default_factory=list)  # note ids in the file with no drafted note
    agreed: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    wrong: dict[str, list[str]] = field(default_factory=dict)  # note id → the fields read wrong

    def lines(self) -> list[str]:
        out = [f"notes scored: {self.notes}", f"read right in every field: {self.whole} of {self.notes}"]
        out += [f"  {f}: {self.agreed[f]} of {self.notes}" for f in FIELDS]
        out.append(f"notes the reader could not read: {self.unread}")
        out += [f"  {note}: {', '.join(fields)}" for note, fields in self.wrong.items()]
        out += [f"not a drafted note: {note}" for note in self.missing]
        return out


def score(conn: db.Conn, expected: list[dict]) -> Score:
    out = Score()
    for entry in expected:
        note = conn.execute(
            "select * from pii.educator_note where id = %s and transcript is not null",
            (voice_intake.valid_id(str(entry["note_id"])),),
        ).fetchone()
        if note is None:
            out.missing.append(str(entry["note_id"]))
            continue
        found = voice_intake.resolve(conn, note)
        got, want = read_back(found), _expected(entry)
        wrong = [f for f in FIELDS if got[f] != want[f]]
        out.notes += 1
        out.whole += not wrong
        out.unread += found.blocked
        for f in FIELDS:
            out.agreed[f] += f not in wrong
        if wrong:
            out.wrong[str(note["id"])] = wrong
    return out


def replay(
    conn: db.Conn, class_id: str, transcript: str, received: dt.datetime | None = None
) -> voice_intake.Resolved:
    """A typed transcript read against a class as a note's would be. Nothing is written."""
    note = {
        "transcript": transcript,
        "class_id": voice_intake.valid_id(class_id),
        "received_at": received or db.one(conn, "select now() as n")["n"],
    }
    return voice_intake.resolve(conn, note)


def replay_lines(found: voice_intake.Resolved) -> list[str]:
    """The draft as numbers and problems; a free sentence or an incident by its length, never its words."""
    out = [f"taught on: {found.taught_on.isoformat()}", f"activity: {found.activity or '(not found)'}"]
    for line in found.draft.lines:
        if line.text is not None:
            out.append(f"{line.section}: ({len(line.text.split())} words)")
        elif line.section not in ("activity",):
            out.append(
                f"{line.section}: {', '.join(map(str, line.numbers)) or ('yes' if line.said else '-')}"
            )
    out += [f"PROBLEM {p}" for p in [*found.draft.problems, *found.problems]]
    out += [f"PROBLEM {line.section}: {p}" for line in found.draft.lines for p in line.problems]
    out.append(f"count: {found.count_line()}")
    return out
