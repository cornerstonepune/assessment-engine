"""A K2 voice note from the phone to a draft the educator confirms (task M1-01, goals/m1-01-voice-intake.yaml).

received (the recording kept, `received_at` the server's clock) → transcribed (Sarvam, `adapters/speech.py`) → drafted:
the words read by code (`voice_note.read`), the activity's spoken number found in the K2 activity list
(`activity.sheet_no`) and every child number in the class's enrolment open that day (`enrolment.roll_no`). A number
with no child, an activity not on the list, is a problem shown to her, never guessed. A note waits for her
`voice.confirm_within_hours` (48); after that it is left unconfirmed and never becomes evidence.
"""

import datetime as dt
import uuid
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from engine.adapters import speech
from engine.core import db, settings
from engine.w3_read import voice_day, voice_note, voice_store

LISTS = ("above", "below", "not_willing", "absent")  # the template's sections that name children


def enabled(conn: db.Conn) -> bool:
    return settings.config(conn, "voice.screens_enabled", False) is True


def recording_enabled(conn: db.Conn) -> bool:
    """Recording, on top of the screens (D-065: no child's voice is kept or sent on until Nimish turns it on). A
    missing row is off."""
    return enabled(conn) and settings.config(conn, "voice.recording_enabled", False) is True


def valid_id(text: str) -> str:
    """An id from a page, refused in words when it is not one (never a database error)."""
    try:
        return str(uuid.UUID(text))
    except ValueError:
        raise voice_store.Refused("Not found.", 404) from None


def staff_of(conn: db.Conn, email: str) -> uuid.UUID:
    sid = db.one(conn, "select public.staff_of_email(%s) as id", (email,))["id"]
    if sid is None:
        raise voice_store.Refused("This sign-in is not on the staff list.", 403)
    return sid


def may_record(conn: db.Conn, staff: uuid.UUID, class_id: str) -> None:
    """She records for a class only while she holds an open grant on it in a role that records
    (`voice.roles_that_record`, a config row). Anyone else is refused, a campus-wide role too unless the row names it."""
    roles = list(settings.config(conn, "voice.roles_that_record", []))
    held = conn.execute(
        "select 1 from staff_role_grant where staff_id = %s and school_class_id = %s and role_code = any(%s)"
        " and valid_from <= current_date and (valid_to is null or valid_to >= current_date)",
        (staff, valid_id(str(class_id)), roles),
    ).fetchone()
    if held is None:
        raise voice_store.Refused("You do not hold this class.", 403)


def receive(conn: db.Conn, email: str, class_id: str, filename: str, data: bytes) -> dict:
    """The recording kept and its row written; the words come after (`transcribe`)."""
    staff = staff_of(conn, email)
    may_record(conn, staff, class_id)
    note_id = uuid.uuid4()
    key = voice_store.key_for(note_id, filename, dt.date.today().year)
    note = conn.execute(
        "insert into pii.educator_note (id, tenant_id, staff_id, class_id, audio_key)"
        " select %s, c.tenant_id, %s, c.id, %s from school_class c where c.id = %s::text::uuid returning *",
        (note_id, staff, key, valid_id(class_id)),
    ).fetchone()
    if note is None:
        raise voice_store.Refused("Not sent. That class is not one of the school's.", 404)
    voice_store.save(
        key, data
    )  # after the row, so a refused note leaves no recording behind (the row rolls back)
    return note


def transcribe(conn: db.Conn, note_id: str, client=None) -> str:
    """The recording turned into words and the note drafted. A failure leaves it received, to be sent again."""
    note = db.one(conn, "select * from pii.educator_note where id = %s", (note_id,))
    terms = [" ".join(words) for words, _ in voice_note.template().phrases]
    heard = speech.transcribe(
        voice_store.read(note["audio_key"]), note["audio_key"].rsplit("/", 1)[1], terms, client
    )
    conn.execute(
        "update pii.educator_note set transcript = %s, status = 'drafted' where id = %s",
        (heard.transcript, note_id),
    )
    return heard.transcript


@dataclass
class Resolved:
    """A draft with its numbers found: what the Confirm page shows."""

    draft: voice_note.Draft
    taught_on: dt.date
    activity: str | None
    children: dict[str, str] = field(default_factory=dict)  # roll number → child id, for every number heard
    enrolled: dict[str, str] = field(default_factory=dict)  # every open roll number of the class that day
    problems: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.draft.blocked or bool(self.problems)

    def numbers(self, section: str) -> tuple[int, ...]:
        line = self.draft.line(section)
        return line.numbers if line else ()

    def count_line(self) -> str:
        named = {str(n) for s in LISTS for n in self.numbers(s)}
        counts = {s: len(self.numbers(s)) for s in LISTS}
        rest = len(set(self.enrolled) - named)
        said = self.draft.line("rest")
        if not (said and said.said):
            return f"{len(named)} named; the other {rest} not seen"
        parts = [f"{n} {s.replace('_', ' ')}" for s, n in counts.items() if n]
        return ", ".join([*parts, f"{rest} as expected"]) + f" = {len(named) + rest}"


