"""What the K2 screens ask, answered in one call each (task M1-03, goals/m1-03-k2-reads.yaml). Only reading: nothing here
writes, and nothing here thinks. A note is a problem when `voice_intake.resolve` says so, the one rule the Confirm page
uses, here fed rows fetched at once so a list of fifty notes asks the database as often as a list of three.

A child is never named here: a screen names a child by Sr. No., and no answer carries a name, an id of a child, what
she said, or "not willing". The school's own words for who may ask and how far back a list reaches are the config row
`k2.reads`.
"""

import datetime as dt
from collections import defaultdict
from zoneinfo import ZoneInfo

from engine.core import db
from engine.w3_read import voice_intake
from engine.w3_read.voice_store import Refused

GROUPS = ("to_confirm", "fix_this", "left_unconfirmed", "being_read")  # a note is in exactly one
UNPLANNED_WHY = "There is no plan of activities to compare with yet."


def _cfg(conn: db.Conn) -> dict:
    rows = conn.execute(
        "select key, value from config where key in ('voice.confirm_within_hours', 'school.time_zone', 'k2.reads')"
    ).fetchall()
    got = {r["key"]: r["value"] for r in rows}
    return {
        "hours": int(got["voice.confirm_within_hours"]),
        "zone": got["school.time_zone"],
        **got["k2.reads"],
    }


def _notes(conn: db.Conn, cfg: dict, staff: str | None, campus: str | None) -> list[dict]:
    """Every note of hers (or of a campus's classes) not yet confirmed, within the days a list reaches back, with
    its state worked out. Three questions however many notes."""
    notes = conn.execute(
        "select n.id, n.tenant_id, n.class_id, n.status, n.transcript, n.received_at, c.grade_code, c.section,"
        " floor(extract(epoch from now() - n.received_at) / 3600)::int as age_hours"
        " from pii.educator_note n join school_class c on c.id = n.class_id"
        " where n.status <> 'confirmed' and n.received_at > now() - make_interval(days => %s)"
        " and (%s::uuid is null or n.staff_id = %s) and (%s::uuid is null or c.campus_id = %s)"
        " order by n.received_at, n.id",
        (cfg["row_days"], staff, staff, campus, campus),
    ).fetchall()
    heard = [n for n in notes if n["transcript"]]
    classes = list({n["class_id"] for n in heard})
    grades = list({n["grade_code"] for n in heard})
    rolls = defaultdict(list)
    for e in conn.execute(
        "select class_id, roll_no, child_id, from_date, to_date from enrolment where class_id = any(%s)",
        (classes,),
    ).fetchall():
        rolls[e["class_id"]].append(e)
    named = defaultdict(list)
    for a in conn.execute(
        "select code, name, band, sheet_no from activity where band = any(%s) and sheet_no is not null",
        (grades,),
    ).fetchall():
        named[(a["band"], a["sheet_no"])].append(a)
    grade_of = {n["class_id"]: n["grade_code"] for n in heard}

    def enrolled_on(class_id, day):
        return {
            e["roll_no"]: str(e["child_id"])
            for e in rolls[class_id]
            if e["from_date"] <= day and (e["to_date"] is None or e["to_date"] >= day)
        }

    def activities_of(class_id, number):
        return sorted(a["code"] for a in named[(grade_of[class_id], str(number))])

    zone = ZoneInfo(cfg["zone"])

    def day_of(at):
        return at.astimezone(zone).date()

    names = {a["code"]: a["name"] for found in named.values() for a in found}
    out = []
    for n in notes:
        found = voice_intake.resolve(conn, n, enrolled_on, activities_of, day_of) if n["transcript"] else None
        late = n["status"] == "left_unconfirmed" or (
            n["status"] in ("received", "drafted") and n["age_hours"] >= cfg["hours"]
        )
        state = (
            "left_unconfirmed" if late else "being_read" if found is None else "fix_this" if found.blocked else "to_confirm"
        )  # fmt: skip
        code = found.activity if found else None
        out.append({
            "note_id": str(n["id"]), "class": f"{n['grade_code']} {n['section']}", "activity": code,
            "activity_name": names.get(code), "received_at": n["received_at"].isoformat(),
            "age_hours": n["age_hours"], "state": state,
        })  # fmt: skip
    return out


