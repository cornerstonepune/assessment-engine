"""What the educator sees of the generated timetable (M1-06 part 2): her day, her week, one period with its activity.
Reads only: the rows `k2_timetable_load` wrote. Every answer is for a class she holds an open grant on, in a role the
`educator.timetable_roles` row names, and carries no child and no name. One query gives all the days asked for."""

import datetime as dt
from typing import Any

from engine.core import db, settings

SWITCH = "educator.timetable_enabled"


class Refused(Exception):
    def __init__(self, words: str, status: int = 403):
        super().__init__(words)
        self.status = status


def enabled(conn: db.Conn) -> bool:
    return settings.config(conn, SWITCH, False) is True


def my_classes(conn: db.Conn, staff_id: Any, day: dt.date) -> list[dict]:
    roles = list(settings.config(conn, "educator.timetable_roles", []))
    return conn.execute(
        "select distinct c.id::text as id, c.grade_code as grade, c.section, c.academic_year_id, c.campus_id"
        " from staff_role_grant g join school_class c on c.id = g.school_class_id"
        " where g.staff_id = %s and g.role_code = any(%s) and g.valid_from <= %s"
        " and (g.valid_to is null or g.valid_to >= %s) order by c.grade_code, c.section",
        (staff_id, roles, day, day),
    ).fetchall()


def chosen(classes: list[dict], class_id: str | None) -> dict:
    if not classes:
        raise Refused("No class is yours on this day.")
    if class_id is None:
        return classes[0]
    found = [c for c in classes if c["id"] == str(class_id)]
    if not found:
        raise Refused("That is not a class you hold.")
    return found[0]


def _public(c: dict) -> dict:
    return {"id": c["id"], "grade": c["grade"], "section": c["section"]}


_ROWS = """
select d.on_date, d.kind as day_kind, d.note, f.number, f.starts_on, f.ends_on,
  case when f.id is null then null when d.on_date - f.starts_on < 7 then 'A' else 'B' end as week,
  p.id::text as period_id, p.starts_at, p.ends_at, p.label, p.fixed, ts.kind, ts.subject_code,
  coalesce(s.text, ts.text) as text, s.state, pe.text as line, a.id::text as activity_id, a.code, a.name
from school_day d
left join fortnight f on f.academic_year_id = %(year)s and d.on_date between f.starts_on and f.ends_on
left join timetable_slot ts on ts.school_class_id = %(cls)s and d.kind <> 'holiday'
  and ts.weekday = extract(isodow from d.on_date)
  and ts.week_code = case when d.on_date - f.starts_on < 7 then 'A' else 'B' end
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
        "text": r["text"] or "", "line": r["line"], "state": r["state"] or "planned", "activity": act,
    }  # fmt: skip


def days(conn: db.Conn, klass: dict, dates: list[dt.date]) -> list[dict]:
    """Each date's meaning and periods, in date order. A date with no school-day row says `none`."""
    got: dict[dt.date, dict] = {}
    for r in conn.execute(
        _ROWS,
        {"year": klass["academic_year_id"], "cls": klass["id"], "campus": klass["campus_id"], "days": dates},
    ).fetchall():
        d = got.setdefault(r["on_date"], {
            "day": r["on_date"].isoformat(), "weekday": r["on_date"].isoweekday(), "kind": r["day_kind"], "note": r["note"],
            "week": r["week"], "fortnight": {"number": r["number"], "starts_on": r["starts_on"].isoformat(), "ends_on": r["ends_on"].isoformat()} if r["number"] else None,
            "periods": [],
        })  # fmt: skip
        if r["period_id"]:
            d["periods"].append(_period(r))
    return [
        got.get(
            d,
            {
                "day": d.isoformat(),
                "weekday": d.isoweekday(),
                "kind": "none",
                "note": None,
                "week": None,
                "fortnight": None,
                "periods": [],
            },
        )
        for d in dates
    ]


def day(conn: db.Conn, klass: dict, classes: list[dict], on: dt.date) -> dict:
    return {"classes": [_public(c) for c in classes], "class": _public(klass), **days(conn, klass, [on])[0]}


def week(conn: db.Conn, klass: dict, classes: list[dict], any_day: dt.date) -> dict:
    monday = any_day - dt.timedelta(days=any_day.weekday())
    five = days(conn, klass, [monday + dt.timedelta(d) for d in range(5)])
    first = five[0]
    return {
        "classes": [_public(c) for c in classes], "class": _public(klass), "week_of": monday.isoformat(),
        "week": first["week"], "fortnight": first["fortnight"], "days": five,
    }  # fmt: skip


def period(conn: db.Conn, klass: dict, classes: list[dict], on: dt.date, period_id: str) -> dict:
    one = next((p for p in days(conn, klass, [on])[0]["periods"] if p["period_id"] == str(period_id)), None)
    if one is None:
        raise Refused("That period is not on this day.", 404)
    detail, lines = None, []
    if one["activity"]:
        a = db.one(
            conn,
            "select id::text, code, name, strand, materials, objective, level_0, level_1, level_2, level_3"
            " from activity where id = %s",
            (one["activity"]["id"],),
        )
        detail = {
            "id": a["id"], "code": a["code"], "name": a["name"], "strand": a["strand"], "tlms": a["materials"] or None,
            "lesson_plan": None, "learning_outcomes": a["objective"] or None,
            "levels": {str(i): a[f"level_{i}"] for i in range(4)},
        }  # fmt: skip
    if one["line"]:
        lines = [
            r["text"]
            for r in conn.execute(
                "select pe.text from plan_entry pe where pe.school_class_id = %s and pe.fortnight_id = (select id from fortnight"
                " where academic_year_id = %s and %s between starts_on and ends_on) and pe.plan_key = (select plan_key from"
                " plan_entry where id = (select plan_entry_id from session where school_class_id = %s and period_id = %s and"
                " school_day_id = (select id from school_day where campus_id = %s and on_date = %s))) order by pe.ord",
                (
                    klass["id"],
                    klass["academic_year_id"],
                    on,
                    klass["id"],
                    one["period_id"],
                    klass["campus_id"],
                    on,
                ),
            ).fetchall()
        ]
    return {
        "classes": [_public(c) for c in classes],
        "class": _public(klass),
        "day": on.isoformat(),
        **one,
        "activity_detail": detail,
        "plan_lines": lines,
    }
