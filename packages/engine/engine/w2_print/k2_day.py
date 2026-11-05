"""What the educator sees of the generated timetable (M1-06 part 2): her day, her week, one period with its activity.
Reads only: the rows `k2_timetable_load` wrote. Every answer is for a class she holds an open grant on, in a role the
`educator.timetable_roles` row names, and carries no child and no name. One query gives all the days asked for."""

import datetime as dt
from typing import Any

from engine.core import db, settings
from engine.w2_print import educator_gate as gate

SWITCH = gate.SWITCH


class Refused(Exception):
    def __init__(self, words: str, status: int = 403):
        super().__init__(words)
        self.status = status


def enabled(conn: db.Conn) -> bool:
    return gate.switched_on(conn)


def my_classes(conn: db.Conn, staff_id: Any, day: dt.date) -> list[dict]:
    """The classes she holds that day; while switched off, the staff preview (D-076) also gets every class whose
    timetable is in force that day."""
    roles = list(settings.config(conn, "educator.timetable_roles", []))
    held = conn.execute(
        "select distinct c.id::text as id, c.grade_code as grade, c.section, c.academic_year_id, c.campus_id"
        " from staff_role_grant g join school_class c on c.id = g.school_class_id"
        " where g.staff_id = %s and g.role_code = any(%s) and g.valid_from <= %s"
        " and (g.valid_to is null or g.valid_to >= %s) order by c.grade_code, c.section",
        (staff_id, roles, day, day),
    ).fetchall()
    if not gate.previewing(conn, staff_id):
        return held
    ids = {c["id"] for c in held}
    return held + [c for c in gate.timetabled_classes(conn, day) if c["id"] not in ids]


def chosen(classes: list[dict], class_id: str | None) -> dict:
    if not classes:
        raise Refused("No class is yours on this day.")
    if class_id is None:
        return classes[0]
    found = next((c for c in classes if c["id"] == class_id), None)
    if found is None:
        raise Refused("That is not a class you hold.")
    return found


def _public(c: dict) -> dict:
    return {"id": c["id"], "grade": c["grade"], "section": c["section"]}


_ROWS = """
select d.on_date, d.kind as day_kind, d.note, f.number, f.starts_on, f.ends_on,
  w.week,
  p.id::text as period_id, p.starts_at, p.ends_at, p.label, p.fixed, ts.kind, ts.subject_code,
  coalesce(s.text, ts.text) as text, ts.text as slot_text, s.state, pe.text as line, pe.id::text as entry_id, a.id::text as activity_id, a.code, a.name
from school_day d
left join fortnight f on f.academic_year_id = %(year)s and d.on_date between f.starts_on and f.ends_on
left join lateral (select case when f.id is null then null when d.on_date - f.starts_on < 7 then 'A' else 'B' end as week) w on true
left join timetable_slot ts on ts.school_class_id = %(cls)s and d.kind <> 'holiday'
  and ts.weekday = extract(isodow from d.on_date)
  and ts.week_code = w.week
  and ts.valid_from <= d.on_date and (ts.valid_to is null or ts.valid_to >= d.on_date)
left join period p on p.id = ts.period_id
left join session s on s.school_class_id = ts.school_class_id and s.school_day_id = d.id and s.period_id = ts.period_id
left join plan_entry pe on pe.id = s.plan_entry_id
left join activity a on a.id = pe.activity_id
where d.campus_id = %(campus)s and d.on_date = any(%(days)s)
order by d.on_date, p.starts_at
"""


def _hm(t: dt.time | None) -> str | None:
    return t.strftime("%H:%M") if t else None


def _period(r: dict) -> dict:
    act = {"id": r["activity_id"], "code": r["code"], "name": r["name"]} if r["activity_id"] else None
    return {
        "period_id": r["period_id"], "starts_at": _hm(r["starts_at"]), "ends_at": _hm(r["ends_at"]),
        "label": r["label"], "fixed": r["fixed"], "kind": r["kind"], "subject": r["subject_code"],
        "name": r["label"] if r["fixed"] else (r["slot_text"] or r["label"]),
        "text": r["text"] or "", "line": r["line"], "plan_entry_id": r["entry_id"], "state": r["state"] or "planned", "activity": act,
    }  # fmt: skip


