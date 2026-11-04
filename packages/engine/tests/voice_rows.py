"""Placeholder rows for the K2 voice-note tests: a K2 class, its educator, five enrolled children with roll numbers 1
to 5, and an activity numbered 12 on the K2 list with two skills. Made inside the test's transaction; no school data."""

import datetime as dt
import uuid

from tests.rows import a_child, tenant


def a_k2_class(conn) -> dict:
    t = tenant(conn)
    tag = uuid.uuid4().hex[:6]
    campus = conn.execute("select id from campus where tenant_id = %s limit 1", (t,)).fetchone()["id"]
    year = conn.execute(
        "insert into academic_year (tenant_id, label, starts_on, ends_on) values (%s, '2031-32', '2026-01-01',"
        " '2032-03-31') on conflict (tenant_id, label) do update set label = excluded.label returning id",
        (t,),
    ).fetchone()["id"]
    klass = conn.execute(
        "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
        " values (%s, %s, %s, 'K2', %s) returning id",
        (t, campus, year, f"T{tag}"),
    ).fetchone()["id"]
    staff = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (t, campus)
    ).fetchone()["id"]
    email = f"placeholder.{tag}@example.test"
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'Placeholder Educator', %s)",
        (t, staff, email),
    )
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by)"
        " values (%s, %s, 'class_teacher', %s, '2026-01-01', 'test')",
        (t, staff, klass),
    )
    children = {}
    for roll in ("1", "2", "3", "4", "5"):
        child = a_child(conn)
        conn.execute(
            "insert into enrolment (tenant_id, child_id, class_id, roll_no, from_date, recorded_by)"
            " values (%s, %s, %s, %s, %s, 'test')",
            (t, child, klass, roll, dt.date(2026, 1, 1)),
        )
        children[roll] = str(child)
    code = f"ACT-K2-T{tag}"
    conn.execute(
        "insert into activity (tenant_id, code, band, strand, name, sheet_no) values (%s, %s, 'K2', 'Maths',"
        " 'Placeholder activity', '12')",
        (t, code),
    )
    skills = [
        r["code"]
        for r in conn.execute(
            "select code from registry_skill where tenant_id = %s order by code limit 2", (t,)
        ).fetchall()
    ]
    for skill in skills:
        conn.execute(
            "insert into activity_skill (tenant_id, activity_code, skill_code) values (%s, %s, %s)",
            (t, code, skill),
        )
    return {
        "tenant": t, "class": str(klass), "staff": staff, "email": email, "children": children,
        "activity": code, "skills": skills,
    }  # fmt: skip


def a_note(conn, k: dict, transcript: str, *, hours_ago: float = 0) -> dict:
    """A note as if received and transcribed: its row, drafted, `received_at` moved back for an old note."""
    note = conn.execute(
        "insert into pii.educator_note (tenant_id, staff_id, class_id, audio_key, transcript, status)"
        " values (%s, %s, %s, %s, %s, 'drafted') returning *",
        (k["tenant"], k["staff"], k["class"], f"voice/2026/{uuid.uuid4()}.m4a", transcript),
    ).fetchone()
    if hours_ago:
        conn.execute("alter table pii.educator_note disable trigger educator_note_clock")
        conn.execute(
            "update pii.educator_note set received_at = now() - make_interval(secs => %s) where id = %s",
            (hours_ago * 3600, note["id"]),
        )
        conn.execute("alter table pii.educator_note enable trigger educator_note_clock")
        note = conn.execute("select * from pii.educator_note where id = %s", (note["id"],)).fetchone()
    return note
