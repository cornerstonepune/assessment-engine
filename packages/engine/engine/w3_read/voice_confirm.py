"""The educator confirms a K2 note, or saves the form: observations, then evidence, written by code in one transaction
(task M1-01; observation model section 4, steps 5 and 6).

She sends what she confirms: the activity, the level she expected, the roll numbers under each outcome and whether
"the rest did as expected". One confirmation is one id. Each child named gets one `activity_observation` row (entry
mode individual); "the rest" gives every child of the class enrolled that day and not named a row as expected (group).
Above, below and as expected are evidence on each skill the activity names, its mark from config rows
(`voice.outcome_moves_level`, `voice.level_mark`); not willing and absent are observations only. No model writes here.
A voice note's draft lines are written beside what she kept (`pii.note_claim`): her changes are the reader's record.
"""

import datetime as dt
import uuid
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from engine.core import db, settings
from engine.w3_read import voice_intake, voice_note
from engine.w3_read.voice_store import Refused

EVIDENCE = (
    "above",
    "as_expected",
    "below",
)  # outcomes that are evidence on a skill; the rest are observations only


@dataclass
class Confirmed:
    activity: str  # activity code, as she confirmed it
    level: int  # the level she expected
    lists: dict[str, list[str]] = field(
        default_factory=dict
    )  # section (above, below, not_willing, absent) → rolls
    rest: bool = False  # "the rest did as expected"
    day: dt.date | None = None  # the day it was taught; the note's own day when not given


def _reached(conn: db.Conn, outcome: str, level: int) -> int:
    """The level the outcome showed: her expected level moved by the outcome (`voice.outcome_moves_level`), 0 to 3."""
    return min(3, max(0, level + settings.config(conn, "voice.outcome_moves_level", {})[outcome]))


def _mark(conn: db.Conn, reached: int) -> str:
    """The mark on the seen scale for a level reached (`voice.level_mark`)."""
    return settings.config(conn, "voice.level_mark", {})[str(reached)]


def _observed_at(conn: db.Conn, day: dt.date, received: dt.datetime) -> dt.datetime:
    """When it was taught: the note's own time on its own day, else the start of the day she said; never later than
    now, so a phone clock ahead of the database's is never refused for it."""
    zone = ZoneInfo(settings.config(conn, "school.time_zone", "Asia/Kolkata"))
    at = received if received.astimezone(zone).date() == day else dt.datetime.combine(day, dt.time(), zone)
    return min(at, db.one(conn, "select now() as n")["n"])


def _children(
    conn: db.Conn, class_id: str, day: dt.date | None, final: Confirmed
) -> dict[str, tuple[str, str]]:
    """child id → (outcome, entry mode), every roll number found in the class's enrolment that day."""
    enrolled = voice_intake.enrolled(conn, class_id, day or dt.date.today())
    outcome = {s: voice_note.template().outcomes[s] or s for s in voice_intake.LISTS}
    out: dict[str, tuple[str, str]] = {}
    for section, rolls in final.lists.items():
        for roll in rolls:
            child = enrolled.get(str(roll))
            if child is None:
                raise Refused(f"#{roll} is not in this class. Which child?")
            if child in out:
                raise Refused(f"#{roll} is in two lists. Pick one.")
            out[child] = (outcome[section], "individual")
    if final.rest:
        out |= {c: ("as_expected", "group_as_expected") for c in enrolled.values() if c not in out}
    return out


def _write(
    conn: db.Conn, *, class_id, staff, final: Confirmed, route: str, note_id, observed_at
) -> uuid.UUID:
    if not conn.execute(
        "select 1 from activity a join school_class c on c.tenant_id = a.tenant_id where c.id = %s and a.code = %s",
        (class_id, final.activity),
    ).fetchone():
        raise Refused(f"{final.activity} is not on the activity list.")
    skills = [
        r["skill_code"]
        for r in conn.execute(
            "select skill_code from activity_skill where activity_code = %s", (final.activity,)
        )
    ]
    confirmation = uuid.uuid4()
    for child, (outcome, mode) in _children(conn, class_id, final.day, final).items():
        reached = _reached(conn, outcome, final.level) if outcome in EVIDENCE else None
        obs = db.one(
            conn,
            "insert into activity_observation (tenant_id, confirmation_id, note_id, activity_code, child_id, class_id,"
            " outcome, entry_mode, route, expected_level, reached_level, observed_at, observed_by, confirmed_by)"
            " select tenant_id, %s, %s, %s, %s, id, %s, %s, %s, %s, %s, %s, %s, %s from school_class where id = %s"
            " returning id, tenant_id",
            (confirmation, note_id, final.activity, child, outcome, mode, route, final.level, reached, observed_at,
             staff, staff, class_id),
        )  # fmt: skip
        if reached is not None:
            mark = _mark(conn, reached)
            for skill in skills:
                conn.execute(
                    "insert into evidence_event (tenant_id, child_id, skill_code, channel, observed_at, confirmed_by,"
                    " kind, mark, seen_by, place, source, observation_id)"
                    " values (%s, %s, %s, 'educator', %s, %s, 'observed', %s, %s, %s, %s, %s)",
                    (obs["tenant_id"], child, skill, observed_at, str(staff), mark, str(staff), f"class {class_id}",
                     f"activity_observation {obs['id']}", obs["id"]),
                )  # fmt: skip
    return confirmation