def _empty_day(d: dt.date, kind: str = "none", note: str | None = None) -> dict:
    return {
        "day": d.isoformat(), "weekday": d.isoweekday(), "kind": kind, "note": note, "week": None, "fortnight": None,
        "periods": [],
    }  # fmt: skip


def days(conn: db.Conn, klass: dict, dates: list[dt.date]) -> list[dict]:
    """Each date's meaning and periods, in date order. A date with no school-day row says `none`."""
    got: dict[dt.date, dict] = {}
    query = {
        "year": klass["academic_year_id"],
        "cls": klass["id"],
        "campus": klass["campus_id"],
        "days": dates,
    }
    for r in conn.execute(_ROWS, query).fetchall():
        if r["on_date"] not in got:
            got[r["on_date"]] = _empty_day(r["on_date"], r["day_kind"], r["note"]) | {
                "week": r["week"],
                "fortnight": {"number": r["number"], "starts_on": r["starts_on"].isoformat(), "ends_on": r["ends_on"].isoformat()}
                if r["number"] else None,
            }  # fmt: skip
        if r["period_id"]:
            got[r["on_date"]]["periods"].append(_period(r))
    for d in got.values():
        _ends(d["periods"])
    return [got.get(d) or _empty_day(d) for d in dates]


def _ends(periods: list[dict]) -> None:
    """A period the frame gives no end (the bus) lasts until the next one starts; the day's last keeps none."""
    for p, after in zip(periods, periods[1:]):
        if p["ends_at"] is None:
            p["ends_at"] = after["starts_at"]


def _who(klass: dict, classes: list[dict]) -> dict:
    # `frozen` is the month lock (M1-12): false until that exists, so a screen reads it and never guesses
    return {"classes": [_public(c) for c in classes], "class": _public(klass), "frozen": False}


def day(conn: db.Conn, klass: dict, classes: list[dict], on: dt.date) -> dict:
    return {**_who(klass, classes), **days(conn, klass, [on])[0]}


def week(conn: db.Conn, klass: dict, classes: list[dict], any_day: dt.date) -> dict:
    monday = any_day - dt.timedelta(days=any_day.weekday())
    five = days(conn, klass, [monday + dt.timedelta(d) for d in range(5)])
    return {
        **_who(klass, classes), "week_of": monday.isoformat(), "week": next((d["week"] for d in five if d["week"]), None),
        "fortnight": next((d["fortnight"] for d in five if d["fortnight"]), None), "days": five,
    }  # fmt: skip


def _plan_lines(conn: db.Conn, entry_id: str | None) -> list[str]:
    """The planner lines under the same heading and fortnight as this period's line, in the planner's order: of its own
    week when the fortnight is listed under two months (`plan_entry.week_code`), else all of them."""
    if not entry_id:
        return []
    return [
        r["text"]
        for r in conn.execute(
            "select sib.text from plan_entry pe join plan_entry sib on sib.school_class_id = pe.school_class_id"
            " and sib.fortnight_id = pe.fortnight_id and sib.plan_key = pe.plan_key"
            " and sib.week_code is not distinct from pe.week_code where pe.id = %s order by sib.ord",
            (entry_id,),
        ).fetchall()
    ]


def period(conn: db.Conn, klass: dict, classes: list[dict], on: dt.date, period_id: str) -> dict:
    """One period of one day, with the planner lines for its subject in this fortnight. The activity's own text is the
    activity page's (`/activity`): here it is only who it is."""
    today = days(conn, klass, [on])[0]
    one = next((p for p in today["periods"] if p["period_id"] == period_id), None)
    if one is None:
        raise Refused("That period is not on this day.", 404)
    head = {k: v for k, v in today.items() if k not in ("periods", "weekday")}
    return {**_who(klass, classes), **head, **one, "plan_lines": _plan_lines(conn, one["plan_entry_id"])}
