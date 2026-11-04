"""The rows a staff import and a class educator write: a person, and a dated grant of a role signed by a staff id."""

from datetime import date
from typing import Any

from engine.core import db


def stage(
    conn: db.Conn, tenant: Any, campus: Any, entry: dict[str, Any], staff_id: Any, role: str
) -> list[tuple[Any, str]]:
    """Make the person if the list has them and the tables do not; → their grant to write last (none if `role` is empty)."""
    staff_id = staff_id or _new_staff(
        conn, tenant, campus, str(entry["name"]), str(entry["email"]).strip().lower()
    )
    return [(staff_id, role)] if role else []


def grant_all(conn: db.Conn, tenant: Any, grants: list[tuple[Any, str]], who: str) -> None:
    for staff_id, role in grants:
        grant(conn, tenant, staff_id, role, date.today(), who)


def _new_staff(conn: db.Conn, tenant: Any, campus: Any, name: str, email: str) -> Any:
    sid = db.one(
        conn, "insert into staff (tenant_id, campus_id) values (%s,%s) returning id", (tenant, campus)
    )["id"]
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s,%s,%s,%s)",
        (tenant, sid, name.strip(), email),
    )
    return sid


def grant(
    conn: db.Conn,
    tenant: Any,
    staff_id: Any,
    role: str,
    since: date,
    by: str,
    class_id: Any = None,
    reason: str | None = None,
) -> None:
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by,"
        " override_reason) values (%s,%s,%s,%s,%s,%s,%s)",
        (tenant, staff_id, role, class_id, since, by, reason),
    )