def todo(conn: db.Conn, email: str) -> dict:
    """An educator's own notes in groups with counts: to confirm, to fix, left unconfirmed, being read. Oldest first."""
    staff = str(voice_intake.staff_of(conn, email))
    rows = _notes(conn, _cfg(conn), staff, None)
    groups = {g: {"rows": [], "count": 0} for g in GROUPS}
    for r in rows:
        groups[r["state"]]["rows"].append({k: v for k, v in r.items() if k != "class"})
    for g in groups.values():
        g["count"] = len(g["rows"])
    return {"groups": groups}


def coordinator(conn: db.Conn, email: str) -> dict:
    """Only what needs a decision, red first: notes with a problem, then notes left unconfirmed, as rows; and as counts
    the confirmations made on a later day than the activity, the children and the class-days with nothing observed
    this week. 'Unplanned' is null until a plan exists to compare with: said, not invented."""
    cfg = _cfg(conn)
    staff = voice_intake.staff_of(conn, email)
    me = db.one(
        conn,
        "select s.campus_id, exists (select 1 from staff_role_grant g where g.staff_id = s.id"
        " and g.role_code = any(%s) and g.valid_from <= current_date and (g.valid_to is null or g.valid_to >= current_date))"
        " as ok from staff s where s.id = %s",
        (cfg["coordinator_roles"], staff),
    )
    if not me["ok"]:
        raise Refused("This page is for the coordinators.", 403)
    rows = [
        r
        for r in _notes(conn, cfg, None, str(me["campus_id"]))
        if r["state"] in ("fix_this", "left_unconfirmed")
    ]
    rows.sort(key=lambda r: (r["state"] != "fix_this", -r["age_hours"]))  # red first, each oldest first
    return {"rows": rows, "counts": _counts(conn, cfg, str(me["campus_id"]))}


def _counts(conn: db.Conn, cfg: dict, campus: str) -> dict:
    zone = ZoneInfo(cfg["zone"])
    today = dt.datetime.now(zone).date()
    week = today - dt.timedelta(days=(today.weekday() - cfg["week_starts_on"]) % 7)
    got = db.one(
        conn,
        "with k as (select id from school_class where campus_id = %(campus)s and grade_code = any(%(grades)s)),"
        " start as (select (%(week)s::date::timestamp at time zone %(zone)s) as at)"
        " select"
        " (select count(distinct o.confirmation_id) from activity_observation o, start where o.class_id in (select id from k)"
        "  and o.supersedes is null and o.stored_at >= start.at"
        "  and (o.stored_at at time zone %(zone)s)::date > (o.observed_at at time zone %(zone)s)::date) as late,"
        " (select count(*) from enrolment e, start where e.class_id in (select id from k) and e.to_date is null"
        "  and not exists (select 1 from activity_observation o where o.child_id = e.child_id"
        "   and o.stored_at >= start.at)) as children_without_notes,"
        " (select count(*) from k cross join generate_series(%(week)s::date, %(today)s::date, '1 day') d"
        "  where extract(isodow from d) < 6 and not exists (select 1 from pii.educator_note n where n.class_id = k.id"
        "   and (n.received_at at time zone %(zone)s)::date = d::date)) as class_days_without_notes",
        {"campus": campus, "grades": cfg["grades"], "week": week, "today": today, "zone": cfg["zone"]},
    )
    return {
        "late": got["late"], "unplanned": None, "unplanned_why": UNPLANNED_WHY,
        "children_without_notes": got["children_without_notes"],
        "class_days_without_notes": got["class_days_without_notes"],
    }  # fmt: skip
