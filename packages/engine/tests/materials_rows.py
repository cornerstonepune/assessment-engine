"""Placeholder rows for the materials-list tests (task M1-10): a K2 class, its educator, planned sessions and the
materials of their activities. Every row is made inside the test's own transaction and rolled back: no school data and
no child, and no name of one."""

import datetime as dt
import uuid

from tests.rows import tenant

MON = dt.date(2031, 11, 3)  # a Monday in a year no real row uses


def school(conn):
    t = tenant(conn)
    campus = conn.execute("select id from campus where tenant_id = %s limit 1", (t,)).fetchone()["id"]
    year = conn.execute(
        "insert into academic_year (tenant_id, label, starts_on, ends_on) values (%s, '2031-32', '2031-04-01',"
        " '2032-03-31') on conflict (tenant_id, label) do update set label = excluded.label returning id",
        (t,),
    ).fetchone()["id"]
    klass = conn.execute(
        "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
        " values (%s, %s, %s, 'K2', %s) returning id",
        (t, campus, year, f"T{uuid.uuid4().hex[:5]}"),
    ).fetchone()["id"]
    staff = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (t, campus)
    ).fetchone()["id"]
    email = f"placeholder.{uuid.uuid4().hex[:6]}@example.test"
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'Placeholder Educator', %s)",
        (t, staff, email),
    )
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by)"
        " values (%s, %s, 'class_teacher', %s, '2026-01-01', 'test')",
        (t, staff, klass),
    )
    fortnight = conn.execute(
        "insert into fortnight (tenant_id, academic_year_id, number, kind, starts_on, ends_on)"
        " values (%s, %s, 910, 'teaching', %s, %s) returning id",
        (t, year, MON, MON + dt.timedelta(days=13)),
    ).fetchone()["id"]
    periods = [
        conn.execute(
            "insert into period (tenant_id, grade_code, ord, starts_at, label) values (%s, 'K2', %s, %s, %s)"
            " on conflict (tenant_id, grade_code, starts_at) do update set label = excluded.label returning id",
            (t, 900 + i, f"{9 + i}:00", f"slot {i}"),
        ).fetchone()["id"]
        for i in range(3)
    ]
    codes = [
        r["code"]
        for r in conn.execute("select code from activity where tenant_id = %s order by code limit 4", (t,))
    ]
    return {
        "tenant": t,
        "campus": campus,
        "class": klass,
        "staff": staff,
        "email": email,
        "fortnight": fortnight,
        "periods": periods,
        "acts": codes,
        "slot": {},
    }


def item(conn, s, name, unit="piece", home=None, unit_value=None):
    code = f"MAT-T{uuid.uuid4().hex[:6]}"
    conn.execute(
        "insert into material_item (tenant_id, code, name, unit, home, unit_value) values (%s,%s,%s,%s,%s,%s)",
        (s["tenant"], code, f"{name} {code}", unit, home, unit_value),
    )
    return code


def needs(conn, s, activity, material, quantity, ord_=1):
    conn.execute(
        "insert into activity_material (tenant_id, activity_code, material_code, quantity, ord)"
        " values (%s,%s,%s,%s,%s)",
        (s["tenant"], activity, material, quantity, ord_),
    )


def planned(conn, s, on, activity, planned_=True, klass=None):
    """A session of `activity` for the class on `on`, in the next free period of that day."""
    day = conn.execute(
        "insert into school_day (tenant_id, campus_id, on_date, kind) values (%s,%s,%s,'teaching')"
        " on conflict (tenant_id, campus_id, on_date) do update set kind = 'teaching' returning id",
        (s["tenant"], s["campus"], on),
    ).fetchone()["id"]
    n = s["slot"][on] = s["slot"].get(on, -1) + 1
    plan = conn.execute(
        "insert into plan_entry (tenant_id, school_class_id, fortnight_id, plan_key, ord, text, activity_id, source)"
        " values (%s,%s,%s,%s,%s,'a planner line',(select id from activity where tenant_id=%s and code=%s),'test')"
        " returning id",
        (
            s["tenant"],
            klass or s["class"],
            s["fortnight"],
            f"k{on}{n}{uuid.uuid4().hex[:4]}",
            1 + n,
            s["tenant"],
            activity,
        ),
    ).fetchone()["id"]
    conn.execute(
        "insert into session (tenant_id, school_class_id, school_day_id, period_id, planned, plan_entry_id, text)"
        " values (%s,%s,%s,%s,%s,%s,'x')",
        (s["tenant"], klass or s["class"], day, s["periods"][n], planned_, plan),
    )


def another_class(conn, s, section, grade="K2"):
    """A second class in the same school year as `s`'s, with no plan yet."""
    return conn.execute(
        "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
        " select tenant_id, campus_id, academic_year_id, %s, %s from school_class where id = %s returning id",
        (grade, section, s["class"]),
    ).fetchone()["id"]