def enrolled(conn: db.Conn, class_id: str, day: dt.date) -> dict[str, str]:
    rows = conn.execute(
        "select roll_no, child_id from enrolment where class_id = %s and from_date <= %s"
        " and (to_date is null or to_date >= %s)",
        (class_id, day, day),
    ).fetchall()
    return {r["roll_no"]: str(r["child_id"]) for r in rows}


def activity_of(conn: db.Conn, class_id: str, number: int) -> list[str]:
    """The activity a spoken number names: the class's grade's activity with that number on the K2 team's list."""
    return [
        r["code"]
        for r in conn.execute(
            "select a.code from activity a join school_class c on c.tenant_id = a.tenant_id and c.grade_code = a.band"
            " where c.id = %s and a.sheet_no = %s order by a.code",
            (class_id, str(number)),
        ).fetchall()
    ]


def school_day(conn: db.Conn, at: dt.datetime) -> dt.date:
    """The day a moment falls on by the school's clock (config `school.time_zone`), never the server's: a note heard at
    03:54 in Pune is about that morning, though it is still the night before in UTC."""
    return at.astimezone(ZoneInfo(settings.config(conn, "school.time_zone", "Asia/Kolkata"))).date()


def resolve(conn: db.Conn, note: dict, enrolled_on=None, activities_of=None, day_of=None) -> Resolved:
    """A note's draft with its numbers found. A page reading many notes passes `enrolled_on(class_id, day)`,
    `activities_of(class_id, number)` and `day_of(moment)` answered from rows it fetched at once, so the rule is this
    one and no query is asked per note (engine/w3_read/k2_reads.py)."""
    enrolled_on = enrolled_on or (lambda class_id, day: enrolled(conn, class_id, day))
    activities_of = activities_of or (lambda class_id, number: activity_of(conn, class_id, number))
    day_of = day_of or (lambda at: school_day(conn, at))
    draft = voice_note.read(note["transcript"] or "")
    heard = day_of(note["received_at"])
    day = voice_day.taught_on(draft.day, heard) or heard
    out = Resolved(draft, day, None, enrolled=enrolled_on(note["class_id"], day))
    act = draft.line("activity")
    if act and act.numbers:
        found = activities_of(note["class_id"], act.numbers[0])
        if len(found) == 1:
            out.activity = found[0]
        else:
            out.problems.append(
                f"Activity {act.numbers[0]} is not on the list. Search by number or name."
                if not found
                else f"Activity {act.numbers[0]} is more than one activity on the list: {', '.join(found)}. Pick one."
            )
    for section in LISTS:
        for n in out.numbers(section):
            if str(n) in out.enrolled:
                out.children[str(n)] = out.enrolled[str(n)]
            else:
                out.problems.append(f"#{n} is not in this class. Which child?")
    return out


def classes_of(conn: db.Conn, staff_id: str, day: dt.date) -> list[dict]:
    """The classes she records a note for that day: an open grant in a role that records (`voice.roles_that_record`,
    the rule `may_record` holds her to), on a class whose grade has activities. M0-05's grants, never a class she types."""
    roles = list(settings.config(conn, "voice.roles_that_record", []))
    return conn.execute(
        "select distinct c.id::text as id, c.grade_code as grade, c.section from staff_role_grant g"
        " join school_class c on c.id = g.school_class_id where g.staff_id = %s and g.role_code = any(%s)"
        " and g.valid_from <= %s and (g.valid_to is null or g.valid_to >= %s) and exists (select 1 from activity a"
        " where a.tenant_id = c.tenant_id and a.band = c.grade_code) order by c.grade_code, c.section",
        (staff_id, roles, day, day),
    ).fetchall()


def queue(conn: db.Conn, staff_id: str) -> list[dict]:
    """Her notes still waiting: being read, or drafted and within the hours a note waits."""
    hours = settings.config(conn, "voice.confirm_within_hours", 48)
    return conn.execute(
        "select id, class_id, status, received_at from pii.educator_note where staff_id = %s"
        " and status in ('received', 'drafted') and received_at > now() - make_interval(hours => %s)"
        " order by received_at",
        (staff_id, int(hours)),
    ).fetchall()


def expire(conn: db.Conn) -> int:
    """Every note older than the hours a note waits, not confirmed: left unconfirmed, never evidence."""
    hours = settings.config(conn, "voice.confirm_within_hours", 48)
    return conn.execute(
        "update pii.educator_note set status = 'left_unconfirmed' where status in ('received', 'drafted')"
        " and received_at <= now() - make_interval(hours => %s)",
        (int(hours),),
    ).rowcount
