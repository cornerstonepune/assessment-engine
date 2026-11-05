"""Who sees the K2 educator's screens (D-076): everyone they are for once `educator.timetable_enabled` is on; before
that, only the staff preview, a member of staff whose open grant is in a role `educator.preview_roles` names (a config
row; head and coordinator). A previewer who holds no class sees every class that has a timetable: a timetable carries
no child. The one rule for the timetable and the materials routes; the switch alone still decides what is sent out
(reminders), since a preview sends nothing."""

from typing import Any

from engine.core import db, settings

SWITCH = "educator.timetable_enabled"
PREVIEW = "educator.preview_roles"


def switched_on(conn: db.Conn) -> bool:
    return settings.config(conn, SWITCH, False) is True


def previews(conn: db.Conn, staff: Any) -> bool:
    roles = list(settings.config(conn, PREVIEW, ["head", "coordinator"]))
    return bool(
        conn.execute(
            "select 1 from staff_role_grant where staff_id = %s and role_code = any(%s)"
            " and valid_from <= current_date and (valid_to is null or valid_to >= current_date)",
            (staff, roles),
        ).fetchone()
    )


def open_to(conn: db.Conn, staff: Any) -> bool:
    return switched_on(conn) or previews(conn, staff)


def timetabled_classes(conn: db.Conn) -> list[dict]:
    """Every class with a timetable, as `k2_day.my_classes` gives a class."""
    return conn.execute(
        "select distinct c.id::text as id, c.grade_code as grade, c.section, c.academic_year_id, c.campus_id"
        " from school_class c where exists (select 1 from timetable_slot t where t.school_class_id = c.id)"
        " order by c.grade_code, c.section"
    ).fetchall()
