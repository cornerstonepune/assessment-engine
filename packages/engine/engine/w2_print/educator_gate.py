"""Who sees the K2 educator's screens (D-076): everyone they are for once `educator.timetable_enabled` is on; before
that, only the staff preview, a member of staff whose open grant is in a role `educator.preview_roles` names (a config
row; head and coordinator; a missing row previews nobody). A previewer who holds no class sees every class whose
timetable is in force on the day asked: a timetable carries no child. A preview only looks: it changes and sends
nothing. The one rule for the timetable and the materials routes, and the one reading of the switch."""

import datetime as dt
from typing import Any

from engine.core import db, settings

SWITCH = "educator.timetable_enabled"
PREVIEW = "educator.preview_roles"


def switched_on(conn: db.Conn) -> bool:
    return settings.config(conn, SWITCH, False) is True


def school_today(conn: db.Conn) -> dt.date:
    zone = settings.config(conn, "school.time_zone", "Asia/Kolkata")
    return db.one(conn, "select (now() at time zone %s)::date as d", (zone,))["d"]


def holds(conn: db.Conn, staff: Any, key: str) -> bool:
    """Whether `staff` holds an open grant today, by the school's clock, in a role the config row `key` names (a list; a
    missing row names nobody)."""
    roles = list(settings.config(conn, key, []))
    today = school_today(conn)
    return bool(roles) and bool(
        conn.execute(
            "select 1 from staff_role_grant where staff_id = %s and role_code = any(%s)"
            " and valid_from <= %s and (valid_to is null or valid_to >= %s)",
            (staff, roles, today, today),
        ).fetchone()
    )


def previews(conn: db.Conn, staff: Any) -> bool:
    """Whether `staff` is the staff preview today, by the school's clock."""
    return holds(conn, staff, PREVIEW)


def open_to(conn: db.Conn, staff: Any) -> bool:
    return switched_on(conn) or previews(conn, staff)


def previewing(conn: db.Conn, staff: Any) -> bool:
    """Switched off, and she is the staff preview: she may look, not change."""
    return not switched_on(conn) and previews(conn, staff)


def timetabled_classes(conn: db.Conn, day: dt.date) -> list[dict]:
    """Every class whose timetable is in force on `day`, as `k2_day.my_classes` gives a class."""
    return conn.execute(
        "select distinct c.id::text as id, c.grade_code as grade, c.section, c.academic_year_id, c.campus_id"
        " from school_class c where exists (select 1 from timetable_slot t where t.school_class_id = c.id"
        " and t.valid_from <= %s and (t.valid_to is null or t.valid_to >= %s)) order by c.grade_code, c.section",
        (day, day),
    ).fetchall()