def _claims(conn: db.Conn, note: dict, found: voice_intake.Resolved, final: Confirmed, staff) -> None:
    """Each draft line beside what she kept: accepted as read, changed, or removed."""
    kept = {s: [str(r) for r in final.lists.get(s, [])] for s in voice_intake.LISTS} | {
        "activity": [final.activity], "level": [str(final.level)], "rest": ["yes"] if final.rest else [],
    }  # fmt: skip
    start = 0
    for line in found.draft.lines:
        if line.section not in kept:
            continue
        read_as = [str(n) for n in line.numbers] if line.numbers or line.section != "rest" else ["yes"]
        at = (note["transcript"] or "").find(line.words.split(" … ")[0], start)
        start = at if at >= 0 else start
        if line.section == "activity":
            read_as = [found.activity or ", ".join(read_as)]
        same = read_as == kept[line.section]
        decision = "accepted" if same else ("removed" if not kept[line.section] else "changed")
        conn.execute(
            "insert into pii.note_claim (tenant_id, note_id, section, read_as, words, span_start, span_end, decision,"
            " kept_as, decided_by) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (note["tenant_id"], note["id"], line.section, ", ".join(read_as), line.words, max(start, 0),
             max(start, 0) + len(line.words), decision, ", ".join(kept[line.section]) if decision == "changed" else None,
             staff),
        )  # fmt: skip


def confirm_note(conn: db.Conn, note_id: str, email: str, final: Confirmed) -> uuid.UUID:
    staff = voice_intake.staff_of(conn, email)
    note_id = voice_intake.valid_id(note_id)
    note = conn.execute("select * from pii.educator_note where id = %s for update", (note_id,)).fetchone()
    if note is None or note["staff_id"] != staff:
        raise Refused("This is not one of your notes.", 404)
    if note["status"] != "drafted":
        raise Refused(f"This note is {note['status'].replace('_', ' ')}, not waiting to be confirmed.", 409)
    hours = settings.config(conn, "voice.confirm_within_hours", 48)
    if db.one(
        conn, "select %s < now() - make_interval(hours => %s) as late", (note["received_at"], int(hours))
    )["late"]:
        raise Refused(
            f"This note waited more than {hours} hours; it is kept as unconfirmed, never evidence.", 409
        )
    draft = voice_note.read(note["transcript"] or "")
    if draft.kind == "incident":
        raise Refused("An incident note is never confirmed as an observation.", 409)
    found = voice_intake.resolve(conn, note)
    voice_intake.may_record(conn, staff, note["class_id"])
    final.day = final.day or found.taught_on
    at = _observed_at(conn, final.day, note["received_at"])
    # confirmed first, in the same transaction: the database refuses evidence from a note that is not
    # (`internal.evidence_of_a_confirmed_note`), and a refusal below undoes the confirmation with everything else
    conn.execute("update pii.educator_note set status = 'confirmed' where id = %s", (note["id"],))
    confirmation = _write(
        conn,
        class_id=note["class_id"],
        staff=staff,
        final=final,
        route="voice",
        note_id=note["id"],
        observed_at=at,
    )
    _claims(conn, note, found, final, staff)
    return confirmation


def save_form(conn: db.Conn, email: str, class_id: str, final: Confirmed) -> uuid.UUID:
    """The form's Save is its confirmation: the same rows, by the form, with no note."""
    staff = voice_intake.staff_of(conn, email)
    class_id = voice_intake.valid_id(class_id)
    voice_intake.may_record(conn, staff, class_id)
    final.day = final.day or dt.date.today()
    now = db.one(conn, "select now() as n")["n"]
    return _write(
        conn, class_id=class_id, staff=staff, final=final, route="form", note_id=None,
        observed_at=_observed_at(conn, final.day, now),
    )  # fmt: skip


def correct(conn: db.Conn, observation_id: str, email: str, outcome: str, reason: str) -> uuid.UUID:
    """A confirmed observation corrected: a new row naming the one it replaces and why, with its own evidence."""
    staff = voice_intake.staff_of(conn, email)
    observation_id = voice_intake.valid_id(observation_id)
    old = conn.execute("select * from activity_observation where id = %s", (observation_id,)).fetchone()
    if old is None or staff not in (old["confirmed_by"], old["observed_by"]):
        raise Refused("This is not one of your observations.", 404)
    voice_intake.may_record(conn, staff, old["class_id"])
    if conn.execute("select 1 from activity_observation where supersedes = %s", (old["id"],)).fetchone():
        raise Refused("This observation is already corrected; correct the newer one.", 409)
    reached = _reached(conn, outcome, old["expected_level"]) if outcome in EVIDENCE else None
    new = db.one(
        conn,
        "insert into activity_observation (tenant_id, confirmation_id, note_id, activity_code, child_id, class_id,"
        " outcome, entry_mode, route, expected_level, reached_level, observed_at, observed_by, confirmed_by,"
        " supersedes, reason) values (%s, %s, %s, %s, %s, %s, %s, 'individual', %s, %s, %s, %s, %s, %s, %s, %s)"
        " returning id",
        (old["tenant_id"], uuid.uuid4(), old["note_id"], old["activity_code"], old["child_id"], old["class_id"],
         outcome, old["route"], old["expected_level"], reached, old["observed_at"], old["observed_by"], staff,
         old["id"], reason),
    )["id"]  # fmt: skip
    if reached is not None:
        mark = _mark(conn, reached)
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, channel, observed_at, confirmed_by, kind,"
            " mark, seen_by, place, source, observation_id)"
            " select %s, %s, skill_code, 'educator', %s, %s, 'observed', %s, %s, %s, %s, %s from activity_skill"
            " where activity_code = %s",
            (old["tenant_id"], old["child_id"], old["observed_at"], str(staff), mark, str(old["observed_by"]),
             f"class {old['class_id']}", f"activity_observation {new}", new, old["activity_code"]),
        )  # fmt: skip
    return new
